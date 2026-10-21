# Tapestry

An open source, fully local alternative to Yoto and Tonies. Tap an NFC card or figure on a small player and it plays a story. You own the audio, the card mappings and all the data, and nothing goes through a cloud service. That also means you can add stories in any language, including Dutch.

## How it works

1. The **server** stores your audio and the mapping from each NFC card ID to a file. Its web portal is where you upload audio and assign cards.
2. The **player** (a Raspberry Pi with an NFC reader and a speaker) reads a card and asks the server what it plays. It downloads the file if it's new or changed, caches it, and plays it. Cached cards keep working offline.
3. A card the server doesn't know is logged, and it appears in the portal's **Waiting** tab, ready to assign to audio.

## Layout

    server/    FastAPI + SQLite server and web portal (see server/README.md)
    player/    Raspberry Pi player daemon and setup guide (see player/SETUP.md)

## Quick start

**Server** (any machine on your network):

    cd server
    pip install -r requirements.txt
    python server.py        # portal at http://<host>:8080

**Player** (Raspberry Pi): follow `player/SETUP.md`. You can test everything with typed card IDs before the NFC hardware arrives.

## Status

Early prototype. The wiring, player and server have not yet been run together on real hardware.
