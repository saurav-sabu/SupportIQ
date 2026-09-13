from datetime import datetime, timezone
import logging
from typing import List, Dict, Any, Tuple, Optional

from sqlalchemy import create_engine, Integer, String, Text, DateTime, desc
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session
from src.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class Base(DeclarativeBase):
    pass


class AuditLog(Base):
    """
    SQLAlchemy Audit Log model for SupportIQ.
    Stores interaction history, questions, answers, routing decisions, and latency in NeonDB.
    """
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    source_used: Mapped[str] = mapped_column(String(50), nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else "",
            "question": self.question,
            "answer": self.answer,
            "source_used": self.source_used,
            "latency_ms": self.latency_ms,
        }


def _normalize_db_url(raw_url: str) -> str:
    """
    Standardizes PostgreSQL database URL for SQLAlchemy engine.
    Converts legacy 'postgres://' prefixes to standard 'postgresql://'.
    """
    url = raw_url.strip()
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


def _create_db_engine() -> Tuple[Optional[Any], str]:
    """
    Creates an engine connecting exclusively to NeonDB (PostgreSQL) using SQLAlchemy.
    """
    raw_url = settings.database_url.strip() if settings.database_url else ""
    if not raw_url:
        logger.info("DATABASE_URL not configured. NeonDB audit logging is inactive.")
        return None, "NeonDB (Not Configured - set DATABASE_URL in .env)"

    try:
        db_url = _normalize_db_url(raw_url)
        engine = create_engine(
            db_url,
            pool_pre_ping=True,      # Automatically verifies connection health (crucial for Neon serverless)
            pool_recycle=300,        # Recycles connections every 5 mins to handle idle auto-suspend
        )
        # Test connectivity
        with engine.connect() as conn:
            pass
        logger.info("Successfully connected to NeonDB (PostgreSQL) via SQLAlchemy.")
        return engine, "NeonDB (PostgreSQL via SQLAlchemy)"
    except Exception as e:
        logger.error(
            f"Failed to connect to NeonDB via SQLAlchemy: {e}",
            exc_info=False
        )
        return None, f"NeonDB Connection Error: {e}"


# Module-level Engine & Session Maker
engine, db_provider = _create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) if engine is not None else None


def init_audit_table():
    """
    Initializes the audit_logs table on NeonDB using SQLAlchemy Base.metadata.create_all.
    """
    if engine is None:
        return
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("NeonDB audit_logs table verified/created successfully.")
    except Exception as e:
        logger.error(f"Error creating audit_logs table on NeonDB with SQLAlchemy: {e}", exc_info=True)


# Initialize table on module import if NeonDB engine is active
init_audit_table()


def log_audit(question: str, answer: str, source_used: str, latency_ms: int = 0):
    """
    Logs a single IT support interaction directly to NeonDB using SQLAlchemy ORM.
    """
    if SessionLocal is None:
        logger.debug("NeonDB audit log skipped: DATABASE_URL not configured or engine unavailable.")
        return

    session = SessionLocal()
    try:
        record = AuditLog(
            timestamp=datetime.now(timezone.utc),
            question=question,
            answer=answer,
            source_used=source_used,
            latency_ms=latency_ms
        )
        session.add(record)
        session.commit()
    except Exception as e:
        session.rollback()
        logger.warning(f"Failed to record audit log in NeonDB with SQLAlchemy: {e}")
    finally:
        session.close()


def get_audit_logs(limit: int = 50) -> Tuple[List[Dict[str, Any]], str]:
    """
    Retrieves the most recent audit records directly from NeonDB via SQLAlchemy.
    """
    if SessionLocal is None:
        return [], db_provider

    session = SessionLocal()
    try:
        records = session.query(AuditLog).order_by(desc(AuditLog.id)).limit(limit).all()
        logs = [r.to_dict() for r in records]
        return logs, db_provider
    except Exception as e:
        logger.warning(f"Failed to query audit logs from NeonDB with SQLAlchemy: {e}")
        return [], db_provider
    finally:
        session.close()
