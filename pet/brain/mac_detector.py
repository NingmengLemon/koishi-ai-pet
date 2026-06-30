"""macOS 窗口枚举 —— 基于 Quartz CGWindow API，与 Win32 版保持相同接口。"""

import Quartz
from AppKit import NSScreen

MIN_WINDOW_SIZE = 50
OCCLUSION_THRESHOLD = 0.8


def _screen_for_point(x: float, y: float) -> NSScreen:
    """返回包含指定 CG 坐标点的 NSScreen（CG 坐标系，左下原点）。"""
    for screen in NSScreen.screens():
        frame = screen.frame()
        cg_bottom = frame.origin.y
        cg_top = frame.origin.y + frame.size.height
        cg_left = frame.origin.x
        cg_right = frame.origin.x + frame.size.width
        if cg_left <= x < cg_right and cg_bottom <= y < cg_top:
            return screen
    return NSScreen.mainScreen()


def _flip_y(y: float, h: float, screen_height: float | None = None) -> int:
    """CG 坐标系 (左下原点) → Qt 坐标系 (左上原点)。"""
    if screen_height is None:
        screen_height = NSScreen.mainScreen().frame().size.height
    return int(screen_height - y - h)


def _windows_above(target_id: int) -> list[dict]:
    """返回 Z 序在 target_id 之上的所有窗口。"""
    window_list = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly
        | Quartz.kCGWindowListOptionOnScreenAboveWindow,
        target_id,
    )
    return window_list or []


def _all_windows() -> list[dict]:
    """返回屏幕上所有窗口 (排除桌面元素)。"""
    window_list = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly
        | Quartz.kCGWindowListExcludeDesktopElements,
        Quartz.kCGNullWindowID,
    )
    return window_list or []


def _find_window(window_id: int) -> dict | None:
    """按 windowID 查找单个窗口。"""
    window_list = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly
        | Quartz.kCGWindowListOptionIncludingWindow,
        window_id,
    )
    if window_list:
        return window_list[0]
    return None


def _bounds_to_rect(
    bounds: dict, screen_height: float | None = None
) -> tuple[int, int, int, int]:
    """CG bounds → (left, top, right, bottom) 屏幕坐标。"""
    x = int(bounds.get("X", 0))
    y = int(bounds.get("Y", 0))
    w = int(bounds.get("Width", 0))
    h = int(bounds.get("Height", 0))
    top = _flip_y(y, h, screen_height)
    return (x, top, x + w, top + h)


def is_window_alive(window_id: int) -> bool:
    return _find_window(window_id) is not None


def get_window_rect(window_id: int) -> tuple[int, int, int, int] | None:
    win = _find_window(window_id)
    if win is None:
        return None
    return _bounds_to_rect(win.get("kCGWindowBounds", {}))


def _compute_occluded_area(
    target_rect: tuple[int, int, int, int],
    above_rects: list[tuple[int, int, int, int]],
) -> int:
    """坐标压缩网格扫描法：计算遮挡矩形的精确并集面积。"""
    if not above_rects:
        return 0

    clipped = []
    for r in above_rects:
        cx1 = max(target_rect[0], r[0])
        cy1 = max(target_rect[1], r[1])
        cx2 = min(target_rect[2], r[2])
        cy2 = min(target_rect[3], r[3])
        if cx1 < cx2 and cy1 < cy2:
            clipped.append((cx1, cy1, cx2, cy2))
    if not clipped:
        return 0

    xs: set[int] = set()
    ys: set[int] = set()
    for r in clipped:
        xs.add(r[0])
        xs.add(r[2])
        ys.add(r[1])
        ys.add(r[3])
    xs_sorted = sorted(xs)
    ys_sorted = sorted(ys)

    x_idx = {v: i for i, v in enumerate(xs_sorted)}
    y_idx = {v: i for i, v in enumerate(ys_sorted)}

    grid = [[False] * (len(ys_sorted) - 1) for _ in range(len(xs_sorted) - 1)]
    for r in clipped:
        for i in range(x_idx[r[0]], x_idx[r[2]]):
            for j in range(y_idx[r[1]], y_idx[r[3]]):
                grid[i][j] = True

    area = 0
    for i in range(len(xs_sorted) - 1):
        for j in range(len(ys_sorted) - 1):
            if grid[i][j]:
                area += (xs_sorted[i + 1] - xs_sorted[i]) * (
                    ys_sorted[j + 1] - ys_sorted[j]
                )
    return area


def is_window_occluded(
    window_id: int,
    threshold: float = OCCLUSION_THRESHOLD,
    skip_hwnd: int = 0,
) -> bool:
    win = _find_window(window_id)
    if win is None:
        return True

    bounds = win.get("kCGWindowBounds", {})
    rect = _bounds_to_rect(bounds)
    area = (rect[2] - rect[0]) * (rect[3] - rect[1])
    if area <= 0:
        return True

    above_rects = []
    for above_win in _windows_above(window_id):
        if above_win["kCGWindowNumber"] == skip_hwnd:
            continue
        alpha = above_win.get("kCGWindowAlpha", 1.0)
        if alpha < 1.0:
            continue
        above_bounds = above_win.get("kCGWindowBounds", {})
        above_rect = _bounds_to_rect(above_bounds)
        if (above_rect[2] - above_rect[0]) > 0 and (above_rect[3] - above_rect[1]) > 0:
            above_rects.append(above_rect)

    covered = _compute_occluded_area(rect, above_rects)
    return covered / area > threshold


def get_visible_windows() -> list[dict]:
    """返回所有可见窗口列表。"""
    screen_height = NSScreen.mainScreen().frame().size.height
    windows = []
    for win in _all_windows():
        bounds = win.get("kCGWindowBounds", {})
        w = int(bounds.get("Width", 0))
        h = int(bounds.get("Height", 0))
        if w < MIN_WINDOW_SIZE or h < MIN_WINDOW_SIZE:
            continue
        name = win.get("kCGWindowName", "") or win.get("kCGWindowOwnerName", "")
        window_id = win["kCGWindowNumber"]
        rect = _bounds_to_rect(bounds, screen_height)
        windows.append(
            {
                "hwnd": window_id,
                "title": name,
                "rect": rect,
            }
        )
    return windows
