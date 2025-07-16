import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from .providers import init_provider, parse_receipt

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
	log.info("starting service")
	init_provider()
	log.info("ready")
	yield


app = FastAPI(title="arian-receipts", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health():
	return {"status": "ok"}


@app.post("/parse")
async def parse(file: UploadFile = File(...)):
	try:
		log.info("received %s (%s)", file.filename, file.content_type)
		t0 = time.perf_counter()
		data = parse_receipt(await file.read())
		log.info("served in %.2f s", time.perf_counter() - t0)
		return JSONResponse(content=data)

	except Exception as exc:
		log.exception("parsing failed")
		raise HTTPException(400, detail=str(exc))
