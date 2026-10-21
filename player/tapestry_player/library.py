"""Server lookups plus a local cache, so cards keep working offline."""
import hashlib
import json
import logging
import os
from pathlib import Path

import requests

log = logging.getLogger(__name__)


class ServerUnavailable(Exception):
    pass


class DownloadError(Exception):
    pass


class ServerClient:
    def __init__(self, base_url: str, lookup_timeout: float, download_timeout: float):
        self.base = base_url
        self.lookup_timeout = lookup_timeout
        self.download_timeout = download_timeout
        self.http = requests.Session()

    def lookup(self, uid: str) -> dict | None:
        """File info for a card, or None if the server doesn't know it."""
        try:
            r = self.http.get(f"{self.base}/api/v1/tokens/{uid}", timeout=self.lookup_timeout)
        except requests.RequestException as e:
            raise ServerUnavailable(str(e)) from e
        if r.status_code == 404:
            return None
        if r.status_code >= 500:
            raise ServerUnavailable(f"server error {r.status_code}")
        r.raise_for_status()
        return r.json()

    def download(self, url: str, dest: Path, expected_sha256: str) -> None:
        tmp = dest.with_name(dest.name + ".part")
        digest = hashlib.sha256()
        try:
            with self.http.get(self.base + url, stream=True,
                               timeout=(self.lookup_timeout, self.download_timeout)) as r:
                r.raise_for_status()
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(1 << 16):
                        f.write(chunk)
                        digest.update(chunk)
        except requests.RequestException as e:
            tmp.unlink(missing_ok=True)
            raise ServerUnavailable(str(e)) from e
        if digest.hexdigest() != expected_sha256:
            tmp.unlink(missing_ok=True)
            raise DownloadError("Downloaded file does not match the server's hash")
        os.replace(tmp, dest)


class Library:
    """Maps card IDs to cached audio files. Files are stored by hash, so identical audio is stored once."""

    def __init__(self, client: ServerClient, data_dir: Path):
        self.client = client
        self.audio_dir = data_dir / "audio"
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = data_dir / "index.json"
        try:
            self.index = json.loads(self.index_path.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            self.index = {}

    def resolve(self, uid: str) -> Path | None:
        """Path to this card's audio (downloading it if new or changed), or None if unknown."""
        cached = self._cached(self.index.get(uid))
        try:
            info = self.client.lookup(uid)
        except ServerUnavailable as e:
            log.warning("Server unreachable (%s); using cache", e)
            return cached
        if info is None:
            self._forget(uid)
            return None
        file = info["file"]
        path = self.audio_dir / (file["sha256"] + Path(file["filename"]).suffix.lower())
        if not path.exists():
            log.info("Downloading '%s' (%d KB)", file["title"], file["size"] // 1024)
            try:
                self.client.download(file["download_url"], path, file["sha256"])
            except ServerUnavailable as e:
                log.warning("Download failed (%s); using cached copy if any", e)
                return cached
        self.index[uid] = {"title": file["title"], "path": path.name}
        self._save()
        return path

    def _cached(self, entry: dict | None) -> Path | None:
        path = self.audio_dir / entry["path"] if entry else None
        return path if path and path.exists() else None

    def _forget(self, uid: str) -> None:
        if self.index.pop(uid, None) is not None:
            self._save()

    def _save(self) -> None:
        tmp = self.index_path.with_name("index.json.tmp")
        tmp.write_text(json.dumps(self.index))
        os.replace(tmp, self.index_path)
        used = {e["path"] for e in self.index.values()}
        for f in self.audio_dir.iterdir():  # drop audio no card refers to any more
            if f.name not in used and not f.name.endswith(".part"):
                f.unlink(missing_ok=True)
