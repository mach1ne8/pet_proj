import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

if not POSTGRES_PASSWORD:
    raise RuntimeError("POSTGRES_PASSWORD is not set")


DATABASE_URL = (
    "postgresql+asyncpg://"
    f"arena:{POSTGRES_PASSWORD}"
    "@127.0.0.1:5432/"
    "negotiation_arena"
)


LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock").strip().lower()
LLM_BASE_URL = os.getenv(
    "LLM_BASE_URL",
    "http://127.0.0.1:11434/v1",
).rstrip("/")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "negotiation-arena")
LLM_TIMEOUT_SECONDS = float(
    os.getenv("LLM_TIMEOUT_SECONDS", "60")
)
