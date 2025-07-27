from __future__ import annotations

from typing import Protocol

from ..schemas import Receipt


class Provider(Protocol):
	name: str
	kind: str  # "remote" | "local"

	def model_id(self) -> str | None: ...
	def available(self) -> tuple[bool, str | None]: ...
	def parse(self, image_bytes: bytes, mime_type: str | None) -> Receipt: ...
