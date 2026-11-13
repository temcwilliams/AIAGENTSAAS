"""Tenant knowledge, cited responses, consented contact capture, and handoff."""
from alembic import op
import sqlalchemy as sa
revision='0004'
down_revision='0003'

def upgrade():
    op.create_table('knowledge_documents',sa.Column('id',sa.String(36),primary_key=True),sa.Column('business_id',sa.String(36),sa.ForeignKey('businesses.id'),nullable=False),sa.Column('title',sa.String(200),nullable=False),sa.Column('content',sa.Text(),nullable=False),sa.Column('enabled',sa.Boolean(),nullable=False),sa.Column('created_at',sa.DateTime(),nullable=False))
    op.create_index('ix_knowledge_documents_business_id','knowledge_documents',['business_id'])
    op.add_column('conversations',sa.Column('status',sa.String(16),nullable=False,server_default='ai'))
    op.add_column('conversations',sa.Column('handoff_reason',sa.Text(),nullable=False,server_default=''))
    op.add_column('conversations',sa.Column('handoff_requested_at',sa.DateTime(),nullable=True))
    op.add_column('messages',sa.Column('sources',sa.JSON(),nullable=False,server_default='[]'))
    with op.batch_alter_table('leads') as batch:
        batch.add_column(sa.Column('conversation_id',sa.String(36),nullable=True))
        batch.add_column(sa.Column('source',sa.String(12),nullable=False,server_default='manual'))
        batch.create_foreign_key('fk_lead_conversation_tenant','conversations',['conversation_id','business_id'],['id','business_id'])
    op.create_index('uq_conversation_lead_email','leads',['business_id','conversation_id','email'],unique=True)

def downgrade():
    op.drop_index('uq_conversation_lead_email',table_name='leads')
    with op.batch_alter_table('leads') as batch:
        batch.drop_constraint('fk_lead_conversation_tenant',type_='foreignkey')
        batch.drop_column('source');batch.drop_column('conversation_id')
    op.drop_column('messages','sources')
    op.drop_column('conversations','handoff_requested_at')
    op.drop_column('conversations','handoff_reason')
    op.drop_column('conversations','status')
    op.drop_index('ix_knowledge_documents_business_id',table_name='knowledge_documents')
    op.drop_table('knowledge_documents')
