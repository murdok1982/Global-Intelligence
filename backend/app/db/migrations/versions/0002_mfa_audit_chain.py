"""MFA, recovery codes, WebAuthn skeleton, append-only audit chain.

Revision ID: 0002_mfa_audit_chain
Revises: 0001_state_grade
Create Date: 2026-05-18 12:00:00.000000

Adds:
    * mfa_recovery_codes table (bcrypt-hashed single-use codes).
    * webauthn_credentials table (P3 schema-only stub).
    * audit_events table with prev_hash / row_hash columns forming a
      tamper-evident chain.
    * Trigger ``audit_events_no_update_delete`` that aborts any
      UPDATE or DELETE on audit_events when the session role does
      not have ``BYPASSRLS``. Combined with the ``app_bypass_rls``
      role (created below) this keeps the chain append-only in the
      runtime path while still allowing operators to perform
      maintenance via the bypass role.
    * Genesis row inserted with deterministic prev_hash / row_hash so
      the application can verify the chain from boot.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0002_mfa_audit_chain"
down_revision: Union[str, None] = "0001_state_grade"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Pinned constants — also referenced by app.models.audit.
_GENESIS_PREV_HASH = "0" * 64
# sha256("GENESIS")
_GENESIS_ROW_HASH = (
    "901131d838b17aac0f7885b81e03cbdc9f5157a00343d30ab22083685ed1416a"
)


def upgrade() -> None:
    # --- MFA recovery codes ---------------------------------------------
    op.create_table(
        "mfa_recovery_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code_hash", sa.String(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_mfa_recovery_codes_user_id", "mfa_recovery_codes", ["user_id"]
    )

    # --- WebAuthn credentials (schema-only stub) -------------------------
    op.create_table(
        "webauthn_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("credential_id", sa.LargeBinary(), nullable=False, unique=True),
        sa.Column("public_key", sa.LargeBinary(), nullable=False),
        sa.Column(
            "sign_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("transports", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_webauthn_credentials_user_id", "webauthn_credentials", ["user_id"]
    )

    # --- Audit events ---------------------------------------------------
    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "actor_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("actor_ip", sa.String(length=45), nullable=True),
        sa.Column("actor_user_agent", sa.String(), nullable=True),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("resource_type", sa.String(), nullable=True),
        sa.Column("resource_id", sa.String(), nullable=True),
        sa.Column("classification", sa.Integer(), nullable=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("outcome", sa.String(), nullable=False),
        sa.Column(
            "metadata_json",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("prev_hash", sa.String(length=64), nullable=False),
        sa.Column("row_hash", sa.String(length=64), nullable=False, unique=True),
    )
    op.create_index("ix_audit_events_timestamp", "audit_events", ["timestamp"])
    op.create_index(
        "ix_audit_events_actor_user_id", "audit_events", ["actor_user_id"]
    )
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])
    op.create_index("ix_audit_events_resource_id", "audit_events", ["resource_id"])
    op.create_index("ix_audit_events_org_id", "audit_events", ["org_id"])

    # --- BYPASSRLS maintenance role -------------------------------------
    # Created if missing. Application runtime must NEVER connect with
    # this role — only out-of-band ops (audit pruning policy review,
    # forensic dumps, schema migrations). See docs/OPERATIONS.md.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_bypass_rls') THEN
                CREATE ROLE app_bypass_rls
                    NOLOGIN
                    BYPASSRLS
                    NOSUPERUSER
                    NOCREATEDB
                    NOCREATEROLE
                    NOINHERIT;
            END IF;
        END
        $$;
        """
    )

    # --- Append-only trigger --------------------------------------------
    # UPDATEs and DELETEs from any role that does NOT have BYPASSRLS are
    # blocked at the database layer. The trigger reads the connected
    # role's catalog flag rather than a session variable so it cannot be
    # subverted by SET commands.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION audit_events_no_update_delete()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            v_bypass boolean;
        BEGIN
            SELECT rolbypassrls INTO v_bypass
              FROM pg_roles
             WHERE rolname = current_user;
            IF v_bypass IS DISTINCT FROM TRUE THEN
                RAISE EXCEPTION USING
                    ERRCODE = '42501',
                    MESSAGE = 'audit_events is append-only',
                    DETAIL  = format(
                        'Operation %s on audit_events denied for role %s',
                        TG_OP, current_user
                    );
            END IF;
            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            END IF;
            RETURN NEW;
        END;
        $$;

        DROP TRIGGER IF EXISTS audit_events_no_update_delete_trg ON audit_events;
        CREATE TRIGGER audit_events_no_update_delete_trg
            BEFORE UPDATE OR DELETE ON audit_events
            FOR EACH ROW
            EXECUTE FUNCTION audit_events_no_update_delete();
        """
    )

    # --- Genesis row ----------------------------------------------------
    op.execute(
        sa.text(
            """
            INSERT INTO audit_events (
                id, timestamp, event_type, outcome,
                prev_hash, row_hash
            ) VALUES (
                '00000000-0000-0000-0000-000000000001',
                CURRENT_TIMESTAMP,
                'audit.genesis',
                'success',
                :prev,
                :row
            )
            """
        ).bindparams(prev=_GENESIS_PREV_HASH, row=_GENESIS_ROW_HASH)
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_events_no_update_delete_trg ON audit_events")
    op.execute("DROP FUNCTION IF EXISTS audit_events_no_update_delete()")

    op.drop_index("ix_audit_events_org_id", table_name="audit_events")
    op.drop_index("ix_audit_events_resource_id", table_name="audit_events")
    op.drop_index("ix_audit_events_event_type", table_name="audit_events")
    op.drop_index("ix_audit_events_actor_user_id", table_name="audit_events")
    op.drop_index("ix_audit_events_timestamp", table_name="audit_events")
    op.drop_table("audit_events")

    op.drop_index("ix_webauthn_credentials_user_id", table_name="webauthn_credentials")
    op.drop_table("webauthn_credentials")

    op.drop_index("ix_mfa_recovery_codes_user_id", table_name="mfa_recovery_codes")
    op.drop_table("mfa_recovery_codes")

    # We leave app_bypass_rls in place — dropping a role used by
    # operations would be surprising on downgrade. Document the
    # cleanup separately if a full teardown is needed.
