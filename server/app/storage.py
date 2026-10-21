"""AudioStore: audio bytes on disk. No database, no HTTP."""
import hashlib
import mimetypes
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from .errors import InvalidInput, UnsupportedMedia


@dataclass
class StoredAudio:
    stored: str
    size: int
    sha256: str
    mime: str


class AudioStore:
    def __init__(self, directory: Path, allowed_extensions: set[str]):
        self.directory = directory
        self.allowed = allowed_extensions
        self.directory.mkdir(parents=True, exist_ok=True)

    def save(self, source: BinaryIO, filename: str) -> StoredAudio:
        """Stream an upload to disk under a random name, hashing as it goes."""
        ext = Path(filename or "").suffix.lower()
        if ext not in self.allowed:
            raise UnsupportedMedia(f"Unsupported file type. Use: {', '.join(sorted(self.allowed))}")
        stored = uuid.uuid4().hex + ext
        digest, size = hashlib.sha256(), 0
        with open(self.directory / stored, "wb") as out:
            while chunk := source.read(1 << 20):
                out.write(chunk)
                digest.update(chunk)
                size += len(chunk)
        if size == 0:
            self.delete(stored)
            raise InvalidInput("The file is empty")
        mime = mimetypes.guess_type(stored)[0] or "application/octet-stream"
        return StoredAudio(stored, size, digest.hexdigest(), mime)

    def path(self, stored: str) -> Path:
        return self.directory / stored

    def delete(self, stored: str) -> None:
        self.path(stored).unlink(missing_ok=True)
