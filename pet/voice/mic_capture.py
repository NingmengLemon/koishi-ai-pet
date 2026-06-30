"""麦克风 PCM 采集模块"""

import logging
from collections import deque
from threading import Lock

import numpy as np
import sounddevice as sd
from PySide6.QtCore import QObject, QTimer, Signal

logger = logging.getLogger(__name__)

# 讯飞要求: PCM 16kHz, 16bit, mono
SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "int16"
FRAME_SAMPLES = 4000  # 每帧采样数，对应约 0.25s
FRAME_BYTES = FRAME_SAMPLES * 2  # 16bit = 2 bytes/sample → 8000 bytes/帧


class MicCapture(QObject):
    """麦克风采集，输出 16kHz 16bit mono PCM 数据流。

    使用无锁环形缓冲 (deque) 解耦音频回调与 Qt 信号发射：
    - 回调线程只做轻量 append
    - 主线程 QTimer 周期性 drain deque 并 emit
    """

    audio_chunk = Signal(bytes)  # 每帧 PCM 数据
    started = Signal()
    stopped = Signal()
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stream: sd.InputStream | None = None
        self._running = False
        self._buffer: deque[bytes] = deque()
        self._buffer_lock = Lock()

        # 主线程定时器：每 50ms 检查缓冲并发射信号
        self._flush_timer = QTimer(self)
        self._flush_timer.setInterval(50)
        self._flush_timer.timeout.connect(self._flush_buffer)

    def start(self):
        """打开麦克风，启动采集。"""
        if self._running:
            return
        try:
            stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype=DTYPE,
                blocksize=FRAME_SAMPLES,
                callback=self._on_audio,
            )
            stream.start()
        except Exception as e:
            logger.error(f"[MicCapture] start failed: {e}")
            self.error_occurred.emit(str(e))
            return

        self._stream = stream
        self._running = True
        self._flush_timer.start()
        self.started.emit()
        logger.info("[MicCapture] started")

    def stop(self):
        """停止采集，关闭麦克风。"""
        if not self._running:
            return
        self._flush_timer.stop()
        self._running = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        self.stopped.emit()
        logger.info("[MicCapture] stopped")

    def _on_audio(self, indata: np.ndarray, frames: int, _time, _status):
        """sounddevice 回调：轻量写入环形缓冲。

        在实时音频回调中禁止 emit Qt 信号（会导致 xrun）。
        """
        try:
            if _status:
                logger.warning(f"[MicCapture] stream status: {_status}")
            if not self._running:
                return
            data = indata.tobytes()  # int16 → bytes
            with self._buffer_lock:
                self._buffer.append(data)
        except Exception as e:
            logger.error(f"[MicCapture] _on_audio error: {e}")

    def _flush_buffer(self):
        """主线程：取出缓冲中的数据并发射信号。"""
        if not self._running:
            return
        chunks = []
        with self._buffer_lock:
            while self._buffer:
                chunks.append(self._buffer.popleft())
        for chunk in chunks:
            self.audio_chunk.emit(chunk)

    def __del__(self):
        self.stop()

    @property
    def is_running(self) -> bool:
        return self._running
