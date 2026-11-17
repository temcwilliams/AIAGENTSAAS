"""Account action tokens, disabled state and scoped memberships."""
from alembic import op
import sqlalchemy as sa
revision='0005'
down_revision='0004'

def upgrade():
    with op.batch_alter_table('users') as batch:
        batch.add_column(sa.Column('email_verified_at',sa.DateTime(timezone=True),nullable=True))
        batch.add_column(sa.Column('disabled',sa.Boolean(),nullable=False,server_default=sa.false()))
        batch.create_unique_constraint('uq_users_id_business',['id','business_id'])
    op.create_table('memberships',
        sa.Column('business_id',sa.String(36),sa.ForeignKey('businesses.id'),primary_key=True),
        sa.Column('user_id',sa.String(36),primary_key=True),
        sa.Column('role',sa.String(12),nullable=False),
        sa.ForeignKeyConstraint(['user_id','business_id'],['users.id','users.business_id']),
        sa.CheckConstraint("role IN ('viewer','responder','manager')"))
    op.execute("INSERT INTO memberships (business_id,user_id,role) SELECT business_id,id,'viewer' FROM users WHERE role='client'")
    op.create_table('action_tokens',
        sa.Column('token_hash',sa.String(64),primary_key=True),
        sa.Column('user_id',sa.String(36),sa.ForeignKey('users.id'),nullable=False),
        sa.Column('purpose',sa.String(12),nullable=False),
        sa.Column('expires_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('consumed_at',sa.DateTime(timezone=True),nullable=True),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('delivery_status',sa.String(12),nullable=False),
        sa.CheckConstraint("purpose IN ('reset','verify','setup')"),
        sa.CheckConstraint("delivery_status IN ('pending','sent','failed')"))
    op.create_index('ix_action_tokens_user_id','action_tokens',['user_id'])

def downgrade():
    op.drop_index('ix_action_tokens_user_id',table_name='action_tokens')
    op.drop_table('action_tokens');op.drop_table('memberships')
    with op.batch_alter_table('users') as batch:
        batch.drop_constraint('uq_users_id_business',type_='unique')
        batch.drop_column('disabled');batch.drop_column('email_verified_at')
