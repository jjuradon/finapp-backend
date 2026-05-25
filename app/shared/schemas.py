# app/shared/schemas.py
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MetaSchema(BaseModel):
    request_id: UUID
    timestamp: datetime


class ErrorSchema(BaseModel):
    code: str
    message: str


class ResponseEnvelope[T](BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: T | None
    meta: MetaSchema
    error: ErrorSchema | None = None


class CursorPage[T](BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: list[T]
    next_cursor: str | None
    page_size: int
