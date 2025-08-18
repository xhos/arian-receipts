from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Callable

SERVICE_NAME = "arian-receipts"


def _env(name: str, default: Any, cast: Callable[[str], Any]):
	raw = os.getenv(name)
	if raw is None:
		return default
	try:
		return cast(raw)
	except Exception as e:
		raise ValueError(
			f"env var {name!r}={raw!r} not valid for {cast.__name__}"
		) from e


# minimal env surface
LOG_LEVEL = _env("LOG_LEVEL", "INFO", str)
OTLP_ENDPOINT = _env("OTLP_ENDPOINT", None, str)
LOKI_URL = _env("LOKI_URL", None, str)  # presence toggles json logs, no direct emission

# provider tuning
GEMINI_MODEL = _env("GEMINI_MODEL", "gemini-2.0-flash-001", str).strip()
PROVIDER_TIMEOUT_SECS = _env("PROVIDER_TIMEOUT_SECS", 20, int)


# constraints
MAX_UPLOAD_MB = _env("MAX_UPLOAD_MB", 10, int)
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png"}


@dataclass(frozen=True)
class Settings:
	service: str = SERVICE_NAME
	log_level: str = LOG_LEVEL
	json_logs: bool = bool(OTLP_ENDPOINT or LOKI_URL)
	otlp_endpoint: str | None = OTLP_ENDPOINT
	gemini_model: str = GEMINI_MODEL
	provider_timeout_secs: int = PROVIDER_TIMEOUT_SECS
	max_upload_mb: int = MAX_UPLOAD_MB
	allowed_mime_types: set[str] = field(default_factory=lambda: ALLOWED_MIME_TYPES)


def load_settings() -> Settings:
	return Settings()
