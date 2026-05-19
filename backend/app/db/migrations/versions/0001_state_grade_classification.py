"""State-grade classification: baseline schema + RLS

Revision ID: 0001_state_grade
Revises:
Create Date: 2026-05-18 00:00:00.000000

Baseline schema for Global Intelligence. This migration creates every
table currently declared in ``app.models`` AND establishes the
state-grade classification controls:

* Adds classification / TLP / Admiralty / org_id / signature columns.
* Installs the ``pgvector`` extension.
* Creates ``app.set_user_context(clearance int, org_id uuid)`` which
  uses ``SET LOCAL`` to push request-scoped clearance into Postgres.
* Enables ROW LEVEL SECURITY on every classified table and adds a
  policy that compares the row classification against the session
  clearance, plus an optional org_id filter.

There is no prior Alembic history in the repository, so this revision
is the chain root. Future migrations must list this one as
``down_revision``.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0001_state_grade"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CLASSIFIED_TABLES = ("intelligence_items", "daily_reports", "premium_reports")


def _create_role_enum() -> postgresql.ENUM:
    return postgresql.ENUM("user", "institutional", "admin", name="roleenum")


def _create_plan_enum() -> postgresql.ENUM:
    return postgresql.ENUM("individual", "institutional", name="plantypeenum")


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------


def upgrade() -> None:
    # --- Extensions ------------------------------------------------------
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    role_enum = _create_role_enum()
    plan_enum = _create_plan_enum()
    role_enum.create(op.get_bind(), checkfirst=True)
    plan_enum.create(op.get_bind(), checkfirst=True)

    # --- Geography -------------------------------------------------------
    op.create_table(
        "continents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column("code", sa.String(), nullable=False, unique=True),
    )
    op.create_index("ix_continents_name", "continents", ["name"])

    op.create_table(
        "countries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "continent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("continents.id"),
        ),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column("iso_code", sa.String(), nullable=False, unique=True),
    )
    op.create_index("ix_countries_name", "countries", ["name"])

    op.create_table(
        "country_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "country_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("countries.id"),
            unique=True,
        ),
        sa.Column("overall_risk_score", sa.String(), nullable=True),
        sa.Column("metadata_json", sa.String(), nullable=True),
    )

    # --- Users / subscriptions ------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column(
            "role",
            sa.Enum("user", "institutional", "admin", name="roleenum", create_type=False),
            nullable=False,
            server_default="user",
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
        sa.Column("two_factor_enabled", sa.Boolean(), server_default=sa.false()),
        sa.Column("mfa_secret", sa.String(), nullable=True),
        sa.Column(
            "clearance_level",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_org_id", "users", ["org_id"])

    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            unique=True,
        ),
        sa.Column("stripe_customer_id", sa.String(), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(), nullable=True),
        sa.Column(
            "plan_type",
            sa.Enum(
                "individual",
                "institutional",
                name="plantypeenum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("status", sa.String(), server_default="inactive"),
        sa.Column("current_period_end", sa.DateTime(), nullable=True),
    )

    # --- Intelligence ----------------------------------------------------
    op.create_table(
        "intelligence_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
    )

    op.create_table(
        "intelligence_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "country_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("countries.id"),
        ),
        sa.Column(
            "category_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("intelligence_categories.id"),
        ),
        sa.Column("agent_source", sa.String(), nullable=False),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("confidence_score", sa.Float(), server_default="0.0"),
        sa.Column("metadata_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "classification",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "tlp",
            sa.String(),
            nullable=False,
            server_default="TLP:CLEAR",
        ),
        sa.Column("admiralty_reliability", sa.String(length=1), nullable=True),
        sa.Column("admiralty_credibility", sa.Integer(), nullable=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_intelligence_items_classification",
        "intelligence_items",
        ["classification"],
    )
    op.create_index(
        "ix_intelligence_items_org_id",
        "intelligence_items",
        ["org_id"],
    )

    op.create_table(
        "source_registry",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("url", sa.String(), nullable=False, unique=True),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("credibility_score", sa.Float(), server_default="0.5"),
        sa.Column("last_scraped", sa.DateTime(), nullable=True),
        sa.Column(
            "max_classification",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )

    # --- Reports ---------------------------------------------------------
    op.create_table(
        "daily_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "country_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("countries.id"),
        ),
        sa.Column(
            "report_date",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("executive_summary", sa.Text(), nullable=False),
        sa.Column("content_json", sa.Text(), nullable=False),
        sa.Column("published", sa.Boolean(), server_default=sa.false()),
        sa.Column(
            "classification",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "tlp",
            sa.String(),
            nullable=False,
            server_default="TLP:CLEAR",
        ),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("signature", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_daily_reports_classification",
        "daily_reports",
        ["classification"],
    )
    op.create_index("ix_daily_reports_org_id", "daily_reports", ["org_id"])

    op.create_table(
        "premium_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
        ),
        sa.Column("request_topic", sa.String(), nullable=False),
        sa.Column("content_markdown", sa.Text(), nullable=False),
        sa.Column("human_reviewed", sa.Boolean(), server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "classification",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "tlp",
            sa.String(),
            nullable=False,
            server_default="TLP:CLEAR",
        ),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("signature", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_premium_reports_classification",
        "premium_reports",
        ["classification"],
    )
    op.create_index("ix_premium_reports_org_id", "premium_reports", ["org_id"])

    op.create_table(
        "report_citations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_registry_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("source_registry.id"),
        ),
        sa.Column("report_type", sa.String(), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
    )

    # --- Interactions ----------------------------------------------------
    op.create_table(
        "chat_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
        ),
        sa.Column("report_bind_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chat_sessions.id"),
        ),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.create_table(
        "scenario_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
        ),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("input_variables", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("output_markdown", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.create_table(
        "contributor_submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("alias", sa.String(), nullable=True),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("country", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("actors", sa.String(), nullable=True),
        sa.Column("confidence", sa.String(), nullable=True),
        sa.Column("consent_recorded", sa.Boolean(), server_default=sa.false()),
        sa.Column("status", sa.String(), server_default="pending_review"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    # --- Session context helper -----------------------------------------
    # ``set_user_context`` is called at the start of every request to
    # push the caller's clearance / org into Postgres as session
    # variables. RLS policies then read those variables.
    op.execute(
        """
        CREATE SCHEMA IF NOT EXISTS app;

        CREATE OR REPLACE FUNCTION app.set_user_context(
            p_clearance integer,
            p_org_id uuid
        ) RETURNS void
        LANGUAGE plpgsql
        AS $$
        BEGIN
            PERFORM set_config('app.user_clearance', COALESCE(p_clearance, 0)::text, true);
            PERFORM set_config(
                'app.user_org_id',
                COALESCE(p_org_id::text, ''),
                true
            );
        END;
        $$;
        """
    )

    # --- Row Level Security ---------------------------------------------
    for table in _CLASSIFIED_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        # FORCE so even the table owner is subject to the policy unless
        # they explicitly opt out via BYPASSRLS.
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

        # Tenant isolation: fail CLOSED. If app.user_org_id is not set
        # by set_user_context() we deny access to any tenant-scoped row
        # (org_id IS NOT NULL). Globally-visible rows (org_id IS NULL)
        # remain accessible to any caller that meets the clearance bar.
        # WITH CHECK enforces both clearance AND tenant on write — a
        # caller cannot insert/update a row above their clearance, and
        # cannot move a row across tenants.
        op.execute(
            f"""
            CREATE POLICY {table}_clearance_org_isolation
            ON {table}
            USING (
                classification <= COALESCE(
                    NULLIF(current_setting('app.user_clearance', true), ''),
                    '0'
                )::int
                AND (
                    org_id IS NULL
                    OR (
                        NULLIF(current_setting('app.user_org_id', true), '') IS NOT NULL
                        AND org_id::text = current_setting('app.user_org_id', true)
                    )
                )
            )
            WITH CHECK (
                classification <= COALESCE(
                    NULLIF(current_setting('app.user_clearance', true), ''),
                    '0'
                )::int
                AND (
                    org_id IS NULL
                    OR (
                        NULLIF(current_setting('app.user_org_id', true), '') IS NOT NULL
                        AND org_id::text = current_setting('app.user_org_id', true)
                    )
                )
            )
            """
        )


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------


def downgrade() -> None:
    for table in _CLASSIFIED_TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_clearance_org_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.execute("DROP FUNCTION IF EXISTS app.set_user_context(integer, uuid)")
    op.execute("DROP SCHEMA IF EXISTS app")

    op.drop_table("contributor_submissions")
    op.drop_table("scenario_runs")
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
    op.drop_table("report_citations")
    op.drop_index("ix_premium_reports_org_id", table_name="premium_reports")
    op.drop_index("ix_premium_reports_classification", table_name="premium_reports")
    op.drop_table("premium_reports")
    op.drop_index("ix_daily_reports_org_id", table_name="daily_reports")
    op.drop_index("ix_daily_reports_classification", table_name="daily_reports")
    op.drop_table("daily_reports")
    op.drop_table("source_registry")
    op.drop_index("ix_intelligence_items_org_id", table_name="intelligence_items")
    op.drop_index(
        "ix_intelligence_items_classification", table_name="intelligence_items"
    )
    op.drop_table("intelligence_items")
    op.drop_table("intelligence_categories")
    op.drop_table("subscriptions")
    op.drop_index("ix_users_org_id", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.drop_table("country_profiles")
    op.drop_index("ix_countries_name", table_name="countries")
    op.drop_table("countries")
    op.drop_index("ix_continents_name", table_name="continents")
    op.drop_table("continents")

    _create_plan_enum().drop(op.get_bind(), checkfirst=True)
    _create_role_enum().drop(op.get_bind(), checkfirst=True)

    op.execute("DROP EXTENSION IF EXISTS vector")
