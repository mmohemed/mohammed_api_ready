# =========================================
# إعداد قاعدة البيانات (SQLite + SQLAlchemy)
# =========================================
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_URL = os.environ.get("ERP_DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'erp.db')}")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """جلسة قاعدة بيانات لكل طلب (Dependency)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
