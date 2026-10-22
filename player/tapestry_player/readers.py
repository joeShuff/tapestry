"""Card readers. Each yields Event('present', uid) when a card arrives and Event('removed') when it leaves."""
import logging
import sys
import time
from collections import namedtuple

log = logging.getLogger(__name__)
Event = namedtuple("Event", "kind uid data", defaults=(None, None))
PRESENT, REMOVED, QUIT = "present", "removed", "quit"


class TagTracker:
    """Turns raw polls (a card ID, or None for nothing) into present/removed events.

    A card only counts as gone after `misses` polls in a row without seeing it. While the current
    card is still being read, other cards are ignored: with two tags near the reader the PN532
    reports them alternately, and that must not look like a stream of new cards. A direct swap still
    works, because the new card takes over once the old one has been missing for `misses` polls.
    """

    def __init__(self, misses: int = 3):
        self.misses = misses
        self.present = None
        self.missed = 0

    def update(self, uid):
        if self.present is None:
            if uid:
                self.present, self.missed = uid, 0
                return Event(PRESENT, uid)
            return None
        if uid == self.present:
            self.missed = 0
            return None
        self.missed += 1                      # the current card wasn't seen this poll
        if self.missed < self.misses:
            return None
        self.missed = 0
        if uid:                               # another card has replaced it
            self.present = uid
            return Event(PRESENT, uid)
        self.present = None
        return Event(REMOVED)


class StdinReader:
    """For testing without hardware: type a card ID to tap it, press Enter on an empty line to remove it."""

    def events(self):
        print("Type a card ID to place a card. Empty line removes it. Ctrl+D quits.", flush=True)
        for line in sys.stdin:
            uid = line.strip().upper()
            yield Event(PRESENT, uid) if uid else Event(REMOVED)


class PN532Reader:
    """PN532 over I2C using Adafruit's library."""

    def __init__(self, misses: int = 3):
        import board
        import busio
        from adafruit_pn532.i2c import PN532_I2C

        self.pn = PN532_I2C(busio.I2C(board.SCL, board.SDA), debug=False)
        self.pn.SAM_configuration()
        self.misses = misses
        log.info("PN532 ready, firmware %s", self.pn.firmware_version)

    def events(self):
        tracker = TagTracker(self.misses)
        while True:
            try:
                raw = self.pn.read_passive_target(timeout=0.25)
            except (OSError, RuntimeError) as e:  # I2C hiccups are normal; keep going
                log.debug("Read error: %s", e)
                time.sleep(0.1)
                continue
            event = tracker.update(raw.hex().upper() if raw else None)
            if event:
                yield event


def make_reader(name: str, misses: int):
    if name == "stdin":
        return StdinReader()
    if name == "pn532":
        return PN532Reader(misses)
    raise ValueError(f"Unknown reader: {name}")


if __name__ == "__main__":  # hardware check: python -m tapestry_player.readers
    logging.basicConfig(level=logging.INFO)
    for event in PN532Reader().events():
        print(event, flush=True)