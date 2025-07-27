from __future__ import annotations
from .config import configure_logging
from .providers import init_gemini, parse_gemini, init_local, parse_local
from contextlib import asynccontextmanager
from fastapi import FastAPI, File, HTTPException, UploadFile, Query
from fastapi.responses import JSONResponse
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from typing import Annotated, Literal
import os
import time

log = configure_logging()


def setup_tracing(app: FastAPI) -> None:
	resource = Resource.create({"service.name": "arian-receipts"})
	provider = TracerProvider(resource=resource)

	exporter = OTLPSpanExporter(
		endpoint=os.getenv("OTLP_ENDPOINT", "http://localhost:4317"), insecure=True
	)
	provider.add_span_processor(BatchSpanProcessor(exporter))
	trace.set_tracer_provider(provider)

	FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)


@asynccontextmanager
async def lifespan(app: FastAPI):
	log.info("starting service")
	setup_tracing(app)
	init_gemini()
	init_local()
	log.info("ready")
	yield


app = FastAPI(title="arian-receipts", version="0.2.0", lifespan=lifespan)


@app.get("/health")
async def health():
	return {"status": "ok"}


@app.post("/parse")
async def parse_endpoint(
	file: Annotated[UploadFile, File(description="JPEG or PNG receipt image")],
	provider: Annotated[
		Literal["gemini", "local"],
		Query(description="The provider to use for parsing. Defaults to 'gemini'."),
	] = "gemini",
):
	try:
		log.info(
			"received file for provider '%s'",
			provider,
			extra={"upload_filename": file.filename, "content_type": file.content_type},
		)
		t0 = time.perf_counter()

		image_bytes = await file.read()

		if provider == "local":
			result = parse_local(image_bytes)
		else:
			result = parse_gemini(image_bytes)

		log.info("served by %s in %.2f s", provider, time.perf_counter() - t0)
		return JSONResponse(content=result)
	except RuntimeError as e:
		log.error("Provider configuration error for '%s': %s", provider, e)
		raise HTTPException(status_code=400, detail=str(e))
	except Exception:
		log.exception("An unexpected error occurred during parsing")
		raise HTTPException(
			status_code=500,
			detail="Failed to parse receipt due to an internal server error.",
		)
