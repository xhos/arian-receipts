from __future__ import annotations

import logging
import time
from typing import Dict

from opentelemetry import trace

from .config import Settings
from .providers.base import Provider
from .providers.gemini import GeminiProvider
from .providers.local import LocalProvider
from .schemas import ProviderState, Receipt

log = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class ProviderRegistry:
	def __init__(self) -> None:
		self._providers: Dict[str, Provider] = {}

	def register(self, provider: Provider) -> None:
		self._providers[provider.name] = provider

	def get(self, name: str) -> Provider:
		if name not in self._providers:
			raise KeyError(name)
		return self._providers[name]

	def all(self) -> list[Provider]:
		return list(self._providers.values())


class ReceiptService:
	def __init__(self, settings: Settings) -> None:
		self.settings = settings
		self.registry = ProviderRegistry()
		self.registry.register(GeminiProvider())
		self.registry.register(LocalProvider())

	def provider_states(self) -> list[ProviderState]:
		out: list[ProviderState] = []
		for p in self.registry.all():
			ok, reason = p.available()
			out.append(
				ProviderState(
					name=p.name,
					kind=p.kind,
					available=ok,
					reason=reason,
					model=p.model_id(),
				)
			)
		return out

	def parse(
		self, provider_name: str, image_bytes: bytes, mime_type: str | None
	) -> Receipt:
		p = self.registry.get(provider_name)

		with tracer.start_as_current_span("service.parse") as span:
			span.set_attribute("provider.name", provider_name)
			span.set_attribute("provider.model", p.model_id() or "")
			t0 = time.perf_counter()

			ok, reason = p.available()
			if not ok:
				raise RuntimeError(
					f"provider {provider_name!r} unavailable: {reason or 'unknown'}"
				)

			rec = p.parse(image_bytes, mime_type)

			span.set_attribute("items.count", len(rec.items))
			span.set_attribute("total", rec.total or 0.0)
			span.set_attribute("elapsed_secs", round(time.perf_counter() - t0, 3))

		return rec
