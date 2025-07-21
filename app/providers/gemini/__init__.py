import base64
import json
import logging
from google import genai
from google.genai import types
from ...schema import Receipt

log = logging.getLogger(__name__)

_client = None


def init_provider():
	global _client
	_client = genai.Client()


def _img_part(image_bytes, mime="image/jpeg"):
	return {
		"inline_data": {
			"mime_type": mime,
			"data": base64.b64encode(image_bytes).decode(),
		}
	}


def parse_receipt(image_bytes):
	if not _client:
		raise RuntimeError(
			"Gemini provider not initialized. Call init_provider() first."
		)

	prompt = (
		"You are an OCR information extractor. "
		"Return *only* valid JSON with fields:\n"
		"  merchant (string), date (string), total (number),\n"
		"  items (array of {name, price, qty}).\n"
		"Do **not** include any extra keys or non-JSON text."
	)

	response = _client.models.generate_content(
		model="gemini-2.5-flash",
		contents=[_img_part(image_bytes), {"text": prompt}],
		config=types.GenerateContentConfig(response_mime_type="application/json"),
	)

	try:
		data = json.loads(response.text)
	except json.JSONDecodeError:
		log.error("Gemini did not return valid JSON: %s", response.text[:200])
		raise ValueError("Gemini response was not valid JSON")

	# clean up empty items (stamps, points, etc)
	if "items" in data and isinstance(data["items"], list):
		data["items"] = [item for item in data["items"] if item.get("price") != 0]

	Receipt(**data)
	return data
