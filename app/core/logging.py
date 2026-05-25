# app/core/logging.py
import logging
import uuid
from contextvars import ContextVar

from pythonjsonlogger import jsonlogger

from app.core.config import settings

_trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")


def get_trace_id() -> str:
    return _trace_id_var.get() or str(uuid.uuid4())


def set_trace_id(trace_id: str) -> None:
    _trace_id_var.set(trace_id)


class _TraceFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = get_trace_id()
        record.service = settings.service_name
        return True


def configure_logging() -> None:
    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(service)s %(trace_id)s %(message)s",
        rename_fields={"asctime": "timestamp", "levelname": "level"},
    )
    handler.setFormatter(formatter)
    handler.addFilter(_TraceFilter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.log_level.upper())
