from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, StringConstraints
from typing_extensions import Annotated


ISODateStr = Annotated[str, StringConstraints(pattern=r"\d{4}-\d{2}-\d{2}")]


class Item(BaseModel):
	name: str
	price: float
	qty: float


class Receipt(BaseModel):
	# required
	total: float
	items: list[Item] = Field(default_factory=list)
	# optional
	merchant: Optional[str] = None
	date: Optional[ISODateStr] = None


class ProviderState(BaseModel):
	name: str
	kind: str  # "remote" | "local"
	available: bool
	reason: Optional[str] = None
	model: Optional[str] = None


class ErrorBody(BaseModel):
	code: str
	message: str
	details: dict = Field(default_factory=dict)


class ErrorResponse(BaseModel):
	error: ErrorBody
