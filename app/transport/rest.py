from __future__ import annotations

import logging

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..config import Settings
from ..schemas import ErrorBody, ErrorResponse, ProviderState, Receipt
from ..service import ReceiptService

log = logging.getLogger(__name__)


class Health(BaseModel):
	status: str = "ok"


def http_error(
	code: str, message: str, status: int, details: dict | None = None
) -> JSONResponse:
	return JSONResponse(
		status_code=status,
		content=ErrorResponse(
			error=ErrorBody(code=code, message=message, details=details or {})
		).model_dump(),
	)


def build_router(settings: Settings, svc: ReceiptService) -> APIRouter:
	router = APIRouter(prefix="/v1")

	@router.get("/health", response_model=Health)
	async def health() -> Health:
		return Health()

	@router.get("/providers", response_model=list[ProviderState])
	async def providers() -> list[ProviderState]:
		return svc.provider_states()

	@router.post("/providers/{provider}/parse", response_model=Receipt)
	async def parse(provider: str, file: UploadFile = File(...)) -> JSONResponse:
		if not file:
			return http_error("VALIDATION_ERROR", "file is required", 400)

		if file.content_type not in settings.allowed_mime_types:
			return http_error(
				"UNSUPPORTED_MEDIA_TYPE", "only JPEG or PNG are supported", 415
			)

		blob = await file.read()
		if len(blob) > settings.max_upload_mb * 1024 * 1024:
			return http_error(
				"PAYLOAD_TOO_LARGE", f"file exceeds {settings.max_upload_mb} MB", 413
			)

		try:
			rec = svc.parse(provider, blob, file.content_type)
			return JSONResponse(rec.model_dump())
		except KeyError:
			return http_error(
				"UNKNOWN_PROVIDER", f"provider {provider!r} not registered", 404
			)
		except RuntimeError as e:
			return http_error("PROVIDER_UNAVAILABLE", str(e), 400)
		except Exception as e:
			log.exception("parse failed")
			return http_error(
				"INTERNAL", "failed to parse receipt", 500, {"reason": str(e)}
			)

	return router
