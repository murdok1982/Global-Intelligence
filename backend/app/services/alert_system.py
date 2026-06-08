from __future__ import annotations

import enum
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.base import Base
from app.db.session import AsyncSessionLocal


class AlertSeverity(str, enum.Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertChannel(str, enum.Enum):
    EMAIL = "email"
    WEBHOOK = "webhook"
    IN_APP = "in_app"


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, index=True)
    metric = Column(String(200), nullable=False, index=True)
    country_iso = Column(String(3), nullable=True, index=True)
    threshold = Column(Float, nullable=False)
    comparison = Column(String(10), nullable=False, default="gt")
    severity = Column(Enum(AlertSeverity), nullable=False, default=AlertSeverity.MEDIUM)
    channels = Column(JSONB, default=list)
    cooldown_minutes = Column(Integer, nullable=False, default=60)
    is_active = Column(Boolean, nullable=False, default=True)
    metadata_json = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id = Column(UUID(as_uuid=True), ForeignKey("alert_rules.id"), nullable=False, index=True)
    severity = Column(Enum(AlertSeverity), nullable=False)
    title = Column(String(500), nullable=False)
    body = Column(Text, nullable=False)
    channels = Column(JSONB, default=list)
    metric_value = Column(Float)
    threshold_value = Column(Float)
    country_iso = Column(String(3), nullable=True)
    metadata_json = Column(JSONB, default=dict)
    dispatched = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AlertHistory(Base):
    __tablename__ = "alert_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_id = Column(UUID(as_uuid=True), ForeignKey("alerts.id"), nullable=False, index=True)
    channel = Column(Enum(AlertChannel), nullable=False)
    status = Column(String(50), nullable=False, default="pending")
    response_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    dispatched_at = Column(DateTime(timezone=True), server_default=func.now())


PREBUILT_RULES: list[dict[str, Any]] = [
    {
        "name": "Defense Spending Spike (>20% YoY)",
        "metric": "defense_budget_yoy_change",
        "threshold": 20.0,
        "comparison": "gt",
        "severity": AlertSeverity.HIGH,
        "channels": [AlertChannel.EMAIL.value, AlertChannel.IN_APP.value],
        "cooldown_minutes": 1440,
    },
    {
        "name": "Arms Transfer Surge (>5 deals in 30 days)",
        "metric": "arms_deals_30d",
        "threshold": 5.0,
        "comparison": "gt",
        "severity": AlertSeverity.MEDIUM,
        "channels": [AlertChannel.IN_APP.value],
        "cooldown_minutes": 720,
    },
    {
        "name": "Military Exercise Near Border",
        "metric": "military_exercise_proximity_km",
        "threshold": 50.0,
        "comparison": "lt",
        "severity": AlertSeverity.HIGH,
        "channels": [AlertChannel.EMAIL.value, AlertChannel.WEBHOOK.value, AlertChannel.IN_APP.value],
        "cooldown_minutes": 360,
    },
    {
        "name": "Sanctions Escalation",
        "metric": "sanctions_count_delta",
        "threshold": 1.0,
        "comparison": "gte",
        "severity": AlertSeverity.MEDIUM,
        "channels": [AlertChannel.IN_APP.value, AlertChannel.WEBHOOK.value],
        "cooldown_minutes": 1440,
    },
    {
        "name": "Cyber Attack on Critical Infrastructure",
        "metric": "cyber_incident_severity",
        "threshold": 3.0,
        "comparison": "gte",
        "severity": AlertSeverity.CRITICAL,
        "channels": [AlertChannel.EMAIL.value, AlertChannel.WEBHOOK.value, AlertChannel.IN_APP.value],
        "cooldown_minutes": 60,
    },
]


def _compare(value: float, threshold: float, comparison: str) -> bool:
    ops: dict[str, Any] = {
        "gt": lambda a, b: a > b,
        "gte": lambda a, b: a >= b,
        "lt": lambda a, b: a < b,
        "lte": lambda a, b: a <= b,
        "eq": lambda a, b: a == b,
    }
    return ops.get(comparison, ops["gt"])(value, threshold)


class AlertManager:
    def __init__(self) -> None:
        self._dispatchers: dict[str, Any] = {}

    def register_dispatcher(self, channel: AlertChannel, handler: Any) -> None:
        self._dispatchers[channel.value] = handler

    async def seed_prebuilt_rules(self, db: AsyncSession) -> None:
        for rule_data in PREBUILT_RULES:
            result = await db.execute(
                select(AlertRule).where(AlertRule.name == rule_data["name"])
            )
            if result.scalar_one_or_none() is None:
                db.add(AlertRule(**rule_data))
        await db.commit()

    async def evaluate_rules(
        self,
        db: AsyncSession,
        metrics: dict[str, dict[str, Any]],
    ) -> list[Alert]:
        result = await db.execute(select(AlertRule).where(AlertRule.is_active.is_(True)))
        rules = result.scalars().all()
        triggered: list[Alert] = []

        for rule in rules:
            metric_data = metrics.get(rule.metric)
            if metric_data is None:
                continue

            value: float = float(metric_data.get("value", 0))
            country_iso: Optional[str] = metric_data.get("country_iso")

            if not _compare(value, rule.threshold, rule.comparison):
                continue

            cooldown_cutoff = datetime.utcnow() - timedelta(minutes=rule.cooldown_minutes)
            recent = await db.execute(
                select(Alert).where(
                    Alert.rule_id == rule.id,
                    Alert.created_at >= cooldown_cutoff,
                )
            )
            if recent.scalar_one_or_none() is not None:
                continue

            alert = Alert(
                rule_id=rule.id,
                severity=rule.severity,
                title=rule.name,
                body=(
                    f"Metric '{rule.metric}' value {value} "
                    f"{'exceeded' if rule.comparison in ('gt', 'gte') else 'fell below'} "
                    f"threshold {rule.threshold}."
                ),
                channels=rule.channels,
                metric_value=value,
                threshold_value=rule.threshold,
                country_iso=country_iso or rule.country_iso,
                metadata_json=metric_data.get("metadata", {}),
            )
            db.add(alert)
            triggered.append(alert)

        if triggered:
            await db.commit()
            for alert in triggered:
                await self._dispatch(alert, db)
        return triggered

    async def _dispatch(self, alert: Alert, db: AsyncSession) -> None:
        channels: list[str] = alert.channels or []
        for channel_name in channels:
            handler = self._dispatchers.get(channel_name)
            status = "sent" if handler else "no_handler"
            response_body: Optional[str] = None

            if handler:
                try:
                    await handler(alert)
                except Exception as exc:
                    status = "failed"
                    response_body = str(exc)

            history = AlertHistory(
                alert_id=alert.id,
                channel=AlertChannel(channel_name) if channel_name in AlertChannel.__members__.values() else AlertChannel.IN_APP,
                status=status,
                response_body=response_body,
            )
            db.add(history)

        alert.dispatched = True
        await db.commit()

    async def get_alert_history(
        self,
        db: AsyncSession,
        country_iso: Optional[str] = None,
        severity: Optional[AlertSeverity] = None,
        limit: int = 50,
    ) -> list[Alert]:
        query = select(Alert)
        if country_iso:
            query = query.where(Alert.country_iso == country_iso)
        if severity:
            query = query.where(Alert.severity == severity)
        query = query.order_by(Alert.created_at.desc()).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_rules(self, db: AsyncSession) -> list[AlertRule]:
        result = await db.execute(select(AlertRule).order_by(AlertRule.name))
        return list(result.scalars().all())


alert_manager = AlertManager()
