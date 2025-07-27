from __future__ import annotations

import json
import logging
from typing import Any

from google import genai
from google.genai import types
from opentelemetry import trace

from ..config import GEMINI_MODEL, PROVIDER_TIMEOUT_SECS
from ..schemas import Receipt

log = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class GeminiProvider:
	name = "gemini"
	kind = "remote"

	def __init__(self) -> None:
		# relies on GOOGLE_API_KEY in env; genai.Client() reads it
		self._client: genai.Client | None = None
		try:
			self._client = genai.Client()
		except Exception as e:
			log.debug("gemini client init failed: %s", e)
			self._client = None

	def model_id(self) -> str | None:
		return GEMINI_MODEL

	def available(self) -> tuple[bool, str | None]:
		if self._client is None:
			return False, "missing or invalid GOOGLE_API_KEY"
		return True, None

	def parse(self, image_bytes: bytes, mime_type: str | None) -> Receipt:
		if self._client is None:
			raise RuntimeError("Gemini provider not configured")

		img_part = types.Part.from_bytes(
			data=image_bytes, mime_type=mime_type or "image/jpeg"
		)

		prompt = (
			"You extract structured receipt data.\n"
			"- emit only JSON matching the given schema\n"
			"- required: total (number), items (array of {name, price, qty})\n"
			"- optional: merchant (string), date (YYYY-MM-DD) with no time\n"
			"- omit unknown fields; do not invent items\n"
		)

		cfg = types.GenerateContentConfig(
			response_mime_type="application/json",
			response_schema=Receipt,
		)

		with tracer.start_as_current_span("provider.gemini.parse") as span:
			span.set_attribute("llm.provider", "gemini")
			span.set_attribute("llm.model", self.model_id() or "")
			span.set_attribute("request.timeout_secs", PROVIDER_TIMEOUT_SECS)

			resp = self._client.models.generate_content(
				model=self.model_id() or GEMINI_MODEL,
				# must use keyword-only for from_text
				contents=[img_part, types.Part.from_text(text=prompt)],
				config=cfg,
			)

			raw = resp.text
			span.set_attribute("response.size_bytes", len(raw.encode("utf-8")))

		try:
			data: dict[str, Any] = json.loads(raw)
		except json.JSONDecodeError as exc:
			log.error("gemini returned non-json", extra={"error": str(exc)})
			raise ValueError("Gemini response was not valid JSON") from exc

		receipt = Receipt(**data)
		receipt.items = [i for i in receipt.items if i.price not in (0, 0.0)]
		return receipt
