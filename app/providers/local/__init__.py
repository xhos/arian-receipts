import logging
import json

from llama_cpp import Llama

from ..config import ensure_model_present
from ..config import (
	LOCAL_MODEL_FILE,
	LLAMA_THREADS,
	LLAMA_CTX,
	LLAMA_MAX_TOK,
	LLAMA_TEMP,
	LLAMA_TOP_P,
	LLAMA_TOP_K,
)
from ..schema import Receipt
from .ocr import extract_text

log = logging.getLogger(__name__)


def init_provider():
	ensure_model_present()


def parse_receipt(image_bytes):
	ocr_txt = extract_text(image_bytes)

	if not hasattr(parse_receipt, "_llm"):
		parse_receipt._llm = Llama(
			model_path=str(LOCAL_MODEL_FILE),
			n_threads=LLAMA_THREADS,
			n_ctx=LLAMA_CTX,
			chat_format="llama-2",
		)

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

	Receipt(**data)
	return data
