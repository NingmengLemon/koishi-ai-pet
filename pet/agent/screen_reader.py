"""屏幕截图能力 —— 桌宠固有能力，供视觉 AI 分析。"""

import logging
from typing import Optional

from PIL import Image
import mss

logger = logging.getLogger(__name__)


class ScreenReader:
    def __init__(self):
        self._enabled = False
        self._sct: Optional[mss.mss] = None

    def enable(self):
        self._enabled = True
        logger.info("屏幕截图已启用")

    def disable(self):
        self._enabled = False
        logger.info("屏幕截图已禁用")

    def capture_fullscreen(self, all_screens: bool = False) -> Optional[Image.Image]:
        if not self._enabled:
            logger.warning("屏幕截图已禁用，无法截图")
            return None
        try:
            sct = self._get_sct()
            monitor_index = 0 if all_screens else 1
            monitor = sct.monitors[monitor_index]
            sct_img = sct.grab(monitor)
            return Image.frombytes(
                "RGB", sct_img.size, sct_img.bgra, "raw", "BGRX"
            )
        except Exception as e:
            logger.error(f"截图失败：{e}")
            return None

    def capture_area(self, x: int, y: int, width: int, height: int) -> Optional[Image.Image]:
        if not self._enabled:
            return None
        try:
            sct = self._get_sct()
            monitor = {"top": y, "left": x, "width": width, "height": height}
            sct_img = sct.grab(monitor)
            return Image.frombytes(
                "RGB", sct_img.size, sct_img.bgra, "raw", "BGRX"
            )
        except Exception as e:
            logger.error(f"区域截图失败：{e}")
            return None

    def _get_sct(self) -> mss.mss:
        """延迟初始化 mss 实例。"""
        if self._sct is None:
            self._sct = mss.mss()
        return self._sct
