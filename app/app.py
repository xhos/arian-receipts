from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

try:
	# optional; only if opentelemetry-instrumentation-fastapi is installed
	from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
except ImportError:
	FastAPIInstrumentor = None  # type: ignore

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from .config import SERVICE_NAME, load_settings
from .logging import configure_logging
from .service import ReceiptService
from .transport.rest import build_router

settings = load_settings()

# text logs by default, json if any LGTM endpoint is present
configure_logging(
	service=SERVICE_NAME, json_mode=settings.json_logs, level=settings.log_level
)
log = logging.getLogger(__name__)


def setup_tracing(app: FastAPI) -> None:
	if not settings.otlp_endpoint or FastAPIInstrumentor is None:
		msg = "tracing disabled"
		if not settings.otlp_endpoint:
			msg += " (no OTLP_ENDPOINT)"
		elif FastAPIInstrumentor is None:
			msg += " (instrumentation lib missing)"
		log.info(msg)
		return

	resource = Resource.create({"service.name": SERVICE_NAME})
	provider = TracerProvider(resource=resource)
	exporter = OTLPSpanExporter(endpoint=settings.otlp_endpoint, insecure=True)
	provider.add_span_processor(BatchSpanProcessor(exporter))
	trace.set_tracer_provider(provider)
	FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
	log.info("tracing enabled", extra={"otlp_endpoint": settings.otlp_endpoint})


svc = ReceiptService(settings)


@asynccontextmanager
async def lifespan(app: FastAPI):
	log.info("starting service")
	setup_tracing(app)
	log.info("ready")
	yield


app = FastAPI(title=SERVICE_NAME, version="0.2.0", lifespan=lifespan)
app.include_router(build_router(settings, svc))


def main() -> None:
	# entrypoint for `uv run arian-receipts`
	import uvicorn

	uvicorn.run("arian_receipts.app:app", host="0.0.0.0", port=8000, reload=True)
