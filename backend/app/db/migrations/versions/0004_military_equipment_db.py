"""0004_military_equipment_db

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-08

Creates tables for military equipment database:
- weapon_systems, weapon_variants, weapon_operators
- arms_transfers, military_units, military_bases
- defense_budgets
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "weapon_systems",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False, index=True),
        sa.Column("designation", sa.String(100), index=True),
        sa.Column("category", sa.String(50), nullable=False, index=True),
        sa.Column("origin", sa.String(50), nullable=False, index=True),
        sa.Column("manufacturer", sa.String(200)),
        sa.Column("technical_specs", JSONB, server_default="{}"),
        sa.Column("performance_data", JSONB, server_default="{}"),
        sa.Column("description", sa.Text),
        sa.Column("service_entry_year", sa.Integer),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("nato_reporting_name", sa.String(100)),
        sa.Column("nsn_number", sa.String(50)),
        sa.Column("unit_cost_usd", sa.Float),
        sa.Column("production_count", sa.Integer),
        sa.Column("thumbnail_url", sa.String(500)),
        sa.Column("source_urls", JSONB, server_default="[]"),
        sa.Column("classification", sa.String(20), server_default="'PUBLIC'"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "weapon_variants",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("weapon_id", UUID(as_uuid=True), sa.ForeignKey("weapon_systems.id"), nullable=False),
        sa.Column("variant_name", sa.String(200), nullable=False),
        sa.Column("variant_designation", sa.String(100)),
        sa.Column("differences", sa.Text),
        sa.Column("technical_specs_delta", JSONB, server_default="{}"),
        sa.Column("service_entry_year", sa.Integer),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "weapon_operators",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("weapon_id", UUID(as_uuid=True), sa.ForeignKey("weapon_systems.id"), nullable=False),
        sa.Column("country_iso", sa.String(3), nullable=False, index=True),
        sa.Column("country_name", sa.String(100), nullable=False),
        sa.Column("quantity", sa.Integer),
        sa.Column("quantity_source_year", sa.Integer),
        sa.Column("operational_status", sa.String(50)),
        sa.Column("acquisition_date", sa.DateTime(timezone=True)),
        sa.Column("acquisition_type", sa.String(50)),
        sa.Column("notes", sa.Text),
        sa.Column("source", sa.String(200)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "arms_transfers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("supplier_country", sa.String(100), nullable=False, index=True),
        sa.Column("supplier_iso", sa.String(3), index=True),
        sa.Column("recipient_country", sa.String(100), nullable=False, index=True),
        sa.Column("recipient_iso", sa.String(3), index=True),
        sa.Column("weapon_category", sa.String(50), index=True),
        sa.Column("weapon_description", sa.String(500), nullable=False),
        sa.Column("quantity", sa.Integer),
        sa.Column("deal_value_usd", sa.Float),
        sa.Column("agreement_year", sa.Integer),
        sa.Column("delivery_year", sa.Integer),
        sa.Column("deal_type", sa.String(50)),
        sa.Column("status", sa.String(50), server_default="'delivered'"),
        sa.Column("source", sa.String(200)),
        sa.Column("source_url", sa.String(500)),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "military_units",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("country_iso", sa.String(3), nullable=False, index=True),
        sa.Column("country_name", sa.String(100), nullable=False),
        sa.Column("unit_name", sa.String(200), nullable=False),
        sa.Column("unit_type", sa.String(100), index=True),
        sa.Column("unit_size", sa.String(50)),
        sa.Column("branch", sa.String(50), index=True),
        sa.Column("garrison_location", sa.String(200)),
        sa.Column("latitude", sa.Float),
        sa.Column("longitude", sa.Float),
        sa.Column("personnel_count", sa.Integer),
        sa.Column("primary_equipment", JSONB, server_default="[]"),
        sa.Column("operational_status", sa.String(50)),
        sa.Column("readiness_level", sa.String(50)),
        sa.Column("source", sa.String(200)),
        sa.Column("source_date", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "military_bases",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("country_iso", sa.String(3), nullable=False, index=True),
        sa.Column("country_name", sa.String(100), nullable=False),
        sa.Column("base_type", sa.String(100), index=True),
        sa.Column("latitude", sa.Float, nullable=False),
        sa.Column("longitude", sa.Float, nullable=False),
        sa.Column("personnel_count", sa.Integer),
        sa.Column("facilities", JSONB, server_default="[]"),
        sa.Column("is_foreign_hosted", sa.Boolean, server_default="false"),
        sa.Column("host_country_iso", sa.String(3)),
        sa.Column("host_country_name", sa.String(100)),
        sa.Column("strategic_importance", sa.String(50)),
        sa.Column("source", sa.String(200)),
        sa.Column("source_url", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "defense_budgets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("country_iso", sa.String(3), nullable=False, index=True),
        sa.Column("country_name", sa.String(100), nullable=False),
        sa.Column("fiscal_year", sa.Integer, nullable=False, index=True),
        sa.Column("budget_usd", sa.Float),
        sa.Column("budget_local_currency", sa.Float),
        sa.Column("local_currency_code", sa.String(10)),
        sa.Column("gdp_percentage", sa.Float),
        sa.Column("personnel_spending", sa.Float),
        sa.Column("equipment_spending", sa.Float),
        sa.Column("rd_spending", sa.Float),
        sa.Column("infrastructure_spending", sa.Float),
        sa.Column("source", sa.String(200)),
        sa.Column("source_url", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("ix_arms_transfers_year", "arms_transfers", ["agreement_year"])
    op.create_index("ix_defense_budgets_country_year", "defense_budgets", ["country_iso", "fiscal_year"])
    op.create_index("ix_weapon_operators_country", "weapon_operators", ["country_iso", "weapon_id"])


def downgrade() -> None:
    op.drop_table("defense_budgets")
    op.drop_table("military_bases")
    op.drop_table("military_units")
    op.drop_table("arms_transfers")
    op.drop_table("weapon_operators")
    op.drop_table("weapon_variants")
    op.drop_table("weapon_systems")
