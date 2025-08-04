from __future__ import annotations

import logging
from concurrent import futures

import grpc
from grpc_reflection.v1alpha import reflection
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.grpc import GrpcInstrumentorServer
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from .config import SERVICE_NAME, load_settings

# Import proto dependencies in correct order
from arian.v1 import receipt_parsing_pb2_grpc
from .logging import configure_logging
from .service import ReceiptService
from .grpc import ReceiptParsingServiceGrpc

settings = load_settings()

configure_logging(
	service=SERVICE_NAME, json_mode=settings.json_logs, level=settings.log_level
)
log = logging.getLogger(__name__)


def setup_tracing() -> None:
	if not settings.otlp_endpoint:
		log.info("tracing disabled (no OTLP_ENDPOINT)")
		return

	resource = Resource.create({"service.name": SERVICE_NAME})
	provider = TracerProvider(resource=resource)
	exporter = OTLPSpanExporter(endpoint=settings.otlp_endpoint, insecure=True)
	provider.add_span_processor(BatchSpanProcessor(exporter))
	trace.set_tracer_provider(provider)
	GrpcInstrumentorServer().instrument()
	log.info("tracing enabled", extra={"otlp_endpoint": settings.otlp_endpoint})


def serve():
	log.info("starting gRPC server")
	setup_tracing()

	server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

	svc = ReceiptService(settings)
	parsing_service = ReceiptParsingServiceGrpc(settings, svc)
	receipt_parsing_pb2_grpc.add_ReceiptParsingServiceServicer_to_server(
		parsing_service, server
	)

	# Enable gRPC reflection
	from arian.v1 import receipt_parsing_pb2

	SERVICE_NAMES = (
		receipt_parsing_pb2.DESCRIPTOR.services_by_name[
			"ReceiptParsingService"
		].full_name,
		reflection.SERVICE_NAME,
	)
	reflection.enable_server_reflection(SERVICE_NAMES, server)

	listen_addr = f"[::]:{settings.grpc_port}"
	server.add_insecure_port(listen_addr)

	server.start()
	log.info("gRPC server ready", extra={"address": listen_addr})

	try:
		server.wait_for_termination()
	except KeyboardInterrupt:
		log.info("shutting down gRPC server")
		server.stop(0)


def main() -> None:
	serve()
