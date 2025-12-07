"""FastAPI dependency injection."""

from backend.services.database import database


def get_db():
    """Database session dependency."""
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()
