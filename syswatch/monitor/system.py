

import platform
import socket
import time
import getpass
import psutil
import threading
import requests


class SystemInfo:
    LOCAL_IP_TTL = 30.0

    def __init__(self):
        self._lock      = threading.Lock()
        self._public_ip = "…"
        self._boot      = psutil.boot_time()
        self._uname     = platform.uname()
        self._hostname  = socket.gethostname()
        self._user      = getpass.getuser()
        self._distro_name = self._distro()
        self._local_ip  = "N/A"
        self._local_ip_at = 0.0
        threading.Thread(target=self._fetch_ip, daemon=True).start()

    def snapshot(self) -> dict:
        with self._lock:
            pub = self._public_ip
        return {
            "hostname":  self._hostname,
            "user":      self._user,
            "os":        f"{self._uname.system} {self._uname.release}",
            "distro":    self._distro_name,
            "arch":      self._uname.machine,
            "uptime":    self._uptime(),
            "local_ip":  self._cached_local_ip(),
            "public_ip": pub,
        }

    def _uptime(self) -> str:
        secs = int(time.time() - self._boot)
        d, r = divmod(secs, 86400)
        h, r = divmod(r, 3600)
        m, s = divmod(r, 60)
        parts = []
        if d:
            parts.append(f"{d}d")
        if h or d:
            parts.append(f"{h}h")
        parts.append(f"{m}m {s:02d}s")
        return " ".join(parts)

    def _fetch_ip(self):
        try:
            ip = requests.get("https://api.ipify.org", timeout=3).text.strip()
        except Exception:
            ip = "N/A"
        with self._lock:
            self._public_ip = ip

    def _cached_local_ip(self) -> str:
        now = time.monotonic()
        if now - self._local_ip_at >= self.LOCAL_IP_TTL:
            self._local_ip = self._read_local_ip()
            self._local_ip_at = now
        return self._local_ip

    @staticmethod
    def _read_local_ip() -> str:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "N/A"

    @staticmethod
    def _distro() -> str:
        try:
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        return line.split("=", 1)[1].strip().strip('"')
        except Exception:
            pass
        return platform.system()
