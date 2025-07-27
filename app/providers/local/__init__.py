import logging
import json

from llama_cpp import Llama

from ...config import ensure_model_present, LOCAL_PROVIDER_ENABLED
from ...config import (
	LOCAL_MODEL_FILE,
	LLAMA_THREADS,
	LLAMA_CTX,
	LLAMA_MAX_TOK,
	LLAMA_TEMP,
	LLAMA_TOP_P,
	LLAMA_TOP_K,
)
from ...schema import Receipt
# The ocr import is no longer here at the top level

log = logging.getLogger(__name__)


def init_provider():
	"""
	Initialization is deferred to the first call to parse_receipt
	to avoid downloading the model on startup.
	"""
	if LOCAL_PROVIDER_ENABLED:
		log.info("Local provider is enabled.")
	else:
		log.info(
			"Local provider is disabled. Set LOCAL_PROVIDER_ENABLED=true to use it."
		)
	pass


def parse_receipt(image_bytes):
	"""
	Parses a receipt using the local provider.
	Ensures model is downloaded on first run.
	"""
	# Check if the local provider is enabled before proceeding
	if not LOCAL_PROVIDER_ENABLED:
		raise RuntimeError(
			"The local provider is not enabled. Set LOCAL_PROVIDER_ENABLED=true to use it."
		)

	# Defer the import of the heavy OCR module to here
	from .ocr import extract_text

	# 1. Ensure model is present (triggers download on first call)
	ensure_model_present()

	# 2. Extract text from the image
	ocr_txt = extract_text(image_bytes)

	# 3. Lazily load LLM into memory and run inference
	if not hasattr(parse_receipt, "_llm"):
		log.info("Loading local LLM into memory for the first time...")
		try:
			parse_receipt._llm = Llama(
				model_path=str(LOCAL_MODEL_FILE),
				n_threads=LLAMA_THREADS,
				n_ctx=LLAMA_CTX,
				chat_format="llama-2",
				verbose=False,  # Add this line to suppress backend logging
			)
			log.info("Local LLM loaded successfully.")
		except Exception as e:
			log.error(f"Failed to load local LLM model: {e}")
			raise RuntimeError(
				f"Could not load local model from {LOCAL_MODEL_FILE}"
			) from e

	user_prompt = (
		"Extract JSON with keys merchant, date, total (number), "
		"items (array of {name, price, qty}) from the receipt below.\n\n"
		f"### OCR TEXT\n{ocr_txt}\n### END"
	)

	res = parse_receipt._llm.create_chat_completion(
		messages=[{"role": "user", "content": user_prompt}],
		max_tokens=LLAMA_MAX_TOK,
		temperature=LLAMA_TEMP,
		top_p=LLAMA_TOP_P,
		top_k=LLAMA_TOP_K,
		response_format={"type": "json_object"},
	)

	raw = res["choices"][0]["message"]["content"].strip()
	data = json.loads(raw)

	# clean up empty items (stamps, points, etc)
	if "items" in data and isinstance(data["items"], list):
		data["items"] = [item for item in data["items"] if item.get("price") != 0]

	Receipt(**data)
	return data
