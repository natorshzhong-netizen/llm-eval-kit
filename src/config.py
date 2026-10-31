"""配置。"""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

API_BASE = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
TIMEOUT = int(os.getenv("LLM_TIMEOUT", 120))
CONCURRENCY = int(os.getenv("CONCURRENCY", 4))
