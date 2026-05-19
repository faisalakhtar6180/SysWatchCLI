
import contextlib
import select
import sys
import termios
import time
import threading
import tty

from rich.console import Console
from rich.live    import Live
from rich.panel   import Panel
from rich.prompt  import Prompt
from rich.text    import Text
import readchar

from syswatch.monitor import (CPUMonitor, MemoryMonitor, DiskMonitor,
                               NetworkMonitor, ProcessMonitor, SystemInfo)
from syswatch.utils   import (fmt_bytes, fmt_speed, pct_bar, pct_color,
                               AlertManager, setup_logger, log_metrics)
import syswatch.settings as cfg

console = Console()

# ── Help text ─────────────────────────────────────────────────────────────────
_HELP = """\
[bold cyan]SysWatch — Keyboard Shortcuts[/bold cyan]

[bold yellow]q[/bold yellow]  Quit
[bold yellow]r[/bold yellow]  Force refresh
[bold yellow]s[/bold yellow]  Cycle sort order  (CPU → RAM → PID → Name)
[bold yellow]f[/bold yellow]  Filter process list  (blank to clear)
[bold yellow]k[/bold yellow]  Kill process by PID
[bold yellow]c[/bold yellow]  Clear alert messages
[bold yellow]h[/bold yellow]  Show this help

[dim]Press any key to return…[/dim]
"""

_W = 56   # inner content width for dividers


class _TerminalInput:
    """Small nonblocking stdin helper for Linux terminals."""

    def __init__(self):
        self._fd = None
        self._old_settings = None
        self._enabled = False

    def start(self):
        if self._enabled or not sys.stdin.isatty():
            return
        self._fd = sys.stdin.fileno()
        self._old_settings = termios.tcgetattr(self._fd)
        tty.setcbreak(self._fd)
        self._enabled = True

    def stop(self):
        if not self._enabled:
            return
        termios.tcsetattr(self._fd, termios.TCSADRAIN, self._old_settings)
        self._enabled = False

    def read_key(self, timeout: float = 0.05):
        if not sys.stdin.isatty():
            time.sleep(timeout)
            return None
        readable, _, _ = select.select([sys.stdin], [], [], timeout)
        if not readable:
            return None
        return sys.stdin.read(1)

    @contextlib.contextmanager
    def paused(self):
        self.stop()
        try:
            yield
        finally:
            self.start()


# ── Tiny text builders ────────────────────────────────────────────────────────

def _div() -> Text:
    return Text(" " + "─" * _W + "\n", style="dim")


def _metric_row(label: str, pct: float,
                detail: str = "", warn_pct: float = 100.0) -> Text:
    """One CPU/RAM/DISK row."""
    colour = pct_color(pct)
    t = Text()
    t.append(f"  {label:<5} ", style="bold")
    t.append(pct_bar(pct, 22), style=colour)
    t.append(f"  {pct:5.1f}%", style=f"bold {colour}")
    if detail:
        t.append(f"   {detail}", style="dim")
    if pct >= warn_pct:
        t.append("  ⚠", style="bold red")
    t.append("\n")
    return t


# ── Main dashboard class ──────────────────────────────────────────────────────

