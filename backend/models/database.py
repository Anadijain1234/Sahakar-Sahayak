import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Ensure data directory exists
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

DEFAULT_DB_PATH = os.path.join(DATA_DIR, "sahakar_sahayak.db")

# DATABASE_URL set (e.g. a free Neon Postgres) -> permanent storage: accounts and the
# Insights log survive redeploys. Not set -> a SQLite file, which on Render's free plan
# is wiped on every redeploy/restart (fine for local development).
SQLITE_URL = f"sqlite:///{DEFAULT_DB_PATH}"
DATABASE_URL = os.getenv("DATABASE_URL", "").strip().strip('"').strip("'") or SQLITE_URL
# Use the "psycopg" (version 3) Postgres driver: it is in requirements.txt and works on new Python versions.
for _prefix in ("postgres://", "postgresql://"):
    if DATABASE_URL.startswith(_prefix):
        DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL[len(_prefix):]
        break


def _make_engine(url):
    if url.startswith("sqlite"):
        # SQLite requires check_same_thread=False for multithreaded FastAPI requests
        return create_engine(url, connect_args={"check_same_thread": False}, echo=False)
    # Neon sleeps after a few idle minutes and closes old connections: pool_pre_ping checks a
    # connection before using it and reconnects if needed. prepare_threshold=None keeps it
    # working through Neon's connection pooler.
    return create_engine(url, echo=False, pool_pre_ping=True, pool_recycle=240, pool_size=3, max_overflow=2,
                         connect_args={"connect_timeout": 15, "prepare_threshold": None})


try:
    engine = _make_engine(DATABASE_URL)
except Exception as _e:
    # Never let a database setting stop the whole app: fall back to the temporary SQLite file.
    print(f"⚠️ DATABASE_URL could not be used ({type(_e).__name__}: {_e}) -- falling back to a temporary SQLite file.")
    DATABASE_URL = SQLITE_URL
    engine = _make_engine(DATABASE_URL)

IS_SQLITE = DATABASE_URL.startswith("sqlite")
IS_PERMANENT = not IS_SQLITE

try:
    _where = "SQLite file (temporary on Render's free plan)" if IS_SQLITE else \
        f"PostgreSQL at {engine.url.host} (permanent)"
    print(f"🗄️ Database: {_where}")
except Exception:
    pass

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency that provides a SQLAlchemy database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables and perform lightweight schema migrations if necessary."""
    # Import all models to ensure they are registered with Base.metadata
    from backend.models.user import User  # noqa: F401
    from backend.models.pending_registration import PendingRegistration  # noqa: F401

    Base.metadata.create_all(bind=engine)

    # Lightweight migration check for SQLite
    if DATABASE_URL.startswith("sqlite"):
        with engine.connect() as conn:
            inspector = inspect(engine)
            if "users" in inspector.get_table_names():
                columns = [col["name"] for col in inspector.get_columns("users")]
                if "phone" not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR(50)"))
                    conn.commit()
                if "user_type" not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN user_type VARCHAR(50) DEFAULT 'Citizen'"))
                    conn.commit()
                if "preferred_language" not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN preferred_language VARCHAR(10) DEFAULT 'en'"))
                    conn.commit()
                if "email_verified" not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT 1"))
                    conn.commit()
                if "phone_verified" not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN phone_verified BOOLEAN DEFAULT 1"))
                    conn.commit()
                if "is_active" not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1"))
                    conn.commit()

