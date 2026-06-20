"""INFO 级日志查看器 —— 托盘右键打开，扁平化圆角风格。"""

import logging
from collections import deque
from datetime import datetime

from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QLabel,
)


class _LogRelay(QObject):
    """跨线程日志桥接器 — 接收 LogWindowHandler 的 Signal 并交付给 LogWindow。"""

    log_received = Signal(str)

    def __init__(self, buffer_size: int = 2000, parent=None):
        super().__init__(parent)
        self._widget: QWidget | None = None
        self._buffer: deque[str] = deque(maxlen=buffer_size)
        self.log_received.connect(self._on_log_received)

    def set_widget(self, widget: QWidget):
        self._widget = widget
        # 渲入启动期缓存的日志
        while self._buffer:
            widget._append_log(self._buffer.popleft())

    def _on_log_received(self, formatted: str):
        if self._widget:
            self._widget._append_log(formatted)
        else:
            self._buffer.append(formatted)


class LogWindowHandler(logging.Handler):
    """自定义 logging.Handler — 仅 INFO 及以上，格式化后经由 _LogRelay 进入 GUI。"""

    def __init__(self, relay: _LogRelay, level=logging.INFO):
        super().__init__(level=level)
        self._relay = relay
        self.setFormatter(logging.Formatter(
            "[%(asctime)s] [%(levelname)-5s] [%(name)s] %(message)s",
            datefmt="%H:%M:%S",
        ))

    def emit(self, record: logging.LogRecord):
        try:
            self._relay.log_received.emit(self.format(record))
        except Exception:
            self.handleError(record)


_WINDOW_QSS = """
QWidget#LogWindowRoot {
    background: #f0f0f0;
}
"""

_TEXTEDIT_QSS = """
QTextEdit {
    background: #ffffff;
    border: 1px solid #ddd;
    border-radius: 10px;
    padding: 6px 8px;
    font-family: "Consolas", "Microsoft YaHei", monospace;
    font-size: 12px;
    color: #333;
    selection-background-color: #b3d9ff;
}
QTextEdit:focus {
    border-color: #aaa;
}
"""

_CLEAR_BTN_QSS = """
QPushButton {
    background: transparent;
    border: 1px solid #ccc;
    border-radius: 12px;
    padding: 2px 14px;
    font-size: 12px;
    color: #555;
}
QPushButton:hover {
    background: #e0e0e0;
    border-color: #aaa;
}
"""

_MAX_BLOCK_COUNT = 5000


class LogWindow(QWidget):
    """INFO 日志查看窗口。"""

    def __init__(self, relay: _LogRelay, parent=None):
        super().__init__(parent)
        self.setWindowTitle("DeskPet 日志")
        self.setObjectName("LogWindowRoot")
        self.setMinimumSize(520, 350)
        self.resize(600, 420)
        self.setStyleSheet(_WINDOW_QSS)

        # ── 工具栏 ──
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)

        level_label = QLabel("INFO+")
        level_label.setStyleSheet("font-size:13px; color:#666; font-weight:bold;")
        toolbar.addWidget(level_label)

        toolbar.addStretch()

        clear_btn = QPushButton("清空")
        clear_btn.setStyleSheet(_CLEAR_BTN_QSS)
        clear_btn.clicked.connect(self._clear)
        toolbar.addWidget(clear_btn)

        # ── 日志正文 ──
        self._log_view = QTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setFont(QFont("Consolas", 10))
        self._log_view.setStyleSheet(_TEXTEDIT_QSS)

        # ── 组装 ──
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)
        root.addLayout(toolbar)
        root.addWidget(self._log_view)

        # 绑定 relay
        relay.set_widget(self)

    # ── 公开 ──

    def _append_log(self, formatted: str):
        """由 _LogRelay 调用（主线程安全）。"""
        self._log_view.append(formatted)
        self._trim_if_needed()

    def _clear(self):
        self._log_view.clear()

    # ── 内部 ──

    def _trim_if_needed(self):
        doc = self._log_view.document()
        if doc.blockCount() <= _MAX_BLOCK_COUNT:
            return
        excess = doc.blockCount() - _MAX_BLOCK_COUNT
        cursor = QTextCursor(doc.firstBlock())
        for _ in range(excess):
            cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()  # 删除换行符

    def closeEvent(self, event):
        """关闭即隐藏，保留日志历史。"""
        self.hide()
        event.ignore()
