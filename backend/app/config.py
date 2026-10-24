"""Small settings module; avoids extra configuration dependencies."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load backend/.env when the app is run from the backend folder.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

APP_NAME = "CareerPilot API"
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./careerpilot.db")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
