"""Every setting of the project, in one place.

Each value can be set in `.env` or in the shell, using the same name as the variable here.
No other module reads `os.environ`. Run `python main.py config` to see the values in use.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")


def _bool(raw: str) -> bool:
    return raw.strip().lower() in ("1", "true", "yes", "on")


def env(name: str, default, cast=str):
    """Read one setting. Unset means the default.

    For text settings an empty value is kept as empty (it means "don't send"). For numbers,
    flags and lists an empty value means the default.
    """
    raw = os.environ.get(name)
    if raw is None:
        return default
    raw = raw.strip()
    if cast is str:
        return raw
    if raw == "":
        return default
    return cast(raw)


def _path(value: str) -> str:
    return str((ROOT / value).resolve())


# --- keys ------------------------------------------------------------------------------------
LLM_API_KEY = env("LLM_API_OR", "") or env("OPENROUTER_API_KEY", "")

# --- LLM (writes claims and answers) ---------------------------------------------------------
LLM_MODEL = env("LLM_MODEL", "openai/gpt-6-luna")
LLM_BASE_URL = env("LLM_BASE_URL", "https://openrouter.ai/api/v1")
LLM_REASONING_EFFORT = env("LLM_REASONING_EFFORT", "low")  # empty = don't send
LLM_TEMPERATURE = env("LLM_TEMPERATURE", "")  # empty = don't send (the GPT-6 family rejects it)
LLM_MAX_TOKENS = env("LLM_MAX_TOKENS", 1500, int)
LLM_TIMEOUT_S = env("LLM_TIMEOUT_S", 90.0, float)
LLM_MAX_RETRIES = env("LLM_MAX_RETRIES", 3, int)
LLM_REQUIRE_PARAMETERS = env("LLM_REQUIRE_PARAMETERS", True, _bool)
LLM_APP_TITLE = env("LLM_APP_TITLE", "rag-conflicts")
LLM_HTTP_REFERER = env("LLM_HTTP_REFERER", "local-demo")
# Used to work out the cost when OpenRouter does not report it (USD per million tokens).
LLM_PRICE_IN_PER_M = env("LLM_PRICE_IN_PER_M", 0.10, float)
LLM_PRICE_OUT_PER_M = env("LLM_PRICE_OUT_PER_M", 0.50, float)

# --- embeddings ------------------------------------------------------------------------------
EMBEDDING_MODEL = env("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
MODELS_CACHE_DIR = _path(env("MODELS_CACHE_DIR", "./models"))

# --- retrieval -------------------------------------------------------------------------------
TOP_K = env("TOP_K", 6, int)
SCORE_THRESHOLD = env("SCORE_THRESHOLD", 0.58, float)  # drop hits below this cosine score
SCORE_MARGIN = env("SCORE_MARGIN", 0.10, float)  # also drop hits more than this below the best; 0 = off
MAX_CONTEXT_DOCS = env("MAX_CONTEXT_DOCS", 10, int)

# --- qdrant ----------------------------------------------------------------------------------
QDRANT_MODE = env("QDRANT_MODE", "embedded")  # embedded | server
QDRANT_PATH = _path(env("QDRANT_PATH", "./qdrant_data"))
QDRANT_URL = env("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = env("QDRANT_API_KEY", "")
QDRANT_COLLECTION = env("QDRANT_COLLECTION", "helios_docs")

# --- corpus ----------------------------------------------------------------------------------
CORPUS_DIR = _path(env("CORPUS_DIR", "./data/corpus"))
QUESTIONS_FILE = _path(env("QUESTIONS_FILE", "./questions.json"))

# --- langsmith (the langsmith library reads these from the environment itself) ---------------
LANGSMITH_TRACING = env("LANGSMITH_TRACING", False, _bool)
LANGSMITH_API_KEY = env("LANGSMITH_API_KEY", "")
LANGSMITH_PROJECT = env("LANGSMITH_PROJECT", "rag-conflicts")
TRACING_ON = LANGSMITH_TRACING and bool(LANGSMITH_API_KEY)
TRACING_WARNING = (
    "LANGSMITH_TRACING=true but no LANGSMITH_API_KEY is set, so tracing is off."
    if LANGSMITH_TRACING and not LANGSMITH_API_KEY else ""
)
# Send traces to our project by default, and never try to trace without a key.
os.environ["LANGSMITH_PROJECT"] = LANGSMITH_PROJECT
os.environ["LANGSMITH_TRACING"] = "true" if TRACING_ON else "false"

# --- eval ------------------------------------------------------------------------------------
EVAL_DATASET_NAME = env("EVAL_DATASET_NAME", "rag-conflicts-demo")
EVAL_EXPERIMENT_PREFIX = env("EVAL_EXPERIMENT_PREFIX", "rag-conflicts")
# The model that grades answers against the reference answers. Default: the same as LLM_MODEL
# (cheap, but a model grading its own kind of output is biased; set another model to avoid that).
EVAL_JUDGE_MODEL = env("EVAL_JUDGE_MODEL", "") or LLM_MODEL

# --- output ----------------------------------------------------------------------------------
SHOW_SCORES = env("SHOW_SCORES", True, _bool)
LOG_LEVEL = env("LOG_LEVEL", "INFO").upper() or "INFO"

# --- budget ----------------------------------------------------------------------------------
BUDGET_USD = env("BUDGET_USD", 4.0, float)
SPEND_FILE = _path(env("SPEND_FILE", "./.spend.json"))  # running total of money spent by this app

SECRET_NAMES = {"LLM_API_KEY", "QDRANT_API_KEY", "LANGSMITH_API_KEY"}


def _mask(value: str) -> str:
    if not value:
        return "(not set)"
    return value[:6] + "..." + f" ({len(value)} chars)"


def as_dict() -> dict:
    """All settings, with secrets hidden. Used by `python main.py config`."""
    out = {}
    for name, value in globals().items():
        if not name.isupper() or name in ("ROOT", "SECRET_NAMES", "TRACING_WARNING"):
            continue
        if name in SECRET_NAMES:
            value = _mask(value)
        elif value == "":
            value = "(empty: not sent)"
        out[name] = value
    return out
