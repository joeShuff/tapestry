"""CardService: business rules. Talks to DatabaseManager and AudioStore, never to SQL or HTTP."""
import re
from dataclasses import asdict
from pathlib import Path
from typing import BinaryIO

from .database import DatabaseManager
from .errors import InvalidInput, NotFound
from .storage import AudioStore


def normalize_uid(raw: str) -> str:
    """Card IDs are case-insensitive and may contain colons, dashes or spaces."""
    uid = re.sub(r"[\s:\-]", "", raw).upper()
    if not re.fullmatch(r"[0-9A-Z]{4,64}", uid):
        raise InvalidInput("Invalid card ID")
    return uid


class CardService:
    def __init__(self, db: DatabaseManager, store: AudioStore):
        self.db = db
        self.store = store

    # ---- device -----------------------------------------------------------

    def lookup_token(self, raw_uid: str) -> dict:
        """Find what a card plays. Unknown cards are recorded so the portal can show them."""
        uid = normalize_uid(raw_uid)
        mapping = self.db.find_mapping(uid)
        if mapping is None:
            self.db.record_failed_scan(uid)
            raise NotFound("Unknown card")
        return {"uid": uid, "label": mapping["label"], "file": self._present(mapping["file"])}

    def file_for_download(self, file_id: int) -> tuple[Path, dict]:
        file = self._require_file(file_id)
        return self.store.path(file["stored"]), file

    # ---- audio files ------------------------------------------------------

    def list_files(self) -> list[dict]:
        return [self._present(f) for f in self.db.list_files()]

    def upload_file(self, source: BinaryIO, filename: str, title: str) -> dict:
        saved = self.store.save(source, filename)
        file = self.db.add_file(
            title=title.strip() or Path(filename).stem, filename=filename, **asdict(saved)
        )
        return self._present(file)

    def rename_file(self, file_id: int, title: str) -> dict:
        self._require_file(file_id)
        if not title.strip():
            raise InvalidInput("Title can't be empty")
        return self._present(self.db.rename_file(file_id, title.strip()))

    def replace_file(self, file_id: int, source: BinaryIO, filename: str) -> dict:
        """New audio, same file ID: mappings stay and the hash changes so devices re-download."""
        old = self._require_file(file_id)
        saved = self.store.save(source, filename)
        updated = self.db.update_file_content(file_id, filename=filename, **asdict(saved))
        self.store.delete(old["stored"])
        return self._present(updated)

    def delete_file(self, file_id: int) -> None:
        file = self._require_file(file_id)
        self.db.delete_file(file_id)
        self.store.delete(file["stored"])

    # ---- card mappings ----------------------------------------------------

    def list_mappings(self) -> list[dict]:
        return self.db.list_mappings()

    def assign_card(self, raw_uid: str, file_id: int, label: str) -> dict:
        uid = normalize_uid(raw_uid)
        self._require_file(file_id)
        self.db.assign_card(uid, file_id, label.strip())
        return {"uid": uid, "file_id": file_id, "label": label.strip()}

    def remove_mapping(self, raw_uid: str) -> None:
        self.db.remove_mapping(normalize_uid(raw_uid))

    # ---- failed scans -----------------------------------------------------

    def list_failed_scans(self) -> list[dict]:
        return self.db.list_failed_scans()

    def dismiss_failed_scan(self, raw_uid: str) -> None:
        self.db.dismiss_failed_scan(normalize_uid(raw_uid))

    # ---- helpers ----------------------------------------------------------

    def _require_file(self, file_id: int) -> dict:
        file = self.db.get_file(file_id)
        if file is None:
            raise NotFound("Audio file not found")
        return file

    @staticmethod
    def _present(file: dict) -> dict:
        public = {k: v for k, v in file.items() if k != "stored"}
        public["download_url"] = f"/api/v1/files/{file['id']}/download"
        return public
