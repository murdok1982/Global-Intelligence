"""Schemas for military equipment database API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class WeaponSystemBase(BaseModel):
    name: str = Field(..., max_length=200)
    designation: Optional[str] = Field(None, max_length=100)
    category: str = Field(..., max_length=50)
    origin: str = Field(..., max_length=50)
    manufacturer: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    service_entry_year: Optional[int] = None
    is_active: bool = True
    nato_reporting_name: Optional[str] = Field(None, max_length=100)
    unit_cost_usd: Optional[float] = None
    technical_specs: dict[str, Any] = Field(default_factory=dict)
    performance_data: dict[str, Any] = Field(default_factory=dict)
    source_urls: list[str] = Field(default_factory=list)


class WeaponSystemCreate(WeaponSystemBase):
    pass


class WeaponSystemResponse(WeaponSystemBase):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class WeaponSystemList(BaseModel):
    items: list[WeaponSystemResponse]
    total: int
    page: int
    size: int


class WeaponOperatorResponse(BaseModel):
    id: UUID
    weapon_id: UUID
    country_iso: str
    country_name: str
    quantity: Optional[int] = None
    quantity_source_year: Optional[int] = None
    operational_status: Optional[str] = None
    acquisition_type: Optional[str] = None
    source: Optional[str] = None

    model_config = {"from_attributes": True}


class ArmsTransferResponse(BaseModel):
    id: UUID
    supplier_country: str
    supplier_iso: str
    recipient_country: str
    recipient_iso: str
    weapon_category: Optional[str] = None
    weapon_description: str
    quantity: Optional[int] = None
    deal_value_usd: Optional[float] = None
    agreement_year: Optional[int] = None
    delivery_year: Optional[int] = None
    deal_type: Optional[str] = None
    status: Optional[str] = None
    source: Optional[str] = None

    model_config = {"from_attributes": True}


class ArmsTransferList(BaseModel):
    items: list[ArmsTransferResponse]
    total: int


class MilitaryBaseResponse(BaseModel):
    id: UUID
    name: str
    country_iso: str
    country_name: str
    base_type: str
    latitude: float
    longitude: float
    personnel_count: Optional[int] = None
    facilities: list[str] = Field(default_factory=list)
    is_foreign_hosted: bool = False
    host_country_iso: Optional[str] = None
    host_country_name: Optional[str] = None
    strategic_importance: Optional[str] = None

    model_config = {"from_attributes": True}


class MilitaryBaseList(BaseModel):
    items: list[MilitaryBaseResponse]
    total: int


class DefenseBudgetResponse(BaseModel):
    id: UUID
    country_iso: str
    country_name: str
    fiscal_year: int
    budget_usd: Optional[float] = None
    gdp_percentage: Optional[float] = None
    source: Optional[str] = None

    model_config = {"from_attributes": True}


class DefenseBudgetList(BaseModel):
    items: list[DefenseBudgetResponse]
    total: int


class MilitaryStatsResponse(BaseModel):
    total_weapons: int
    total_transfers: int
    total_bases: int
    total_budgets: int
    top_suppliers: list[dict[str, Any]]
    top_recipients: list[dict[str, Any]]
    global_defense_spend_usd: float


__all__ = [
    "WeaponSystemBase",
    "WeaponSystemCreate",
    "WeaponSystemResponse",
    "WeaponSystemList",
    "WeaponOperatorResponse",
    "ArmsTransferResponse",
    "ArmsTransferList",
    "MilitaryBaseResponse",
    "MilitaryBaseList",
    "DefenseBudgetResponse",
    "DefenseBudgetList",
    "MilitaryStatsResponse",
]
