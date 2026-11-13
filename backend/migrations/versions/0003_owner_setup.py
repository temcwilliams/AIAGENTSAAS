"""Atomic, one-time platform owner registration claim."""
from alembic import op
import sqlalchemy as sa
revision='0003'
down_revision='0002'

def upgrade():
    op.create_table('owner_setup',sa.Column('id',sa.String(32),primary_key=True),sa.Column('completed_at',sa.DateTime(),nullable=False))

def downgrade():
    op.drop_table('owner_setup')