class SysWatchDashboard:
    """
    Orchestrates monitors, Rich Live display, and keyboard input.
    Call .run() to start; press q to exit.
    """

    def __init__(self):
        self.cpu_m  = CPUMonitor()
        self.mem_m  = MemoryMonitor()
        self.disk_m = DiskMonitor()
        self.net_m  = NetworkMonitor()
        self.proc_m = ProcessMonitor()
        self.sys_i  = SystemInfo()
        self.alerts = AlertManager()
        self.logger = setup_logger()

        self._running  = True
        self._status   = ""
        self._last_log = 0.0
        self._snap     = {}
        self._lock     = threading.Lock()
        self._collect_lock = threading.Lock()

    # ── Entry ─────────────────────────────────────────────────────────────────

    def run(self):
        collector = threading.Thread(target=self._collect, daemon=True)
        collector.start()
        time.sleep(0.35)   # let first snapshot land

        with Live(self._render(), console=console,
                  refresh_per_second=2, screen=True) as live:
            self._handle_keys(live)

    # ── Background collection ─────────────────────────────────────────────────

    def _collect(self):
        while self._running:
            self._collect_once()
            time.sleep(cfg.REFRESH_INTERVAL)

    def _collect_once(self) -> bool:
        try:
            with self._collect_lock:
                cpu  = self.cpu_m.snapshot()
                mem  = self.mem_m.snapshot()
                disk = self.disk_m.snapshot()
                net  = self.net_m.snapshot()
                proc = self.proc_m.snapshot()
                sys_ = self.sys_i.snapshot()

                self.alerts.evaluate(cpu, mem, disk, net)

                with self._lock:
                    self._snap = {
                        "cpu": cpu, "mem": mem, "disk": disk,
                        "net": net, "proc": proc, "sys": sys_,
                    }

                now = time.monotonic()
                if now - self._last_log >= cfg.LOG_INTERVAL:
                    log_metrics(self.logger, cpu, mem, disk, net)
                    self._last_log = now
            return True
        except Exception as e:
            self.logger.exception("Collect error: %s", e)
            return False

    # ── Key input ─────────────────────────────────────────────────────────────

    def _handle_keys(self, live: Live):
        keys = _TerminalInput()
        keys.start()
        last_render = 0.0
        render_interval = 0.5
        try:
            while self._running:
                try:
                    key = keys.read_key(0.05)
                except Exception:
                    key = None

                if key:
                    self._handle_key(key, live, keys)
                    live.update(self._render())
                    last_render = time.monotonic()
                    continue

                now = time.monotonic()
                if now - last_render >= render_interval:
                    live.update(self._render())
                    last_render = now
        finally:
            keys.stop()

    def _handle_key(self, key: str, live: Live, keys: _TerminalInput):
        if key in ("q", "Q"):
            self._running = False

        elif key in ("r", "R"):
            self._status = "Refreshed" if self._collect_once() else "Refresh failed"

        elif key in ("s", "S"):
            self.proc_m.cycle_sort()
            self._status = "Sort changed"

        elif key in ("c", "C"):
            self.alerts.clear()
            self._status = "Alerts cleared"

        elif key in ("k", "K"):
            with keys.paused():
                try:
                    live.stop()
                    pid = int(Prompt.ask("Kill PID"))
                    self._status = self.proc_m.kill(pid)
                except ValueError:
                    self._status = "[red]Invalid PID[/red]"
                finally:
                    live.start()

        elif key in ("f", "F"):
            with keys.paused():
                try:
                    live.stop()
                    flt = Prompt.ask("Filter process (blank=clear)")
                    self.proc_m.set_filter(flt)
                    self._status = f"Filter: '{flt}'" if flt else "Filter cleared"
                finally:
                    live.start()

        elif key in ("h", "H"):
            with keys.paused():
                try:
                    live.stop()
                    console.print(Panel(Text.from_markup(_HELP),
                                        border_style="cyan", expand=False))
                    readchar.readkey()
                except Exception:
                    pass
                finally:
                    live.start()

    # ── Render ────────────────────────────────────────────────────────────────

    def _render(self):
        with self._lock:
            snap = dict(self._snap)

        if not snap:
            return Panel(Text("  Starting…", style="dim"),
                         border_style="bright_blue")

        cpu  = snap["cpu"]
        mem  = snap["mem"]
        disk = snap["disk"]
        net  = snap["net"]
        proc = snap["proc"]
        sys_ = snap["sys"]
        alerts = self.alerts.get_alerts()

        body = Text()

        # ── Header ────────────────────────────────────────────────────────────
        ts = time.strftime("%H:%M:%S")
        body.append(f"  {sys_['hostname']}", style="bold cyan")
        body.append(f"  up {sys_['uptime']}", style="dim")
        body.append(f"  {sys_['user']}", style="green")
        body.append(f"  {sys_['local_ip']}", style="dim")
        body.append(f"  {ts}", style="dim")
        if self._status:
            body.append(f"   ·  {self._status}", style="yellow")
            self._status = ""
        body.append("\n")
        body.append_text(_div())

        # ── CPU ───────────────────────────────────────────────────────────────
        c     = cpu["total"]
        c_det = ""
        if cpu.get("temp"):
            c_det += f"{cpu['temp']}°C  "
        c_det += f"{cpu['cores_logical']}c"
        if cpu.get("freq_mhz"):
            c_det += f"  {cpu['freq_mhz']} MHz"
        body.append_text(_metric_row("CPU", c, c_det, cfg.CPU_WARN))

        # ── RAM ───────────────────────────────────────────────────────────────
        r     = mem["percent"]
        r_det = f"{fmt_bytes(mem['used'])} / {fmt_bytes(mem['total'])}"
        body.append_text(_metric_row("RAM", r, r_det, cfg.RAM_WARN))

        # ── DISK ──────────────────────────────────────────────────────────────
        d     = disk["root"].get("percent", 0)
        d_det = (f"{fmt_bytes(disk['root'].get('used',0))} / "
                 f"{fmt_bytes(disk['root'].get('total',0))}")
        body.append_text(_metric_row("DISK", d, d_det, cfg.DISK_WARN))

        # ── NET ───────────────────────────────────────────────────────────────
        iface = net["interfaces"][0] if net.get("interfaces") else "—"
        body.append("  NET   ", style="bold")
        body.append(f"↓ {fmt_speed(net['download'])}", style="cyan")
        body.append("   ", style="")
        body.append(f"↑ {fmt_speed(net['upload'])}", style="green")
        body.append(f"   {iface}", style="dim")
        body.append("\n")
        body.append_text(_div())

        # ── Process table ─────────────────────────────────────────────────────
        sort_lbl = (proc["sort_key"]
                    .replace("_percent", "").replace("_", ""))
        flt_lbl  = f"  filter:'{proc['filter']}'" if proc["filter"] else ""
        body.append(
            f"  PROCS  {proc['total']} total · sort:{sort_lbl}"
            f"{flt_lbl}",
            style="dim",
        )
        body.append("   [s]ort [f]ilter [k]ill\n", style="dim")

        # Column header
        body.append(f"  {'PID':>6}  {'NAME':<18}  {'CPU%':>5}  {'RAM%':>5}\n",
                    style="bold dim")

        for p in proc["processes"]:
            cpu_c = pct_color(p["cpu"], 30, 70)
            mem_c = pct_color(p["mem"],  5, 15)
            body.append(f"  {p['pid']:>6}  {p['name']:<18}  ",
                        style="dim")
            body.append(f"{p['cpu']:>5.1f}", style=f"bold {cpu_c}")
            body.append("  ")
            body.append(f"{p['mem']:>5.2f}", style=f"bold {mem_c}")
            body.append("\n")

        # ── Alerts ────────────────────────────────────────────────────────────
        if alerts:
            body.append_text(_div())
            for a in alerts[:4]:
                body.append("  ")
                body.append_text(Text.from_markup(a))
                body.append("\n")

        # ── Footer ────────────────────────────────────────────────────────────
        body.append_text(_div())
        body.append(
            "  [q]uit  [r]efresh  [s]ort  [f]ilter  "
            "[k]ill  [c]lear  [h]elp",
            style="dim",
        )

        return Panel(
            body,
            title=f"[bold cyan] SysWatch {cfg.APP_VERSION} [/bold cyan]",
            border_style="bright_blue",
            padding=(0, 0),
        )
