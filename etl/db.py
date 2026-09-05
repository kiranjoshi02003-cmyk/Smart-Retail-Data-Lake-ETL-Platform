import logging
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, declarative_base
from etl.config import DATABASE_URI, USE_POSTGRES

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# SQLAlchemy Engine & Session Setup
engine = create_engine(
    DATABASE_URI,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URI else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Context manager generator for DB sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables and create schemas if needed."""
    logger.info(f"Initializing database engine with URI: {DATABASE_URI} (Target DB: {'PostgreSQL' if USE_POSTGRES else 'SQLite'})")
    Base.metadata.create_all(bind=engine)

def execute_raw_sql(sql_query: str):
    """Execute raw SQL query safely and return dict containing columns and list of row dicts."""
    with engine.connect() as connection:
        result = connection.execute(text(sql_query))
        if result.returns_rows:
            keys = list(result.keys())
            rows = [dict(zip(keys, row)) for row in result.fetchall()]
            return {"columns": keys, "rows": rows}
        else:
            connection.commit()
            return {"columns": ["affected_rows"], "rows": [{"affected_rows": result.rowcount}]}

def get_table_names():
    """Retrieve list of existing tables in database."""
    inspector = inspect(engine)
    return inspector.get_table_names()
