from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from typing import Any

from opentelemetry import trace
from pythonjsonlogger import jsonlogger


class LokiJSONFormatter(jsonlogger.JsonFormatter):
	def add_fields(
		self,
		log_record: dict[str, Any],
		record: logging.LogRecord,
		message_dict: dict[str, Any],
	):
		super().add_fields(log_record, record, message_dict)

		log_record["timestamp"] = datetime.fromtimestamp(
			record.created, timezone.utc
		).isoformat(timespec="milliseconds")
		log_record["level"] = record.levelname.lower()
		log_record["service"] = log_record.get("service") or "arian-receipts"

		log_record.pop("levelname", None)
		log_record.pop("color_message", None)
		log_record.pop("asctime", None)

		span = trace.get_current_span()
		if span and span.get_span_context().is_valid:
			ctx = span.get_span_context()
			log_record["trace_id"] = f"{ctx.trace_id:032x}"
			log_record["span_id"] = f"{ctx.span_id:016x}"

		return log_record


def configure_logging(
	service: str, json_mode: bool, level: str = "INFO"
) -> logging.Logger:
	root = logging.getLogger()
	if root.handlers:
		return logging.getLogger(__name__)

	handler = logging.StreamHandler(sys.stdout)
	if json_mode:
		handler.setFormatter(
			LokiJSONFormatter(
				"%(timestamp)s %(level)s %(service)s %(name)s %(message)s"
			)
		)
	else:
		handler.setFormatter(
			logging.Formatter(fmt="%(levelname)s %(name)s — %(message)s")
		)

	root.setLevel(level.upper())
	root.addHandler(handler)

	for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
		ul = logging.getLogger(name)
		ul.handlers = [handler]
		ul.propagate = False

	return logging.getLogger(__name__)
