from typing import Optional, List
from pydantic import BaseModel


class Item(BaseModel):
	name: str
	price: float
	qty: float


class Receipt(BaseModel):
	merchant: Optional[str] = None
	date: Optional[str] = None
	total: Optional[float] = None
	items: Optional[List[Item]] = None
