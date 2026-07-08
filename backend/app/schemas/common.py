"""Shared response envelope and pagination schemas."""
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    data: list[T]
    total: int
    page: int
    limit: int
    pages: int


class MessageResponse(BaseModel):
    message: str


class IDResponse(BaseModel):
    id: str
