import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from huggingface_hub import snapshot_download

load_dotenv()

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
	level=LOG_LEVEL,
	format="%(asctime)s %(levelname)s %(name)s — %(message)s",
	datefmt="%Y-%m-%d %H:%M:%S",
	force=True,
)
log = logging.getLogger(__name__)

# model download settings
HF_REPO_ID = os.getenv("HF_REPO_ID", "microsoft/Phi-3-mini-4k-instruct-gguf").strip()
HF_FILENAME = os.getenv("HF_FILENAME", "Phi-3-mini-4k-instruct-q4.gguf").strip()
HF_AUTH = os.getenv("HF_TOKEN")

MODELS_DIR = Path("models")
MODELS_DIR.mkdir(parents=True, exist_ok=True)
LOCAL_MODEL_FILE = MODELS_DIR / HF_FILENAME

# llama-cpp runtime settings
LLAMA_THREADS = int(os.getenv("LLAMA_THREADS", os.cpu_count() or 4))
LLAMA_CTX = int(os.getenv("LLAMA_CTX", "4096"))
LLAMA_MAX_TOK = int(os.getenv("LLAMA_MAX_TOK", "384"))
LLAMA_TEMP = float(os.getenv("LLAMA_TEMP", "0.0"))
LLAMA_TOP_P = float(os.getenv("LLAMA_TOP_P", "0.95"))
LLAMA_TOP_K = int(os.getenv("LLAMA_TOP_K", "50"))


def ensure_model_present():
	if LOCAL_MODEL_FILE.exists():
		return

	log.info("downloading %s from %s ...", HF_FILENAME, HF_REPO_ID)

	snapshot_download(
		repo_id=HF_REPO_ID,
		repo_type="model",
		local_dir=str(MODELS_DIR),
		local_dir_use_symlinks=False,
		allow_patterns=[HF_FILENAME],
		token=HF_AUTH,
		resume_download=True,
	)

	if not LOCAL_MODEL_FILE.exists():
		raise FileNotFoundError(f"download finished but {LOCAL_MODEL_FILE} is missing")

	log.info("model download complete")
