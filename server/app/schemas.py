"""Request and response shapes for the HTTP API."""
from pydantic import BaseModel


class FileOut(BaseModel):
    id: int
    title: str
    filename: str
    mime: str
    size: int
    sha256: str
    updated: float
    download_url: str
    uses: int | None = None


class TokenOut(BaseModel):
    uid: str
    label: str
    file: FileOut


class TitleIn(BaseModel):
    title: str


class MappingIn(BaseModel):
    file_id: int
    label: str = ""


class MappingOut(BaseModel):
    uid: str
    file_id: int
    label: str


class MappingRow(MappingOut):
    updated: float
    file_title: str


class FailedScanOut(BaseModel):
    uid: str
    count: int
    first_seen: float
    last_seen: float
