"""Entry point: `python server.py` or `uvicorn server:app`."""
import os

from app.main import create_app

app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
