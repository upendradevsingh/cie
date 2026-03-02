"""Add enhanced analysis fields and prompt_templates table.

Revision ID: 0002_enhanced_analysis
Revises: 0001_enable_rls
Create Date: 2026-03-02

1. Add escalation_keywords (JSON), sentiment_keywords (JSON), call_tags (JSON)
   columns to the calls table.
2. Create the prompt_templates table for tenant-configurable LLM prompts.
3. Enable RLS on prompt_templates.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "0002_enhanced_analysis"
down_revision = "0001_enable_rls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Add new JSON columns to calls table
    # ------------------------------------------------------------------
    op.add_column(
        "calls",
        sa.Column("escalation_keywords", sa.JSON(), nullable=True),
    )
    op.add_column(
        "calls",
        sa.Column("sentiment_keywords", sa.JSON(), nullable=True),
    )
    op.add_column(
        "calls",
        sa.Column("call_tags", sa.JSON(), nullable=True),
    )

    # ------------------------------------------------------------------
    # 2. Create prompt_templates table
    # ------------------------------------------------------------------
    op.create_table(
        "prompt_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("template_content", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "name",
            name="uq_prompt_templates_tenant_name_active",
        ),
    )
    op.create_index(
        "ix_prompt_templates_tenant_name",
        "prompt_templates",
        ["tenant_id", "name"],
    )

    # ------------------------------------------------------------------
    # 3. Enable RLS on prompt_templates
    # ------------------------------------------------------------------
    op.execute("ALTER TABLE prompt_templates ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE prompt_templates FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON prompt_templates
            USING (
                tenant_id = current_setting('app.current_tenant_id', true)::uuid
            )
        """
    )


def downgrade() -> None:
    # RLS
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON prompt_templates")
    op.execute("ALTER TABLE prompt_templates DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE prompt_templates NO FORCE ROW LEVEL SECURITY")

    # Table
    op.drop_index("ix_prompt_templates_tenant_name", table_name="prompt_templates")
    op.drop_table("prompt_templates")

    # Columns
    op.drop_column("calls", "call_tags")
    op.drop_column("calls", "sentiment_keywords")
    op.drop_column("calls", "escalation_keywords")
