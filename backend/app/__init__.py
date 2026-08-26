from pathlib import Path

from dotenv import load_dotenv

# Load backend/.env before any module reads config at import time (db engine,
# CORS origins). Real environment variables take precedence over the file.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
