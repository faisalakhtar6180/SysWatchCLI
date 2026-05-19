

import os
import signal
import psutil
import threading
from typing import List

import syswatch.settings as cfg


class ProcessMonitor:
    SORT_KEYS = ["cpu_percent", "memory_percent", "pid", "name"]

    def __init__(self):
        self._lock     = threading.Lock()
        self._sort_key = "cpu_percent"
        self._filter   = ""
        # Prime cpu_percent (first call is always 0)
        for p in psutil.process_iter(["cpu_percent"]):
            try:
                p.cpu_percent(interval=None)
            except Exception:
                pass

    def snapshot(self, limit: int = cfg.MAX_PROCS) -> dict:
        with self._lock:
            sort_key = self._sort_key
            flt      = self._filter

        procs = self._collect(flt)
        procs = self._sort(procs, sort_key)
        return {
            "processes": procs[:limit],
            "total":     len(procs),
            "sort_key":  sort_key,
            "filter":    flt,
        }

    def cycle_sort(self):
        with self._lock:
            idx = self.SORT_KEYS.index(self._sort_key)
            self._sort_key = self.SORT_KEYS[(idx + 1) % len(self.SORT_KEYS)]

    def set_filter(self, text: str):
        with self._lock:
            self._filter = text.strip()

    def kill(self, pid: int) -> str:
        try:
            os.kill(pid, signal.SIGTERM)
            return f"[green]SIGTERM → PID {pid}[/green]"
        except ProcessLookupError:
            return f"[yellow]PID {pid} not found[/yellow]"
        except PermissionError:
            return f"[red]Permission denied (PID {pid})[/red]"
        except Exception as e:
            return f"[red]{e}[/red]"

    @staticmethod
    def _collect(flt: str) -> List[dict]:
        procs = []
        attrs = ["pid", "name", "cpu_percent", "memory_percent"]
        for p in psutil.process_iter(attrs):
            try:
                info = p.info
                name = (info["name"] or "")
                if flt and flt.lower() not in name.lower():
                    continue
                procs.append({
                    "pid":  info["pid"],
                    "name": name[:18],
                    "cpu":  round(info["cpu_percent"] or 0, 1),
                    "mem":  round(info["memory_percent"] or 0, 2),
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied,
                    psutil.ZombieProcess):
                pass
        return procs

    @staticmethod
    def _sort(procs: List[dict], key: str) -> List[dict]:
        map_ = {"cpu_percent": "cpu", "memory_percent": "mem",
                "pid": "pid", "name": "name"}
        k    = map_.get(key, "cpu")
        rev  = key in ("cpu_percent", "memory_percent")
        try:
            return sorted(procs, key=lambda p: p.get(k, 0), reverse=rev)
        except TypeError:
            return procs
