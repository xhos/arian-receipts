from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import grpc

from arian.v1 import receipt_parsing_pb2, receipt_parsing_pb2_grpc
from arian.v1.enums_pb2 import ReceiptEngine
from arian.v1.receipts_pb2 import Receipt, ReceiptItem
from .service import ReceiptService

if TYPE_CHECKING:
	from .config import Settings

log = logging.getLogger(__name__)


class ReceiptParsingServiceGrpc(receipt_parsing_pb2_grpc.ReceiptParsingServiceServicer):
	def __init__(self, settings: Settings, service: ReceiptService) -> None:
		self.settings = settings
		self.service = service

	def ParseImage(
		self,
		request: receipt_parsing_pb2.ParseImageRequest,
		context: grpc.ServicerContext,
	) -> receipt_parsing_pb2.ParseImageResponse:
		try:
			if not request.image_data:
				context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
				context.set_details("image_data is required")
				return receipt_parsing_pb2.ParseImageResponse()

			if request.content_type not in self.settings.allowed_mime_types:
				context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
				context.set_details("only JPEG or PNG are supported")
				return receipt_parsing_pb2.ParseImageResponse()

			if len(request.image_data) > self.settings.max_upload_mb * 1024 * 1024:
				context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
				context.set_details(f"image exceeds {self.settings.max_upload_mb} MB")
				return receipt_parsing_pb2.ParseImageResponse()

			provider_name = self._engine_to_provider_name(
				request.engine or ReceiptEngine.ENGINE_GEMINI
			)

			receipt = self.service.parse(
				provider_name, request.image_data, request.content_type
			)

			proto_receipt = self._receipt_to_proto(receipt)
			return receipt_parsing_pb2.ParseImageResponse(receipt=proto_receipt)

		except KeyError:
			context.set_code(grpc.StatusCode.NOT_FOUND)
			context.set_details(f"provider for engine {request.engine} not found")
			return receipt_parsing_pb2.ParseImageResponse()
		except RuntimeError as e:
			context.set_code(grpc.StatusCode.UNAVAILABLE)
			context.set_details(str(e))
			return receipt_parsing_pb2.ParseImageResponse()
		except Exception:
			log.exception("parse failed")
			context.set_code(grpc.StatusCode.INTERNAL)
			context.set_details("failed to parse image")
			return receipt_parsing_pb2.ParseImageResponse()

	def GetStatus(
		self,
		request: receipt_parsing_pb2.GetStatusRequest,
		context: grpc.ServicerContext,
	) -> receipt_parsing_pb2.GetStatusResponse:
		try:
			provider_states = self.service.provider_states()
			providers = []

			for state in provider_states:
				provider = receipt_parsing_pb2.ProviderStatus(
					name=state.name,
					kind=state.kind,
					available=state.available,
					model=state.model,
				)
				if state.reason:
					provider.reason = state.reason
				providers.append(provider)

			return receipt_parsing_pb2.GetStatusResponse(
				providers=providers, service_version="0.3.0"
			)

		except Exception:
			log.exception("status check failed")
			context.set_code(grpc.StatusCode.INTERNAL)
			context.set_details("failed to get status")
			return receipt_parsing_pb2.GetStatusResponse()

	def _engine_to_provider_name(self, engine: ReceiptEngine.ValueType) -> str:
		if engine == ReceiptEngine.ENGINE_GEMINI:
			return "gemini"
		elif engine == ReceiptEngine.ENGINE_LOCAL:
			return "local"
		else:
			raise KeyError(f"unknown engine: {engine}")

	def _receipt_to_proto(self, receipt) -> Receipt:
		proto_receipt = Receipt()
		proto_receipt.engine = self._provider_name_to_engine(
			receipt.provider_name if hasattr(receipt, "provider_name") else "gemini"
		)

		if receipt.merchant:
			proto_receipt.merchant = receipt.merchant
		if receipt.total:
			proto_receipt.total_amount.currency_code = "USD"
			proto_receipt.total_amount.units = int(receipt.total)
			proto_receipt.total_amount.nanos = int(
				(receipt.total - int(receipt.total)) * 1e9
			)

		for item in receipt.items:
			proto_item = ReceiptItem()
			proto_item.name = item.name
			proto_item.quantity = item.qty
			if item.price:
				proto_item.unit_price.currency_code = "USD"
				proto_item.unit_price.units = int(item.price)
				proto_item.unit_price.nanos = int((item.price - int(item.price)) * 1e9)
			proto_receipt.items.append(proto_item)

		return proto_receipt

	def _provider_name_to_engine(self, provider_name: str) -> ReceiptEngine.ValueType:
		if provider_name == "gemini":
			return ReceiptEngine.ENGINE_GEMINI
		elif provider_name == "local":
			return ReceiptEngine.ENGINE_LOCAL
		else:
			return ReceiptEngine.ENGINE_UNSPECIFIED
