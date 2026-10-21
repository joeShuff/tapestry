"""Endpoints the management portal calls."""
from fastapi import APIRouter, Depends, File, Form, UploadFile

from ..deps import get_service
from ..schemas import FailedScanOut, FileOut, MappingIn, MappingOut, MappingRow, TitleIn
from ..services import CardService

router = APIRouter(prefix="/api/v1", tags=["portal"])


# audio files
@router.get("/files", response_model=list[FileOut])
def list_files(svc: CardService = Depends(get_service)):
    return svc.list_files()


@router.post("/files", response_model=FileOut, status_code=201)
def upload_file(file: UploadFile = File(...), title: str = Form(""), svc: CardService = Depends(get_service)):
    return svc.upload_file(file.file, file.filename or "", title)


@router.patch("/files/{file_id}", response_model=FileOut)
def rename_file(file_id: int, body: TitleIn, svc: CardService = Depends(get_service)):
    return svc.rename_file(file_id, body.title)


@router.put("/files/{file_id}/content", response_model=FileOut)
def replace_file(file_id: int, file: UploadFile = File(...), svc: CardService = Depends(get_service)):
    return svc.replace_file(file_id, file.file, file.filename or "")


@router.delete("/files/{file_id}", status_code=204)
def delete_file(file_id: int, svc: CardService = Depends(get_service)):
    svc.delete_file(file_id)


# card mappings
@router.get("/mappings", response_model=list[MappingRow])
def list_mappings(svc: CardService = Depends(get_service)):
    return svc.list_mappings()


@router.put("/mappings/{uid}", response_model=MappingOut)
def assign_card(uid: str, body: MappingIn, svc: CardService = Depends(get_service)):
    return svc.assign_card(uid, body.file_id, body.label)


@router.delete("/mappings/{uid}", status_code=204)
def remove_mapping(uid: str, svc: CardService = Depends(get_service)):
    svc.remove_mapping(uid)


# failed scans
@router.get("/failed", response_model=list[FailedScanOut])
def list_failed(svc: CardService = Depends(get_service)):
    return svc.list_failed_scans()


@router.delete("/failed/{uid}", status_code=204)
def dismiss_failed(uid: str, svc: CardService = Depends(get_service)):
    svc.dismiss_failed_scan(uid)
