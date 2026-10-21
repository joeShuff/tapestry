"""Application factory: wires the layers together."""
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .database import DatabaseManager
from .errors import DomainError
from .routers import device, portal
from .services import CardService
from .storage import AudioStore


def create_app() -> FastAPI:
    app = FastAPI(title="Tapestry server")
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    app.state.service = CardService(
        DatabaseManager(config.DB_PATH),
        AudioStore(config.AUDIO_DIR, config.ALLOWED_EXTENSIONS),
    )

    @app.exception_handler(DomainError)
    def domain_error(_: Request, exc: DomainError):
        return JSONResponse(status_code=exc.status, content={"detail": str(exc)})

    app.include_router(device.router)
    app.include_router(portal.router)
    app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(config.STATIC_DIR / "index.html")

    return app
