from alembic import context
from core.config import Settings
from core.database.models import Base
from core.database.session import database

engine, _ = database(Settings.from_env())
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
engine.dispose()
