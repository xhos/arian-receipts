from __future__ import annotations

import argparse
import logging
import signal
import sys
from concurrent import futures

import grpc
from grpc_reflection.v1alpha import reflection
from grpc_health.v1 import health, health_pb2_grpc, health_pb2
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.grpc import GrpcInstrumentorServer
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from arian.v1 import receipt_parsing_pb2_grpc, receipt_parsing_pb2
from .config import SERVICE_NAME, load_settings
from .version import get_version_info
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


def serve(port: int = 50051) -> None:
	version_info = get_version_info()
	log.info("Starting arian-receipts server", extra={"port": port, **version_info})
	
	setup_tracing()

	server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

	svc = ReceiptService(settings)
	parsing_service = ReceiptParsingServiceGrpc(settings, svc)
	receipt_parsing_pb2_grpc.add_ReceiptParsingServiceServicer_to_server(
		parsing_service, server
	)

	health_servicer = health.HealthServicer()
	health_servicer.set('', health_pb2.HealthCheckResponse.SERVING)
	health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)

	service_names = (
		receipt_parsing_pb2.DESCRIPTOR.services_by_name["ReceiptParsingService"].full_name,
		reflection.SERVICE_NAME,
		health.SERVICE_NAME,
	)
	reflection.enable_server_reflection(service_names, server)

	listen_addr = f"[::]:{port}"
	server.add_insecure_port(listen_addr)
	server.start()
	
	log.info("Server is ready and listening", extra={"address": listen_addr})
	
	def signal_handler(signum, frame):
		log.info("Received shutdown signal, stopping server gracefully")
		server.stop(grace=30)
		sys.exit(0)
	
	signal.signal(signal.SIGTERM, signal_handler)
	signal.signal(signal.SIGINT, signal_handler)
	
	try:
		server.wait_for_termination()
	except KeyboardInterrupt:
		log.info("Keyboard interrupt received, stopping server")
		server.stop(grace=30)


def main() -> None:
	parser = argparse.ArgumentParser(
		prog="arian-receipts",
		description="Receipt processing gRPC microservice"
	)
	parser.add_argument(
		"--port",
		type=int,
		default=50051,
		help="gRPC server port (default: 50051)"
	)
	args = parser.parse_args()
	
	try:
		serve(port=args.port)
	except Exception as e:
		log.error("Server failed to start", extra={"error": str(e)})
		sys.exit(1)


if __name__ == "__main__":
	main()
