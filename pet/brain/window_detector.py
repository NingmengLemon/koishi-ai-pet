"""窗口枚举 — 根据平台分发到 Win32 或 Quartz 后端，对外接口统一。"""

import sys

if sys.platform == "darwin":
    from pet.brain.mac_detector import (       # noqa: F401
        MIN_WINDOW_SIZE,
        OCCLUSION_THRESHOLD,
        is_window_alive,
        get_window_rect,
        is_window_occluded,
        get_visible_windows,
    )
else:
    from pet.brain.win_detector import (       # noqa: F401
        MIN_WINDOW_SIZE,
        OCCLUSION_THRESHOLD,
        is_window_alive,
        get_window_rect,
        is_window_occluded,
        get_visible_windows,
    )
