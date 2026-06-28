import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql+psycopg://search_agent:search_agent@postgres:5432/search_agent',
)


class Base(DeclarativeBase):
    pass


engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def ensure_schema_updates() -> None:
    if not engine.dialect.name.startswith('postgresql'):
        return

    inspector = inspect(engine)
    with engine.begin() as connection:
        if inspector.has_table('users'):
            user_columns = {column['name'] for column in inspector.get_columns('users')}

            if 'username' not in user_columns:
                connection.execute(text('ALTER TABLE users ADD COLUMN username VARCHAR(64)'))
                connection.execute(
                    text(
                        """
                        UPDATE users
                        SET username = LOWER(
                            COALESCE(NULLIF(SPLIT_PART(email, '@', 1), ''), 'user') || '-' || id::text
                        )
                        WHERE username IS NULL OR username = ''
                        """
                    )
                )
                connection.execute(text('ALTER TABLE users ALTER COLUMN username SET NOT NULL'))
                connection.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username)'))

            if 'role' not in user_columns:
                connection.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(32) DEFAULT 'user'"))
                connection.execute(text("UPDATE users SET role = 'user' WHERE role IS NULL OR role = ''"))
                connection.execute(text('ALTER TABLE users ALTER COLUMN role SET NOT NULL'))
                connection.execute(text('CREATE INDEX IF NOT EXISTS ix_users_role ON users (role)'))

        if inspector.has_table('usage_logs'):
            usage_columns = {column['name'] for column in inspector.get_columns('usage_logs')}

            if 'requester_username' not in usage_columns:
                connection.execute(text('ALTER TABLE usage_logs ADD COLUMN requester_username VARCHAR(64)'))
                connection.execute(
                    text(
                        """
                        UPDATE usage_logs AS usage_logs
                        SET requester_username = users.username
                        FROM users
                        WHERE usage_logs.user_id = users.id
                          AND (usage_logs.requester_username IS NULL OR usage_logs.requester_username = '')
                        """
                    )
                )
                connection.execute(
                    text(
                        """
                        UPDATE usage_logs
                        SET requester_username = LOWER(
                            COALESCE(NULLIF(SPLIT_PART(requester_email, '@', 1), ''), 'legacy-user')
                        )
                        WHERE requester_username IS NULL OR requester_username = ''
                        """
                    )
                )
                connection.execute(text('ALTER TABLE usage_logs ALTER COLUMN requester_username SET NOT NULL'))
                connection.execute(
                    text('CREATE INDEX IF NOT EXISTS ix_usage_logs_requester_username ON usage_logs (requester_username)')
                )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
