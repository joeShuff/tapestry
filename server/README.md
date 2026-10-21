# Tapestry server

Local server for an NFC audio player: stores audio, maps NFC card IDs to files, and serves both the device API and a web portal.

## Run
    pip install -r requirements.txt
    python server.py            # http://<host>:8080  (PORT and DATA_DIR env vars supported)

Data lives in `data/` (SQLite db plus `audio/`). API docs: `/docs`.

## Layout
    server.py            entry point
    app/main.py          app factory, wires the layers together
    app/routers/         HTTP only: device.py (player calls), portal.py (management calls)
    app/services.py      business rules (CardService); no SQL, no HTTP
    app/database.py      DatabaseManager: all SQL lives here
    app/storage.py       AudioStore: audio files on disk, hashing
    app/schemas.py       request/response models
    app/errors.py        domain errors, mapped to HTTP in main.py
    app/config.py        paths and settings
    static/              portal: index.html, style.css, app.js

## Device API
| Call | Result |
|---|---|
| `GET /api/v1/tokens/{uid}` | `200 {uid, label, file:{id,title,size,sha256,download_url}}` or `404` (the miss is logged for the portal) |
| `GET /api/v1/files/{id}/download` | the audio file (also sends `X-Content-SHA256`; supports range requests) |

Device logic: look up the token, compare `file.sha256` with the cached copy, download only if it differs. Card IDs are normalised (case, colons and spaces ignored), so `04:a1:b2:c3` and `04A1B2C3` are the same card.

## Portal
- **Waiting:** recent unknown scans, live-updating. Assign existing or newly uploaded audio in one dialog.
- **Cards:** view, change and remove mappings; add a card by typing its ID.
- **Audio:** upload, preview, rename, replace file (changes the hash so devices re-download), delete.

No authentication: keep it on your LAN.
