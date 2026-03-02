"""Add sales_audit_keywords JSON column to calls table.

Revision ID: 0003_sales_audit_keywords
Revises: 0002_enhanced_analysis
Create Date: 2026-03-02

Adds a single JSON column to store categorised audit keywords extracted
by the LLM during call analysis.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0003_sales_audit_keywords"
down_revision = "0002_enhanced_analysis"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "calls",
        sa.Column("sales_audit_keywords", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("calls", "sales_audit_keywords")
