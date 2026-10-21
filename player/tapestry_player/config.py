"""Settings: defaults, overridden by a TOML file."""
import tomllib
from dataclasses import dataclass, fields
from pathlib import Path


@dataclass
class Config:
    server_url: str = "http://localhost:8080"
    data_dir: Path = Path("~/.local/share/tapestry")
    reader: str = "pn532"         # "pn532" or "stdin" (type card IDs, for testing)
    audio_device: str = "auto"    # "auto", "null" (no sound), or a name from `mpv --audio-device=help`
    volume: int = 70
    tag_misses: int = 3           # missed polls before a card counts as removed
    lookup_timeout: float = 3.0
    download_timeout: float = 30.0


def load_config(path: str | None) -> Config:
    cfg = Config()
    if path and Path(path).expanduser().exists():
        with open(Path(path).expanduser(), "rb") as f:
            data = tomllib.load(f)
        known = {f.name for f in fields(Config)}
        for key, value in data.items():
            if key not in known:
                raise ValueError(f"Unknown setting in config: {key}")
            setattr(cfg, key, value)
    cfg.data_dir = Path(cfg.data_dir).expanduser()
    cfg.server_url = cfg.server_url.rstrip("/")
    return cfg
