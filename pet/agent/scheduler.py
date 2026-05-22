"""多频率 Tick 调度器 — fast (1s)、mid (30s)、slow (5min)。"""

from datetime import datetime
from PySide6.QtCore import QObject, QTimer, Signal


class Scheduler(QObject):
    """基于 QTimer 的多频率调度器。"""

    fast_tick = Signal()
    mid_tick  = Signal()
    slow_tick = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._timers: dict[str, QTimer] = {}
        print(f"[Scheduler] Created")

    def start(self, fast_ms: int = 1000, mid_ms: int = 30000,
              slow_ms: int = 300000):
        self.stop()
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] [Scheduler] start(fast={fast_ms}ms, mid={mid_ms}ms, slow={slow_ms}ms)")

        if fast_ms > 0:
            t = QTimer(self)
            t.setInterval(fast_ms)
            t.timeout.connect(self.fast_tick)
            t.start()
            self._timers["fast"] = t

        if mid_ms > 0:
            t = QTimer(self)
            t.setInterval(mid_ms)
            t.timeout.connect(self.mid_tick)
            t.start()
            self._timers["mid"] = t

        if slow_ms > 0:
            t = QTimer(self)
            t.setInterval(slow_ms)
            t.timeout.connect(self.slow_tick)
            t.start()
            self._timers["slow"] = t

        print(f"[{ts}] [Scheduler] Total {len(self._timers)} timer(s) running")

    def stop(self):
        if not self._timers:
            return
        ts = datetime.now().strftime("%H:%M:%S")
        names = list(self._timers.keys())
        for t in self._timers.values():
            t.stop()
            t.deleteLater()
        self._timers.clear()
        print(f"[{ts}] [Scheduler] stop() — stopped {names}")

    def is_running(self) -> bool:
        return bool(self._timers)
