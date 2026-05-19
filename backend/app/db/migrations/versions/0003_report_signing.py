"""Report signing fields + Stripe cleanup.

Revision ID: 0003_report_signing
Revises: 0002_mfa_audit_chain
Create Date: 2026-05-19 00:00:00.000000

Changes:
    * Adds ``signed_at`` (DateTime, nullable) and
      ``signature_fingerprint`` (String(16), nullable, indexed) to
      ``daily_reports`` and ``premium_reports``. The pre-existing
      ``signature`` column from migration 0001 holds the base64 blob.
      The fingerprint index lets operators identify every report
      signed by a specific (potentially revoked) public key.
    * Drops the legacy ``subscriptions`` table and the
      ``plantypeenum`` Postgres enum that only ``Subscription`` used.
      Stripe was removed from the backend in P4.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0003_report_signing"
down_revision: Union[str, None] = "0002_mfa_audit_chain"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Signing fields on daily_reports / premium_reports
    # ------------------------------------------------------------------
    op.add_column(
        "daily_reports",
        sa.Column("signed_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "daily_reports",
        sa.Column(
            "signature_fingerprint", sa.String(length=16), nullable=True
        ),
    )
    op.create_index(
        "ix_daily_reports_signature_fingerprint",
        "daily_reports",
        ["signature_fingerprint"],
    )

    op.add_column(
        "premium_reports",
        sa.Column("signed_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "premium_reports",
        sa.Column(
            "signature_fingerprint", sa.String(length=16), nullable=True
        ),
    )
    op.create_index(
        "ix_premium_reports_signature_fingerprint",
        "premium_reports",
        ["signature_fingerprint"],
    )

    # ------------------------------------------------------------------
    # Stripe cleanup — drop subscriptions table and its enum.
    # ------------------------------------------------------------------
    # Drop the table only if it exists (some test DBs may not have it).
    op.execute("DROP TABLE IF EXISTS subscriptions CASCADE")
    # The enum was created in 0001 and was used solely by subscriptions.
    op.execute("DROP TYPE IF EXISTS plantypeenum")


def downgrade() -> None:
    # ------------------------------------------------------------------
    # Recreate the subscriptions table and plantypeenum so a downgrade
    # leaves the schema usable by clients pinned to 0002.
    # ------------------------------------------------------------------
    op.execute(
        "CREATE TYPE plantypeenum AS ENUM ('individual', 'institutional')"
    )
    op.create_table(
        "subscriptions",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True)  # type: ignore[attr-defined]
            if hasattr(sa.dialects, "postgresql")
            else sa.String(),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True)  # type: ignore[attr-defined]
            if hasattr(sa.dialects, "postgresql")
            else sa.String(),
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

    # ------------------------------------------------------------------
    # Drop signing columns + indices on the reports tables.
    # ------------------------------------------------------------------
    op.drop_index(
        "ix_premium_reports_signature_fingerprint",
        table_name="premium_reports",
    )
    op.drop_column("premium_reports", "signature_fingerprint")
    op.drop_column("premium_reports", "signed_at")

    op.drop_index(
        "ix_daily_reports_signature_fingerprint",
        table_name="daily_reports",
    )
    op.drop_column("daily_reports", "signature_fingerprint")
    op.drop_column("daily_reports", "signed_at")
