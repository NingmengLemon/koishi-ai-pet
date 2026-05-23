"""Win32 窗口枚举 —— 桌宠固有能力，用于检测可站立的窗口。"""

import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32

GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000
MIN_WINDOW_SIZE = 50


def is_window_alive(hwnd: int) -> bool:
    """O(1) 检查窗口句柄是否仍然有效。"""
    return bool(user32.IsWindow(hwnd))


def get_window_rect(hwnd: int) -> tuple[int, int, int, int] | None:
    """O(1) 获取单个窗口的屏幕矩形，不可见或失败返回 None。"""
    if not user32.IsWindowVisible(hwnd):
        return None
    rect = wintypes.RECT()
    if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return (rect.left, rect.top, rect.right, rect.bottom)
    return None


def get_visible_windows() -> list[dict]:
    """返回所有可见顶层窗口，过滤掉工具窗口和极小窗口。"""
    windows = []

    def callback(hwnd, _):
        try:
            if not user32.IsWindowVisible(hwnd):
                return True

            ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            if (ex_style & WS_EX_TOOLWINDOW) and not (ex_style & WS_EX_APPWINDOW):
                return True

            rect = wintypes.RECT()
            if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                return True

            w = rect.right - rect.left
            h = rect.bottom - rect.top
            if w < MIN_WINDOW_SIZE or h < MIN_WINDOW_SIZE:
                return True

            title = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, title, 256)

            windows.append({
                "hwnd": hwnd,
                "title": title.value or "",
                "rect": (rect.left, rect.top, rect.right, rect.bottom),
            })
        except Exception:
            pass
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows(WNDENUMPROC(callback), 0)
    return windows
