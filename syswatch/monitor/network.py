
import psutil
import threading
import time
from typing import List


class NetworkMonitor:
    def __init__(self):
        self._lock = threading.Lock()
        self._prev = psutil.net_io_counters()
        self._prev_time = time.monotonic()

    def snapshot(self) -> dict:
        curr = psutil.net_io_counters()
        now = time.monotonic()
        with self._lock:
            elapsed = max(now - self._prev_time, 0.001)
            up  = max(curr.bytes_sent - self._prev.bytes_sent, 0) / elapsed
            dn  = max(curr.bytes_recv - self._prev.bytes_recv, 0) / elapsed
            self._prev = curr
            self._prev_time = now

        return {
            "upload":       up,
            "download":     dn,
            "bytes_sent":   curr.bytes_sent,
            "bytes_recv":   curr.bytes_recv,
            "interfaces":   self._active_ifaces(),
        }

    @staticmethod
    def _active_ifaces() -> List[str]:
        try:
            stats = psutil.net_if_stats()
            return [
                name for name, st in stats.items()
                if st.isup and name != "lo"
            ]
        except Exception:
            return []
