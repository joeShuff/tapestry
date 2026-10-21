"""Card readers. Each yields Event('present', uid) when a card arrives and Event('removed') when it leaves."""
import logging
import sys
from collections import namedtuple

log = logging.getLogger(__name__)
Event = namedtuple("Event", "kind uid")
PRESENT, REMOVED, QUIT = "present", "removed", "quit"


class StdinReader:
    """For testing without hardware: type a card ID to tap it, press Enter on an empty line to remove it."""

    def events(self):
        print("Type a card ID to place a card. Empty line removes it. Ctrl+D quits.", flush=True)
        for line in sys.stdin:
            uid = line.strip().upper()
            yield Event(PRESENT, uid) if uid else Event(REMOVED, None)


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
        import time

        present, missed = None, 0
        while True:
            try:
                raw = self.pn.read_passive_target(timeout=0.25)
            except (OSError, RuntimeError) as e:  # I2C hiccups are normal; keep going
                log.debug("Read error: %s", e)
                time.sleep(0.1)
                continue
            if raw:
                uid, missed = raw.hex().upper(), 0
                if uid != present:
                    present = uid
                    yield Event(PRESENT, uid)
            elif present:
                missed += 1
                if missed >= self.misses:
                    present = None
                    yield Event(REMOVED, None)


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
