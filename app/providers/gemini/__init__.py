from __future__ import annotations
import base64
import json
import logging
from typing import Any
from google import genai
from google.genai import types
from opentelemetry import trace
from ...schema import Receipt

log = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

_client: genai.Client | None = None


def init_provider() -> None:
	global _client
	_client = genai.Client()
	log.info("Gemini provider initialised")


def _img_part(blob: bytes, mime: str = "image/jpeg") -> dict[str, Any]:
	return {
		"inline_data": {
			"mime_type": mime,
			"data": base64.b64encode(blob).decode(),
		}
	}


PROMPT = (
	"You are an OCR information extractor. "
	"Return only valid JSON with fields: "
	"merchant (string), date (string), total (number), "
	"items (array of {name, price, qty}). "
	"Do not include any extra keys or non-JSON text."
)


def parse_receipt(image_bytes: bytes) -> dict[str, Any]:
	if _client is None:
		raise RuntimeError("Gemini provider not initialised; call init_provider()")

	with tracer.start_as_current_span("gemini.parse_receipt") as span:
		span.set_attribute("llm.model", "gemini-2.5-flash")

		response = _client.models.generate_content(
			model="gemini-2.5-flash",
			contents=[_img_part(image_bytes), {"text": PROMPT}],
			config=types.GenerateContentConfig(response_mime_type="application/json"),
		)

		raw = response.text
		log.debug("Gemini raw response: %s", raw[:200])

		try:
			data: dict[str, Any] = json.loads(raw)
		except json.JSONDecodeError as exc:
			log.error("Gemini did not return valid JSON", extra={"error": str(exc)})
			raise ValueError("Gemini response was not valid JSON") from exc

		if isinstance(data.get("items"), list):
			data["items"] = [i for i in data["items"] if i.get("price") not in (0, 0.0)]

		receipt = Receipt(**data)

		span.set_attribute("receipt.items", len(receipt.items))
		span.set_attribute("receipt.total", receipt.total)

		log.info(
			"parsed receipt",
			extra={
				"merchant": receipt.merchant,
				"date": receipt.date,
				"total": receipt.total,
				"items": len(receipt.items),
			},
		)

		return data
