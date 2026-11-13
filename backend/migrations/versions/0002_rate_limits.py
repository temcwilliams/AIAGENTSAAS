"""Shared-worker request limits, independent of successful usage records."""
from alembic import op
import sqlalchemy as sa
revision = '0002'
down_revision = '0001'

def upgrade():
    op.create_table('rate_limit_buckets',
        sa.Column('key',sa.String(64),primary_key=True),
        sa.Column('count',sa.Integer(),nullable=False),
        sa.Column('reset_at',sa.DateTime(),nullable=False),
        sa.CheckConstraint('count >= 0'))

def downgrade():
    op.drop_table('rate_limit_buckets')
