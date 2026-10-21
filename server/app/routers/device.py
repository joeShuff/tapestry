"""Endpoints the player device calls."""
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from ..deps import get_service
from ..schemas import TokenOut
from ..services import CardService

router = APIRouter(prefix="/api/v1", tags=["device"])


@router.get("/tokens/{uid}", response_model=TokenOut)
def lookup_token(uid: str, svc: CardService = Depends(get_service)):
    """File info and hash for a card, or 404 (the miss is logged for the portal)."""
    return svc.lookup_token(uid)


@router.get("/files/{file_id}/download")
def download(file_id: int, svc: CardService = Depends(get_service)):
    path, file = svc.file_for_download(file_id)
    return FileResponse(path, media_type=file["mime"], filename=file["filename"],
                        headers={"X-Content-SHA256": file["sha256"]})
