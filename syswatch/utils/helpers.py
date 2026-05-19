

def fmt_bytes(n: float) -> str:
    """Human-readable byte count: 1.2 MB"""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024.0:
            return f"{n:6.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} PB"


def fmt_speed(n: float) -> str:
    """Human-readable bytes/sec speed."""
    return fmt_bytes(n) + "/s"


def pct_bar(pct: float, width: int = 20) -> str:
    """Simple unicode block progress bar."""
    filled = max(0, min(width, int(pct / 100 * width)))
    return "█" * filled + "░" * (width - filled)


def pct_color(pct: float, warn: float = 70.0, danger: float = 90.0) -> str:
    """Return a Rich colour name based on percentage."""
    if pct >= danger:
        return "bright_red"
    if pct >= warn:
        return "yellow"
    return "bright_green"
