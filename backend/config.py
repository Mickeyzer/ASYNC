"""Server-only configuration. Environment variables take precedence over .env."""

import os
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=False)

# The SDK also forwards this value as the provider's request deadline.
GEMINI_TIMEOUT_MS = 60_000


def gemini_settings():
    return {
        "api_key": os.environ.get("GEMINI_API_KEY", "").strip(),
        "model": os.environ.get("GEMINI_MODEL", "").strip() or "gemini-3.5-flash-lite",
    }
