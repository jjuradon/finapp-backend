import uuid

from app.core.logging import configure_logging, get_trace_id, set_trace_id
from app.db.session import Base, SessionLocal, engine
from app.shared.exceptions import NotFoundError
from app.shared.schemas import ResponseEnvelope


def test_imports():
    """Verify that core modules can be imported without errors."""
    assert configure_logging is not None
    assert NotFoundError is not None
    assert ResponseEnvelope is not None


def test_logging_and_context():
    """Verify logging configuration and trace ID context var tracking."""
    # Test logger configuration
    configure_logging()

    # Test trace ID generation and setter/getter
    test_id = str(uuid.uuid4())
    set_trace_id(test_id)
    assert get_trace_id() == test_id


def test_db_session_setup():
    """Verify database engine and base class setup."""
    assert Base is not None
    assert engine is not None
    assert SessionLocal is not None
