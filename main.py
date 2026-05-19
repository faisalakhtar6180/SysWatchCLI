

import argparse
import importlib.util
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _check_deps():
    missing = [p for p in ("rich", "psutil", "readchar", "requests")
               if not importlib.util.find_spec(p)]
    if missing:
        print(f"[ERROR] Missing packages: {', '.join(missing)}")
        print("Fix:  pip install -r requirements.txt")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        prog="syswatch",
        description="SysWatch — Minimal Linux terminal monitor",
    )
    parser.add_argument(
        "--refresh", type=float, default=None, metavar="SECS",
        help="Refresh interval in seconds (default: 1.0)",
    )
    parser.add_argument("--version", action="version", version="SysWatch 1.0.0")
    args = parser.parse_args()

    _check_deps()

    if args.refresh is not None:
        import syswatch.settings as cfg
        cfg.REFRESH_INTERVAL = max(0.2, args.refresh)

    from syswatch.ui import SysWatchDashboard
    from rich.console import Console

    con = Console()
    con.clear()
    con.print("\n  [bold cyan]SysWatch[/bold cyan]  [dim]starting…[/dim]\n")

    try:
        SysWatchDashboard().run()
    except KeyboardInterrupt:
        pass
    finally:
        con.clear()
        con.print("\n  [bold cyan]SysWatch[/bold cyan]  Goodbye!\n")


if __name__ == "__main__":
    main()
