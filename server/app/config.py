"""Paths and settings. Everything environment-specific lives here."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
AUDIO_DIR = DATA_DIR / "audio"
DB_PATH = DATA_DIR / "server.db"
STATIC_DIR = BASE_DIR / "static"
ALLOWED_EXTENSIONS = {".mp3", ".wav", ".flac", ".ogg", ".opus", ".m4a", ".aac"}
