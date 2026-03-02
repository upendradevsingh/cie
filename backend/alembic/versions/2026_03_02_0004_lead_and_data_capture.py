"""add lead and data capture question models

Revision ID: 2026_03_02_0004
Revises: 2026_03_02_0003
Create Date: 2026-03-02 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2026_03_02_0004'
down_revision: Union[str, None] = '2026_03_02_0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### Lead table ###
    op.create_table(
        'leads',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('lead_id', sa.String(length=255), nullable=False),
        sa.Column('lead_name', sa.String(length=255), nullable=True),
        sa.Column('lead_phone', sa.String(length=50), nullable=True),
        sa.Column('lead_email', sa.String(length=255), nullable=True),
        sa.Column('source', sa.String(length=127), nullable=True),
        sa.Column('total_calls', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('avg_quality_score', sa.Float(), nullable=True),
        sa.Column('avg_intent_score', sa.Float(), nullable=True),
        sa.Column('latest_intent_classification', sa.String(length=20), nullable=True),
        sa.Column('first_call_date', sa.DateTime(), nullable=True),
        sa.Column('latest_call_date', sa.DateTime(), nullable=True),
        sa.Column('quality_trend', sa.String(length=20), nullable=True),
        sa.Column('top_objections', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('all_tags', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('key_pain_points', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('competitors_mentioned', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('custom_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('latest_budget_score', sa.Float(), nullable=True),
        sa.Column('latest_authority_score', sa.Float(), nullable=True),
        sa.Column('latest_need_score', sa.Float(), nullable=True),
        sa.Column('latest_timeline_score', sa.Float(), nullable=True),
        sa.Column('latest_persona_type', sa.String(length=100), nullable=True),
        sa.Column('pending_action_items', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('completed_action_items', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('follow_up_urgency', sa.String(length=20), nullable=True),
        sa.Column('recommended_next_steps', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_leads_follow_up_urgency', 'leads', ['follow_up_urgency'], unique=False)
    op.create_index('ix_leads_latest_call_date', 'leads', ['latest_call_date'], unique=False)
    op.create_index('ix_leads_tenant_classification', 'leads', ['tenant_id', 'latest_intent_classification'], unique=False)
    op.create_index('ix_leads_tenant_id', 'leads', ['tenant_id'], unique=False)
    op.create_index('ix_leads_tenant_lead_id', 'leads', ['tenant_id', 'lead_id'], unique=True)

    # ### Data Capture Questions table ###
    op.create_table(
        'data_capture_questions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('field_name', sa.String(length=100), nullable=False),
        sa.Column('expected_type', sa.String(length=20), nullable=False, server_default='text'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_data_capture_questions_display_order', 'data_capture_questions', ['display_order'], unique=False)
    op.create_index('ix_data_capture_questions_tenant_active', 'data_capture_questions', ['tenant_id', 'is_active'], unique=False)
    op.create_index('ix_data_capture_questions_tenant_id', 'data_capture_questions', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_data_capture_questions_tenant_id', table_name='data_capture_questions')
    op.drop_index('ix_data_capture_questions_tenant_active', table_name='data_capture_questions')
    op.drop_index('ix_data_capture_questions_display_order', table_name='data_capture_questions')
    op.drop_table('data_capture_questions')

    op.drop_index('ix_leads_tenant_lead_id', table_name='leads')
    op.drop_index('ix_leads_tenant_id', table_name='leads')
    op.drop_index('ix_leads_tenant_classification', table_name='leads')
    op.drop_index('ix_leads_latest_call_date', table_name='leads')
    op.drop_index('ix_leads_follow_up_urgency', table_name='leads')
    op.drop_table('leads')
