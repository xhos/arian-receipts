from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any

from opentelemetry import trace

from ...schemas import Receipt
from ...config import SERVICE_NAME

log = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# defaults chosen for convenience; if download fails, provider will be unavailable
HF_REPO_ID = "microsoft/Phi-3-mini-4k-instruct-gguf"
HF_FILENAME = "Phi-3-mini-4k-instruct-q4.gguf"
MODELS_DIR = Path("models")
LOCAL_MODEL_FILE = MODELS_DIR / HF_FILENAME


class LocalProvider:
	name = "local"
	kind = "local"

	def __init__(self) -> None:
		self._ready_checked = False
		self._reason: str | None = None

	def model_id(self) -> str | None:
		return HF_FILENAME if LOCAL_MODEL_FILE.exists() else None

	def _check_ready(self) -> tuple[bool, str | None]:
		# lightweight capability check; no downloads, no heavy imports
		if shutil.which("tesseract") is None:
			return False, "tesseract not found on PATH"

		try:
			import pytesseract  # noqa:F401
			import numpy  # noqa:F401
			import PIL  # noqa:F401
			import cv2  # noqa:F401
			import llama_cpp  # noqa:F401
			import huggingface_hub  # noqa:F401
		except Exception as e:
			return False, f"missing local extras: {e}"

		return True, None

	def available(self) -> tuple[bool, str | None]:
		if not self._ready_checked:
			ok, reason = self._check_ready()
			self._ready_checked, self._reason = True, reason
			return ok, reason
		return (self._reason is None), self._reason

	def _ensure_model_present(self) -> None:
		if LOCAL_MODEL_FILE.exists():
			return
		MODELS_DIR.mkdir(parents=True, exist_ok=True)
		from huggingface_hub import snapshot_download

		log.info(
			"downloading %s from %s",
			HF_FILENAME,
			HF_REPO_ID,
			extra={"service": SERVICE_NAME},
		)
		snapshot_download(
			repo_id=HF_REPO_ID,
			repo_type="model",
			local_dir=str(MODELS_DIR),
			local_dir_use_symlinks=False,
			allow_patterns=[HF_FILENAME],
			resume_download=True,
		)
		if not LOCAL_MODEL_FILE.exists():
			raise FileNotFoundError(f"{LOCAL_MODEL_FILE!r} missing after download")

	def parse(self, image_bytes: bytes, mime_type: str | None) -> Receipt:
		ok, reason = self.available()
		if not ok:
			raise RuntimeError(f"Local provider unavailable: {reason or 'unknown'}")

		from .ocr import extract_text
		from llama_cpp import Llama

		self._ensure_model_present()

		with tracer.start_as_current_span("provider.local.ocr") as span:
			txt = extract_text(image_bytes)
			span.set_attribute("ocr.chars", len(txt))

		if not hasattr(self, "_llm"):
			log.info("loading local gguf model into memory")
			self._llm = Llama(
				model_path=str(LOCAL_MODEL_FILE), n_ctx=4096, verbose=False
			)

		user_prompt = (
			"Extract JSON with keys merchant (string, optional), "
			"date (YYYY-MM-DD, optional), total (number, required) "
			"and items (array of {name, price, qty}, required) from the receipt below.\n"
			"Return only valid JSON.\n\n"
			f"### OCR TEXT\n{txt}\n### END"
		)

		with tracer.start_as_current_span("provider.local.llm") as span:
			res = self._llm.create_chat_completion(
				messages=[{"role": "user", "content": user_prompt}],
				temperature=0.1,
				response_format={"type": "json_object"},
				max_tokens=512,
			)
			raw = res["choices"][0]["message"]["content"].strip()
			span.set_attribute("llm.output_chars", len(raw))

		data: dict[str, Any] = json.loads(raw)
		rec = Receipt(**data)
		rec.items = [i for i in rec.items if i.price not in (0, 0.0)]
		return rec
