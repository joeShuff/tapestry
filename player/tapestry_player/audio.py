"""MpvPlayer: runs mpv in the background and drives it over its JSON IPC socket."""
import json
import logging
import os
import socket
import subprocess
import tempfile
import threading
import time

log = logging.getLogger(__name__)


class MpvPlayer:
    def __init__(self, device: str = "auto", volume: int = 70):
        self.device, self.volume = device, volume
        self.sock_path = os.path.join(tempfile.gettempdir(), "tapestry-mpv.sock")
        self.proc = self.sock = None
        self._buf, self._req = b"", 0
        self._lock = threading.Lock()

    # ---- playback -----------------------------------------------------

    def play(self, path, start: float = 0.0) -> None:
        reply = self.command("set_property", "start", f"{start:.1f}")
        if reply.get("error") != "success":
            log.warning("Could not set start position: %s", reply.get("error"))
        self.command("set_property", "pause", False)
        self.command("loadfile", str(path), "replace")

    def pause(self) -> None:
        self.command("set_property", "pause", True)

    def resume(self) -> None:
        self.command("set_property", "pause", False)

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:  # never start mpv just to stop it
            self.command("stop")

    def position(self) -> float | None:
        reply = self.command("get_property", "time-pos")
        return reply.get("data") if reply.get("error") == "success" else None

    def is_idle(self) -> bool:
        """True when nothing is loaded (a track finished or was stopped)."""
        return self.command("get_property", "idle-active").get("data") is True

    def close(self) -> None:
        self._drop_socket()
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()

    # ---- mpv process and socket ---------------------------------------

    def command(self, *args) -> dict:
        with self._lock:
            self._ensure_running()
            self._req += 1
            self.sock.sendall((json.dumps({"command": list(args), "request_id": self._req}) + "\n").encode())
            while True:
                while b"\n" not in self._buf:
                    chunk = self.sock.recv(4096)
                    if not chunk:
                        self._drop_socket()
                        raise ConnectionError("mpv closed the connection")
                    self._buf += chunk
                line, self._buf = self._buf.split(b"\n", 1)
                msg = json.loads(line)
                if msg.get("request_id") == self._req:  # skip async events
                    return msg

    def _ensure_running(self) -> None:
        if self.proc and self.proc.poll() is None and self.sock:
            return
        self._drop_socket()
        if self.proc is None or self.proc.poll() is not None:
            self._spawn()
        self._connect()

    def _spawn(self) -> None:
        if os.path.exists(self.sock_path):
            os.unlink(self.sock_path)
        args = ["mpv", "--idle=yes", "--no-video", "--no-terminal", "--really-quiet",
                f"--input-ipc-server={self.sock_path}", f"--volume={self.volume}"]
        if self.device == "null":
            args.append("--ao=null")
        elif self.device != "auto":
            args.append(f"--audio-device={self.device}")
        log.info("Starting mpv")
        try:
            self.proc = subprocess.Popen(args)
        except FileNotFoundError:
            raise RuntimeError("mpv is not installed. Run: sudo apt install mpv") from None

    def _connect(self) -> None:
        deadline = time.time() + 5
        while time.time() < deadline:
            s = socket.socket(socket.AF_UNIX)
            s.settimeout(3)
            try:
                s.connect(self.sock_path)
            except OSError:
                s.close()
                time.sleep(0.1)
                continue
            self.sock, self._buf = s, b""
            return
        raise RuntimeError("mpv did not start (is it installed?)")

    def _drop_socket(self) -> None:
        if self.sock:
            self.sock.close()
        self.sock = None