"""The player's behaviour.

Card placed:  play the cached copy straight away, and check the server in the background.
Card removed: save the position and stop. Stopping also releases the audio device, so the amp goes quiet.
Card back:    carry on from the saved position.
"""
import logging
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from .library import Refresh
from .readers import PRESENT, QUIT, REMOVED, Event

log = logging.getLogger(__name__)
REFRESHED = "refreshed"
REWIND = 2.0  # seconds to back up when resuming, for context


class Daemon:
    def __init__(self, reader, library, player, positions):
        self.reader, self.library, self.player, self.positions = reader, library, player, positions
        self.events: queue.Queue = queue.Queue()
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="refresh")
        self.card: str | None = None         # card on the reader right now
        self.loaded: str | None = None       # card whose audio is loaded (playing, or stopped with its position saved)
        self.loaded_path = None
        self.paused = False                  # loaded card was removed; player is stopped
        self.waiting: str | None = None      # card we're downloading for, with nothing cached to play meanwhile
        self.started = 0.0

    def run(self) -> None:
        threading.Thread(target=self._pump, daemon=True).start()
        while True:
            try:
                event = self.events.get(timeout=0.25)
            except queue.Empty:
                event = None
            if event and event.kind == QUIT:
                break
            try:
                if event is None:
                    self._tick()
                elif event.kind == PRESENT:
                    self._on_present(event.uid)
                elif event.kind == REMOVED:
                    self._on_removed()
                elif event.kind == REFRESHED:
                    self._on_refreshed(event.uid, event.data)
            except Exception:
                log.exception("Failed handling %s", event)
        self._remember()
        self.pool.shutdown(wait=False, cancel_futures=True)
        self.player.close()

    def stop(self) -> None:
        self.events.put(Event(QUIT))

    def _pump(self) -> None:
        try:
            for event in self.reader.events():
                self.events.put(event)
        finally:
            self.stop()

    # ---- card events --------------------------------------------------

    def _on_present(self, uid: str) -> None:
        log.info("Card %s", uid)
        self.card, self.waiting = uid, None
        if uid == self.loaded and not self.paused:
            return  # already playing this card
        if uid == self.loaded and self.loaded_path and self.loaded_path.exists():
            log.info("Resuming")
            self._start(uid, self.loaded_path)
        else:
            self._remember()
            path = self.library.cached(uid)
            if path:
                self._start(uid, path)
            else:
                log.info("Nothing cached for %s, fetching from the server", uid)
                self._halt()
                self.waiting = uid
        self._refresh_in_background(uid)

    def _on_removed(self) -> None:
        self.card = self.waiting = None
        if self.loaded and not self.paused:
            log.info("Card removed, stopping")
            self._remember()
            self.player.stop()
            self.paused = True

    def _tick(self) -> None:
        if self.loaded and not self.paused and time.monotonic() - self.started > 2 and self.player.is_idle():
            log.info("Finished %s", self.loaded)
            self.positions.clear(self.loaded)
            self.loaded = self.loaded_path = None

    # ---- background server check --------------------------------------

    def _refresh_in_background(self, uid: str) -> None:
        def work():
            try:
                result = self.library.refresh(uid)
            except Exception:
                log.exception("Server check failed for %s", uid)
                result = Refresh("error")
            self.events.put(Event(REFRESHED, uid, result))

        self.pool.submit(work)

    def _on_refreshed(self, uid: str, result: Refresh) -> None:
        if result.status == "unknown":
            log.info("No audio for %s. Assign it in the portal's Waiting tab.", uid)
            if self.loaded == uid:
                self._halt()
                self.positions.clear(uid)
            return
        if result.path is None:
            if self.waiting == uid:
                log.warning("Can't play %s: nothing cached and the server isn't available", uid)
            return
        if self.loaded == uid:
            if result.changed:
                log.info("Audio for %s changed on the server, switching to the new version", uid)
                self.positions.clear(uid)
                if self.paused:
                    self.loaded_path = result.path
                else:
                    self._start(uid, result.path)
        elif self.waiting == uid and self.card == uid:
            self.waiting = None
            self._start(uid, result.path)  # the download finished while the card is still there

    # ---- playback helpers ---------------------------------------------

    def _start(self, uid: str, path) -> None:
        self.player.play(path, max(0.0, self.positions.get(uid) - REWIND))
        self.loaded, self.loaded_path, self.paused = uid, path, False
        self.started = time.monotonic()

    def _halt(self) -> None:
        if self.loaded and not self.paused:
            self.player.stop()
        self.loaded = self.loaded_path = None
        self.paused = False

    def _remember(self) -> None:
        if self.loaded and not self.paused:
            pos = self.player.position()
            if pos is not None:
                self.positions.set(self.loaded, pos)