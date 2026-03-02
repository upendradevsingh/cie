"""Enable Row-Level Security on all tenant-scoped tables.

Revision ID: 0001_enable_rls
Revises:
Create Date: 2026-03-02

Enables RLS + FORCE RLS on every table that stores tenant data, and creates
``tenant_isolation`` policies so that queries only return rows belonging to
the tenant identified by ``current_setting('app.current_tenant_id')``.

Tables with a direct ``tenant_id`` column use a simple equality check.
Child tables that inherit tenancy through ``calls.tenant_id`` (via
``call_id`` FK) use a sub-select against ``calls``.

The ``tenants`` table itself is intentionally excluded — it is the root
entity and must remain accessible without RLS.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0001_enable_rls"
down_revision = None
branch_labels = None
depends_on = None

# Tables with a direct tenant_id column.
_DIRECT_TENANT_TABLES = [
    "users",
    "calls",
    "quality_parameters",
    "intent_signals",
    "persona_types",
    "weekly_reports",
    "integrations",
    "api_keys",
]

# Tables that inherit tenancy through a call_id FK → calls.tenant_id.
_CHILD_OF_CALLS_TABLES = [
    "call_quality_scores",
    "call_intent_signals",
    "call_personas",
    "action_items",
]


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Tables with direct tenant_id column
    # ------------------------------------------------------------------
    for table in _DIRECT_TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {table}
                USING (
                    tenant_id = current_setting('app.current_tenant_id', true)::uuid
                )
            """
        )

    # ------------------------------------------------------------------
    # Child tables (no tenant_id; inherit via call_id → calls)
    # ------------------------------------------------------------------
    for table in _CHILD_OF_CALLS_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {table}
                USING (
                    call_id IN (
                        SELECT id FROM calls
                        WHERE tenant_id = current_setting('app.current_tenant_id', true)::uuid
                    )
                )
            """
        )


def downgrade() -> None:
    all_tables = _DIRECT_TENANT_TABLES + _CHILD_OF_CALLS_TABLES

    for table in all_tables:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
