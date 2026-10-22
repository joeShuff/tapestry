"""Entry point: python -m tapestry_player [--config config.toml] [--reader stdin]"""
import argparse
import logging
import shutil
import signal

from .audio import MpvPlayer
from .config import load_config
from .daemon import Daemon
from .library import Library, ServerClient
from .readers import make_reader
from .state import PositionStore


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m tapestry_player")
    ap.add_argument("-c", "--config", default="config.toml")
    ap.add_argument("--reader", choices=["pn532", "stdin"], help="override the reader in the config")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if not shutil.which("mpv"):
        raise SystemExit("mpv is not installed. Run: sudo apt install mpv")

    cfg = load_config(args.config)
    cfg.reader = args.reader or cfg.reader
    cfg.data_dir.mkdir(parents=True, exist_ok=True)

    client = ServerClient(cfg.server_url, cfg.lookup_timeout, cfg.download_timeout)
    daemon = Daemon(
        make_reader(cfg.reader, cfg.tag_misses),
        Library(client, cfg.data_dir),
        MpvPlayer(cfg.audio_device, cfg.volume),
        PositionStore(cfg.data_dir / "positions.json"),
    )
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: daemon.stop())
    daemon.run()


if __name__ == "__main__":
    main()