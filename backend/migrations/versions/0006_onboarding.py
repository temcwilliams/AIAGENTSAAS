"""Versioned tenant onboarding with approved, transactional publication."""
from alembic import op
import sqlalchemy as sa
revision='0006'
down_revision='0005'

def upgrade():
    with op.batch_alter_table('knowledge_documents') as batch:
        batch.create_unique_constraint('uq_knowledge_id_business',['id','business_id'])
    op.create_table('onboarding_drafts',
        sa.Column('business_id',sa.String(36),sa.ForeignKey('businesses.id'),primary_key=True),
        sa.Column('version',sa.Integer(),nullable=False),
        sa.Column('status',sa.String(20),nullable=False),
        sa.Column('profile',sa.JSON(),nullable=False),
        sa.Column('reviewer_notes',sa.Text(),nullable=False),
        sa.Column('agent_id',sa.String(36),nullable=True),
        sa.Column('knowledge_id',sa.String(36),nullable=True),
        sa.Column('published_source_version',sa.Integer(),nullable=True),
        sa.Column('reviewed_by',sa.String(36),sa.ForeignKey('users.id'),nullable=True),
        sa.Column('published_by',sa.String(36),sa.ForeignKey('users.id'),nullable=True),
        sa.Column('template_version',sa.Integer(),nullable=False),
        sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('submitted_at',sa.DateTime(timezone=True),nullable=True),
        sa.Column('published_at',sa.DateTime(timezone=True),nullable=True),
        sa.ForeignKeyConstraint(['agent_id','business_id'],['agents.id','agents.business_id']),
        sa.ForeignKeyConstraint(['knowledge_id','business_id'],['knowledge_documents.id','knowledge_documents.business_id']),
        sa.CheckConstraint('version >= 1'),
        sa.CheckConstraint("status IN ('draft','submitted','changes_requested','approved','published')"))

def downgrade():
    op.drop_table('onboarding_drafts')
    with op.batch_alter_table('knowledge_documents') as batch:
        batch.drop_constraint('uq_knowledge_id_business',type_='unique')
