"""The player's behaviour: card placed means play, removed means pause, put back means resume."""
import logging
import queue
import threading
import time

from .readers import PRESENT, QUIT, REMOVED, Event

log = logging.getLogger(__name__)


class Daemon:
    def __init__(self, reader, library, player, positions):
        self.reader, self.library, self.player, self.positions = reader, library, player, positions
        self.events: queue.Queue = queue.Queue()
        self.loaded: str | None = None   # card whose audio is loaded in the player
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
            except Exception:
                log.exception("Failed handling %s", event)
        self._remember()
        self.player.close()

    def stop(self) -> None:
        self.events.put(Event(QUIT, None))

    def _pump(self) -> None:
        try:
            for event in self.reader.events():
                self.events.put(event)
        finally:
            self.stop()

    def _on_present(self, uid: str) -> None:
        log.info("Card %s", uid)
        if uid == self.loaded:
            self.player.resume()
            return
        self._remember()
        path = self.library.resolve(uid)
        if path is None:
            log.info("No audio for %s. Assign it in the portal's Waiting tab.", uid)
            self.player.stop()
            self.loaded = None
            return
        self.player.play(path, max(0.0, self.positions.get(uid) - 2))  # back up 2s for context
        self.loaded, self.started = uid, time.monotonic()

    def _on_removed(self) -> None:
        if self.loaded:
            log.info("Card removed, pausing")
            self._remember()
            self.player.pause()

    def _tick(self) -> None:
        if self.loaded and time.monotonic() - self.started > 2 and self.player.is_idle():
            log.info("Finished %s", self.loaded)
            self.positions.clear(self.loaded)
            self.loaded = None

    def _remember(self) -> None:
        if self.loaded:
            pos = self.player.position()
            if pos is not None:
                self.positions.set(self.loaded, pos)
