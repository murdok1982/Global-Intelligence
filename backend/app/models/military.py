"""
Military Equipment Database Models

Structured data for weapons systems, platforms, and military capabilities.
Data sourced from: SIPRI, Jane's, IISS Military Balance, GlobalSecurity.org
"""

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
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
import enum
import uuid

from app.db.base import Base


class WeaponCategory(str, enum.Enum):
    AIRCRAFT = "aircraft"
    HELICOPTER = "helicopter"
    UAV = "uav"
    TANK = "tank"
    APC = "apc"
    IFV = "ifv"
    ARTILLERY = "artillery"
    MLRS = "mlrs"
    MISSILE_ATGM = "missile_atgm"
    MISSILE_AAM = "missile_aam"
    MISSILE_AGM = "missile_agm"
    MISSILE_CRUISE = "missile_cruise"
    MISSILE_BALLISTIC = "missile_ballistic"
    MISSILE_SAM = "missile_sam"
    SHIP_CARRIER = "ship_carrier"
    SHIP_DESTROYER = "ship_destroyer"
    SHIP_FRIGATE = "ship_frigate"
    SHIP_CORVETTE = "ship_corvette"
    SHIP_SUBMARINE = "ship_submarine"
    SHIP_PATROL = "ship_patrol"
    RADAR = "radar"
    EW_SYSTEM = "ew_system"
    CBRN = "cbrn"
    SMALL_ARM = "small_arm"


class WeaponOrigin(str, enum.Enum):
    USA = "USA"
    RUSSIA = "Russia"
    CHINA = "China"
    UK = "UK"
    FRANCE = "France"
    GERMANY = "Germany"
    ITALY = "Italy"
    ISRAEL = "Israel"
    SOUTH_KOREA = "South Korea"
    JAPAN = "Japan"
    INDIA = "India"
    TURKEY = "Turkey"
    BRAZIL = "Brazil"
    SWEDEN = "Sweden"
    UKRAINE = "Ukraine"
    OTHER = "Other"


class WeaponSystem(Base):
    __tablename__ = "weapon_systems"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, index=True)
    designation = Column(String(100), index=True)
    category = Column(Enum(WeaponCategory), nullable=False, index=True)
    origin = Column(Enum(WeaponOrigin), nullable=False, index=True)
    manufacturer = Column(String(200))
    
    technical_specs = Column(JSONB, default=dict)
    performance_data = Column(JSONB, default=dict)
    
    description = Column(Text)
    service_entry_year = Column(Integer)
    is_active = Column(Boolean, default=True)
    
    nato_reporting_name = Column(String(100))
    nsn_number = Column(String(50))
    
    unit_cost_usd = Column(Float)
    production_count = Column(Integer)
    
    thumbnail_url = Column(String(500))
    source_urls = Column(JSONB, default=list)
    
    classification = Column(String(20), default="PUBLIC")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    operators = relationship("WeaponOperator", back_populates="weapon")
    variants = relationship("WeaponVariant", back_populates="parent_weapon")


class WeaponVariant(Base):
    __tablename__ = "weapon_variants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    weapon_id = Column(UUID(as_uuid=True), ForeignKey("weapon_systems.id"), nullable=False)
    variant_name = Column(String(200), nullable=False)
    variant_designation = Column(String(100))
    
    differences = Column(Text)
    technical_specs_delta = Column(JSONB, default=dict)
    
    service_entry_year = Column(Integer)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    parent_weapon = relationship("WeaponSystem", back_populates="variants")


class WeaponOperator(Base):
    __tablename__ = "weapon_operators"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    weapon_id = Column(UUID(as_uuid=True), ForeignKey("weapon_systems.id"), nullable=False)
    country_iso = Column(String(3), nullable=False, index=True)
    country_name = Column(String(100), nullable=False)
    
    quantity = Column(Integer)
    quantity_source_year = Column(Integer)
    operational_status = Column(String(50))
    
    acquisition_date = Column(DateTime(timezone=True))
    acquisition_type = Column(String(50))
    
    notes = Column(Text)
    source = Column(String(200))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    weapon = relationship("WeaponSystem", back_populates="operators")


class ArmsTransfer(Base):
    __tablename__ = "arms_transfers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    supplier_country = Column(String(100), nullable=False, index=True)
    supplier_iso = Column(String(3), index=True)
    recipient_country = Column(String(100), nullable=False, index=True)
    recipient_iso = Column(String(3), index=True)
    
    weapon_category = Column(Enum(WeaponCategory), index=True)
    weapon_description = Column(String(500), nullable=False)
    
    quantity = Column(Integer)
    deal_value_usd = Column(Float)
    
    agreement_year = Column(Integer)
    delivery_year = Column(Integer)
    
    deal_type = Column(String(50))
    status = Column(String(50), default="delivered")
    
    source = Column(String(200))
    source_url = Column(String(500))
    
    notes = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MilitaryUnit(Base):
    __tablename__ = "military_units"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    country_iso = Column(String(3), nullable=False, index=True)
    country_name = Column(String(100), nullable=False)
    
    unit_name = Column(String(200), nullable=False)
    unit_type = Column(String(100), index=True)
    unit_size = Column(String(50))
    
    branch = Column(String(50), index=True)
    
    garrison_location = Column(String(200))
    latitude = Column(Float)
    longitude = Column(Float)
    
    personnel_count = Column(Integer)
    
    primary_equipment = Column(JSONB, default=list)
    
    operational_status = Column(String(50))
    readiness_level = Column(String(50))
    
    source = Column(String(200))
    source_date = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MilitaryBase(Base):
    __tablename__ = "military_bases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    country_iso = Column(String(3), nullable=False, index=True)
    country_name = Column(String(100), nullable=False)
    
    base_type = Column(String(100), index=True)
    
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    personnel_count = Column(Integer)
    
    facilities = Column(JSONB, default=list)
    
    is_foreign_hosted = Column(Boolean, default=False)
    host_country_iso = Column(String(3))
    host_country_name = Column(String(100))
    
    strategic_importance = Column(String(50))
    
    source = Column(String(200))
    source_url = Column(String(500))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DefenseBudget(Base):
    __tablename__ = "defense_budgets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    country_iso = Column(String(3), nullable=False, index=True)
    country_name = Column(String(100), nullable=False)
    
    fiscal_year = Column(Integer, nullable=False, index=True)
    
    budget_usd = Column(Float)
    budget_local_currency = Column(Float)
    local_currency_code = Column(String(10))
    
    gdp_percentage = Column(Float)
    
    personnel_spending = Column(Float)
    equipment_spending = Column(Float)
    rd_spending = Column(Float)
    infrastructure_spending = Column(Float)
    
    source = Column(String(200))
    source_url = Column(String(500))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())


__all__ = [
    "WeaponCategory",
    "WeaponOrigin",
    "WeaponSystem",
    "WeaponVariant",
    "WeaponOperator",
    "ArmsTransfer",
    "MilitaryUnit",
    "MilitaryBase",
    "DefenseBudget",
]
