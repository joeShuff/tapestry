"""Remembers where each card stopped, so putting it back resumes."""
import json
import os
from pathlib import Path


class PositionStore:
    def __init__(self, path: Path):
        self.path = path
        try:
            self.data = json.loads(path.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            self.data = {}

    def get(self, uid: str) -> float:
        return float(self.data.get(uid, 0.0))

    def set(self, uid: str, seconds: float) -> None:
        self.data[uid] = round(seconds, 1)
        self._save()

    def clear(self, uid: str) -> None:
        if self.data.pop(uid, None) is not None:
            self._save()

    def _save(self) -> None:
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(json.dumps(self.data))
        os.replace(tmp, self.path)
