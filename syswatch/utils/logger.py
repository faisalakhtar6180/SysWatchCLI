
import logging
import logging.handlers
import os

import syswatch.settings as cfg


def setup_logger(name: str = "syswatch") -> logging.Logger:
    os.makedirs(cfg.LOG_DIR, exist_ok=True)
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fh = logging.handlers.RotatingFileHandler(
        cfg.LOG_FILE, maxBytes=2 * 1024 * 1024, backupCount=2, encoding="utf-8"
    )
    fh.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(fh)
    return logger


def log_metrics(logger: logging.Logger,
                cpu: dict, mem: dict, disk: dict, net: dict) -> None:
    logger.info(
        "CPU=%.1f%%  RAM=%.1f%%  DISK=%.1f%%  UP=%s  DN=%s",
        cpu.get("total", 0),
        mem.get("percent", 0),
        disk.get("root", {}).get("percent", 0),
        _bps(net.get("upload", 0)),
        _bps(net.get("download", 0)),
    )


def _bps(n: float) -> str:
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f}{u}/s"
        n /= 1024
    return f"{n:.1f}GB/s"
