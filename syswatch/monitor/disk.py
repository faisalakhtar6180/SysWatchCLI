
import psutil
import time
from typing import List


class DiskMonitor:
    def __init__(self):
        self._prev_io = psutil.disk_io_counters()
        self._prev_time = time.monotonic()

    def snapshot(self) -> dict:
        parts = self._partitions()
        root  = next((p for p in parts if p["mount"] == "/"),
                     parts[0] if parts else {})
        read_spd, write_spd = self._io_delta()
        return {
            "partitions":  parts,
            "root":        root,
            "read_speed":  read_spd,
            "write_speed": write_spd,
        }

    @staticmethod
    def _partitions() -> List[dict]:
        result = []
        for p in psutil.disk_partitions(all=False):
            try:
                u = psutil.disk_usage(p.mountpoint)
                result.append({
                    "device": p.device,
                    "mount":  p.mountpoint,
                    "fstype": p.fstype,
                    "total":  u.total,
                    "used":   u.used,
                    "free":   u.free,
                    "percent": u.percent,
                })
            except PermissionError:
                pass
        return result

    def _io_delta(self):
        try:
            curr = psutil.disk_io_counters()
            now = time.monotonic()
            elapsed = max(now - self._prev_time, 0.001)
            if curr and self._prev_io:
                rd = max(curr.read_bytes  - self._prev_io.read_bytes,  0) / elapsed
                wr = max(curr.write_bytes - self._prev_io.write_bytes, 0) / elapsed
            else:
                rd = wr = 0
            self._prev_io = curr
            self._prev_time = now
            return rd, wr
        except Exception:
            return 0, 0
