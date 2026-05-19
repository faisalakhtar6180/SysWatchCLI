
import psutil
import threading
from typing import Optional


class CPUMonitor:
    def __init__(self):
        # Prime psutil — first call always returns 0
        psutil.cpu_percent(interval=None)
        psutil.cpu_percent(percpu=True, interval=None)

    def snapshot(self) -> dict:
        freq = psutil.cpu_freq()
        return {
            "total":           psutil.cpu_percent(interval=None),
            "per_core":        psutil.cpu_percent(percpu=True, interval=None),
            "cores_logical":   psutil.cpu_count(logical=True),
            "cores_physical":  psutil.cpu_count(logical=False),
            "freq_mhz":        round(freq.current) if freq else None,
            "temp":            self._temp(),
        }

    @staticmethod
    def _temp() -> Optional[float]:
        try:
            temps = psutil.sensors_temperatures()
            if not temps:
                return None
            for key in ("coretemp", "k10temp", "cpu_thermal", "acpitz"):
                if key in temps and temps[key]:
                    return round(temps[key][0].current, 1)
            first = next(iter(temps.values()))
            return round(first[0].current, 1) if first else None
        except Exception:
            return None
