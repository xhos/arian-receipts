import os
import logging

log = logging.getLogger(__name__)

__all__ = ["init_provider", "parse_receipt"]

if os.getenv("GEMINI_API_KEY"):
	log.info("using gemini")
	from .gemini import init_provider, parse_receipt
else:
	log.info("using local")
	from .local import init_provider, parse_receipt
