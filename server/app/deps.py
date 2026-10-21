"""FastAPI dependencies."""
from fastapi import Request

from .services import CardService


def get_service(request: Request) -> CardService:
    return request.app.state.service
