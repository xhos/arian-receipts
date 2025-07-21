from __future__ import annotations
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from opentelemetry import trace
from pythonjsonlogger import jsonlogger


def _env(name: str, default: Any, cast: Callable[[str], Any]):
	raw = os.getenv(name)
	if raw is None:
		return default
	try:
		return cast(raw)
	except Exception:
		raise ValueError(f"env var {name!r}={raw!r} not valid for {cast.__name__}")


SERVICE = _env("SERVICE_NAME", "arian-receipts", str)
LOG_LEVEL = _env("LOG_LEVEL", "INFO", str).upper()
LOG_FORMAT = _env("LOG_FORMAT", "json", str).lower()  # json | text


class LokiJSONFormatter(jsonlogger.JsonFormatter):
	def add_fields(
		self,
		log_record: dict[str, Any],
		record: logging.LogRecord,
		message_dict: dict[str, Any],
	):
		super().add_fields(log_record, record, message_dict)

		# loki defaults
		log_record["timestamp"] = datetime.fromtimestamp(
			record.created, timezone.utc
		).isoformat(timespec="milliseconds")
		log_record["level"] = record.levelname.lower()
		log_record["service"] = SERVICE

		# remove noise
		log_record.pop("levelname", None)
		log_record.pop("color_message", None)
		log_record.pop("asctime", None)

		# otel correlation
		span = trace.get_current_span()
		if span and span.get_span_context().is_valid:
			ctx = span.get_span_context()
			log_record["trace_id"] = f"{ctx.trace_id:032x}"
			log_record["span_id"] = f"{ctx.span_id:016x}"

		return log_record


def configure_logging() -> logging.Logger:
	root = logging.getLogger()
	if root.handlers:  # already configured
		return logging.getLogger(__name__)

	handler = logging.StreamHandler(sys.stdout)

	if LOG_FORMAT == "json":
		handler.setFormatter(
			LokiJSONFormatter(
				"%(timestamp)s %(level)s %(service)s %(name)s %(message)s"
			)
		)
	else:
		handler.setFormatter(
			logging.Formatter(
				fmt="%(asctime)s %(levelname)s %(name)s — %(message)s",
				datefmt="%Y-%m-%dT%H:%M:%S",
			)
		)

	root.setLevel(LOG_LEVEL)
	root.addHandler(handler)

	for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
		ul = logging.getLogger(name)
		ul.handlers = [handler]
		ul.propagate = False

	return logging.getLogger(__name__)


HF_REPO_ID = _env("HF_REPO_ID", "microsoft/Phi-3-mini-4k-instruct-gguf", str).strip()
HF_FILENAME = _env("HF_FILENAME", "Phi-3-mini-4k-instruct-q4.gguf", str).strip()
HF_TOKEN = _env("HF_TOKEN", None, str)

MODELS_DIR = Path(_env("MODELS_DIR", "models", str))
MODELS_DIR.mkdir(parents=True, exist_ok=True)
LOCAL_MODEL_FILE = MODELS_DIR / HF_FILENAME

LLAMA_THREADS = _env("LLAMA_THREADS", os.cpu_count() or 4, int)
LLAMA_CTX = _env("LLAMA_CTX", 4096, int)
LLAMA_MAX_TOK = _env("LLAMA_MAX_TOK", 384, int)
LLAMA_TEMP = _env("LLAMA_TEMP", 0.0, float)
LLAMA_TOP_P = _env("LLAMA_TOP_P", 0.95, float)
LLAMA_TOP_K = _env("LLAMA_TOP_K", 50, int)


def ensure_model_present() -> None:
	"""download the model file if it's not present"""
	if LOCAL_MODEL_FILE.exists():
		return

	log = logging.getLogger(__name__)
	log.info("downloading %s from %s", HF_FILENAME, HF_REPO_ID)

	from huggingface_hub import snapshot_download

	snapshot_download(
		repo_id=HF_REPO_ID,
		repo_type="model",
		local_dir=str(MODELS_DIR),
		local_dir_use_symlinks=False,
		allow_patterns=[HF_FILENAME],
		token=HF_TOKEN,
		resume_download=True,
	)

	if not LOCAL_MODEL_FILE.exists():
		raise FileNotFoundError(f"{LOCAL_MODEL_FILE!r} missing after download")

	log.info("model download complete")
