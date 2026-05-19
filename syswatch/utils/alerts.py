"""
utils/alerts.py — Threshold-based alert manager.
"""

import time
import threading
from collections import deque
from typing import List

import syswatch.settings as cfg


class AlertManager:
    MAX   = 6
    DELAY = 15.0   # seconds before same alert can repeat

    def __init__(self):
        self._lock  = threading.Lock()
        self._msgs: deque = deque(maxlen=self.MAX)
        self._seen: dict  = {}

    def evaluate(self, cpu: dict, mem: dict, disk: dict, net: dict) -> None:
        now = time.monotonic()
        checks = [
            ("cpu",  cpu.get("total", 0)              >= cfg.CPU_WARN,
             f"[bold red]⚠ CPU[/bold red]  {cpu.get('total',0):.1f}% ≥ {cfg.CPU_WARN}%"),
            ("ram",  mem.get("percent", 0)             >= cfg.RAM_WARN,
             f"[bold red]⚠ RAM[/bold red]  {mem.get('percent',0):.1f}% ≥ {cfg.RAM_WARN}%"),
            ("disk", disk.get("root", {}).get("percent", 0) >= cfg.DISK_WARN,
             f"[yellow]⚠ DISK[/yellow] {disk.get('root',{}).get('percent',0):.1f}% ≥ {cfg.DISK_WARN}%"),
            ("net",  (net.get("upload", 0) >= cfg.NET_SPIKE or
                      net.get("download", 0) >= cfg.NET_SPIKE),
             f"[yellow]⚠ NET[/yellow]  bandwidth spike"),
        ]
        with self._lock:
            for key, triggered, msg in checks:
                if triggered and now - self._seen.get(key, 0) >= self.DELAY:
                    ts = time.strftime("%H:%M:%S")
                    self._msgs.appendleft(f"[dim]{ts}[/dim]  {msg}")
                    self._seen[key] = now

    def get_alerts(self) -> List[str]:
        with self._lock:
            return list(self._msgs)

    def clear(self) -> None:
        with self._lock:
            self._msgs.clear()
            self._seen.clear()
