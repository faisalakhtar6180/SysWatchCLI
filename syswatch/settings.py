"""
syswatch/settings.py — All tunable constants in one place.
"""

from pathlib import Path

APP_NAME       = "SysWatch"
APP_VERSION    = "1.0.0"

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR  = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "syswatch.log"

REFRESH_INTERVAL = 1.0   # seconds between UI updates
LOG_INTERVAL     = 30    # seconds between log file writes
MAX_PROCS        = 18    # max rows in process table

# Alert thresholds (percent)
CPU_WARN  = 85.0
RAM_WARN  = 80.0
DISK_WARN = 90.0
NET_SPIKE = 10 * 1024 * 1024   # 10 MB/s
