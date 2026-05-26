"""多频率 Tick 调度器 — fast、mid、slow，间隔从 config 读取。"""

import logging
from datetime import datetime
from PySide6.QtCore import QObject, QTimer, Signal
from config import config

logger = logging.getLogger(__name__)


class Scheduler(QObject):
    """基于 QTimer 的多频率调度器。"""

    fast_tick = Signal()
    mid_tick  = Signal()
    slow_tick = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._timers: dict[str, QTimer] = {}
        logger.info("[Scheduler] Created")

    def start(self, fast_ms: int | None = None, mid_ms: int | None = None,
              slow_ms: int | None = None):
        fast_ms = fast_ms if fast_ms is not None else config.SCHEDULER_FAST_MS
        mid_ms = mid_ms if mid_ms is not None else config.SCHEDULER_MID_MS
        slow_ms = slow_ms if slow_ms is not None else config.SCHEDULER_SLOW_MS
        self.stop()
        ts = datetime.now().strftime("%H:%M:%S")
        logger.info(f"[{ts}] [Scheduler] start(fast={fast_ms}ms, mid={mid_ms}ms, slow={slow_ms}ms)")

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

        logger.info(f"[{ts}] [Scheduler] Total {len(self._timers)} timer(s) running")

    def stop(self):
        if not self._timers:
            return
        ts = datetime.now().strftime("%H:%M:%S")
        names = list(self._timers.keys())
        for t in self._timers.values():
            t.stop()
            t.deleteLater()
        self._timers.clear()
        logger.info(f"[{ts}] [Scheduler] stop() — stopped {names}")

    def is_running(self) -> bool:
        return bool(self._timers)
