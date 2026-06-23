"""全局热键管理器，使用 pynput 监听按键。"""

import logging

from pynput import keyboard
from PySide6.QtCore import QObject, Signal

from config import config

logger = logging.getLogger(__name__)


class HotkeyManager(QObject):
    """全局热键监听。每次按下/释放切换录音。"""

    voice_toggle = Signal()
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._listener: keyboard.Listener | None = None
        self._hotkey = config.VOICE_HOTKEY.lower()
        self._key_down = False  # 防止按键连发导致高频翻转

    def start(self):
        """启动全局键盘监听线程。"""
        if self._listener and self._listener.running:
            return
        try:
            self._listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release,
            )
            self._listener.daemon = True
            self._listener.start()
            logger.info(f"[HotkeyManager] listening for '{self._hotkey}'")
        except Exception as e:
            logger.error(f"[HotkeyManager] failed to start listener: {e}")
            self.error_occurred.emit(str(e))

    def stop(self):
        """停止键盘监听。"""
        if self._listener and self._listener.running:
            self._listener.stop()
            self._listener = None
        self._key_down = False
        logger.info("[HotkeyManager] stopped")

    def _on_press(self, key):
        """仅在按键从未按下→按下的瞬间触发切换。"""
        if self._key_down:
            return  # 防止 auto-repeat 连发
        key_name = self._key_name(key)
        if key_name != self._hotkey:
            return
        self._key_down = True
        logger.info(f"[HotkeyManager] toggle: {self._hotkey}")
        self.voice_toggle.emit()

    def _on_release(self, key):
        key_name = self._key_name(key)
        if key_name != self._hotkey:
            return
        self._key_down = False

    @staticmethod
    def _key_name(key) -> str:
        try:
            return key.char.lower() if hasattr(key, 'char') and key.char else key.name.lower()
        except Exception:
            return ""
