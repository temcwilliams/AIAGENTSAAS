from alembic import context
from sqlalchemy import create_engine
from app.config import settings
from app.db import Base
from app import models

def run():
    engine = create_engine(settings.database_url_unpooled or settings.database_url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
        with context.begin_transaction(): context.run_migrations()
run()
