"""桌宠动画模块 —— 帧序列播放 + 窗口动画，统一由 PetAnimator 管理。"""

import os
from PySide6.QtCore import Qt, QPoint, QTimer, QPropertyAnimation, QEasingCurve, QObject, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QWidget
from config import config
from pet.agent.window_detector import get_visible_windows, is_window_alive

_SUPPORTED_EXT = (".png", ".jpg", ".jpeg", ".bmp", ".webp")


class PetAnimator(QObject):
    """桌宠动画控制器"""

    animation_finished = Signal(str)  # 非循环播放完毕时发出

    def __init__(self, window: QWidget, label: QLabel, pet_dir: str | None = None, parent=None):
        super().__init__(parent)
        self._window = window
        self._label = label
        self._pet_dir = pet_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "assets", "actions",
        )

        self._frames: list[QPixmap] = []
        self._current_frame: int = 0
        self._current_action: str = ""
        self._loop: bool = True

        self._frame_timer = QTimer(self)
        self._frame_timer.timeout.connect(self._next_frame)

        self._cache: dict[str, list[QPixmap]] = {}
        self._win_anims: list[QPropertyAnimation] = []  # 防止被 GC

        self._gravity_timer = QTimer(self)
        self._gravity_timer.timeout.connect(self._gravity_tick)
        self._gravity_step = 5
        self._gravity_interval = 30
        self._gravity_enabled = True
        self._gravity_falling = False
        self._gravity_timer.start(self._gravity_interval)

        # 窗口检测节流
        self._scan_tick = 0
        self._cached_effective_bottom: int | None = None
        self._standing_hwnd: int = 0
        self._ALIVE_CHECK_INTERVAL = 15  # ~500ms 检查站立窗口是否存活
        self._SCAN_INTERVAL = 3           # ~90ms 全量扫描一次

    def play(self, action: str, loop: bool = True, fps: int | None = None) -> bool:
        """播放指定动作的帧动画。"""
        frames = self._load_action(action)
        if not frames:
            return False

        self._frame_timer.stop()
        self._frames = frames
        self._current_action = action
        self._current_frame = 0
        self._loop = loop

        self._label.setPixmap(self._frames[0])

        if len(self._frames) > 1:
            interval = self._calc_interval(loop, fps)
            self._frame_timer.start(interval)

        return True

    def _calc_interval(self, loop: bool, fps: int | None) -> int:
        base_fps = fps or config.PET_FPS
        raw_interval = round(1000 / base_fps)
        if loop and len(self._frames) < base_fps:
            return max(1, round(1000 / len(self._frames)))
        return max(1, raw_interval)

    def stop(self):
        """停止帧动画，画面保持在当前帧。"""
        self._frame_timer.stop()

    def has_frames(self, action: str) -> bool:
        """检查指定动作是否有可用帧。"""
        return len(self._load_action(action)) > 0

    def available_actions(self) -> list[str]:
        """返回 pet_dir 下所有有帧图片的动作名称。"""
        if not os.path.isdir(self._pet_dir):
            return []
        actions = []
        for name in sorted(os.listdir(self._pet_dir)):
            full = os.path.join(self._pet_dir, name)
            if os.path.isdir(full) and self.has_frames(name):
                actions.append(name)
        return actions

    @property
    def current_action(self) -> str:
        return self._current_action

    @property
    def is_playing(self) -> bool:
        return self._frame_timer.isActive()

    def _cleanup_stopped_anims(self):
        self._win_anims[:] = [
            a for a in self._win_anims
            if a.state() == QPropertyAnimation.State.Running
        ]

    def enable_gravity(self, enabled: bool = True):
        self._gravity_enabled = enabled
        if enabled:
            self._cached_effective_bottom = None
            if not self._gravity_timer.isActive():
                self._gravity_timer.start(self._gravity_interval)

    def _gravity_tick(self):
        if not self._gravity_enabled:
            return
        self._scan_tick += 1
        old_y = self._window.y()
        new_y = old_y + self._gravity_step
        effective_bottom = new_y

        try:
            from PySide6.QtWidgets import QApplication
            screen = QApplication.primaryScreen()
            if screen is None:
                return

            w = self._window.width()
            h = self._window.height()
            screen_bottom = screen.availableGeometry().bottom() - h
            new_y = old_y + self._gravity_step

            # 静止时：仅定时检查站立窗口是否存活
            was_at_bottom = self._cached_effective_bottom is not None and old_y >= self._cached_effective_bottom
            if was_at_bottom and self._cached_effective_bottom is not None:
                if self._standing_hwnd and self._scan_tick % self._ALIVE_CHECK_INTERVAL == 0:
                    if not is_window_alive(self._standing_hwnd):
                        print(f"[Gravity] standing window closed (hwnd={self._standing_hwnd})")
                        self._standing_hwnd = 0
                        self._cached_effective_bottom = None
                else:
                    effective_bottom = self._cached_effective_bottom
                    at_bottom = True
                    new_y = effective_bottom
                    self._window.move(self._window.x(), new_y)
                    return

            # 下落中：节流全量扫描
            if self._cached_effective_bottom is None or self._scan_tick % self._SCAN_INTERVAL == 0:
                old_pet_bottom = old_y + h
                new_pet_bottom = new_y + h
                pet_x = self._window.x()
                pet_self = (pet_x, old_y, pet_x + w, old_y + h)
                found_hwnd = 0

                effective_bottom = screen_bottom
                for win in get_visible_windows():
                    left, top, right, bottom = win["rect"]
                    if (left == pet_self[0] and top == pet_self[1]
                            and right == pet_self[2] and bottom == pet_self[3]):
                        continue
                    if pet_x + w <= left or pet_x >= right:
                        continue
                    if old_pet_bottom <= top <= new_pet_bottom:
                        landing = top - h
                        if landing < effective_bottom:
                            print(f"[Gravity] land on: \"{win['title'][:30]}\" top={top}")
                            effective_bottom = landing
                            found_hwnd = win["hwnd"]
                self._cached_effective_bottom = effective_bottom
                if found_hwnd:
                    self._standing_hwnd = found_hwnd
                elif effective_bottom == screen_bottom:
                    self._standing_hwnd = 0
            else:
                effective_bottom = self._cached_effective_bottom
        except Exception:
            if self._cached_effective_bottom is None:
                from PySide6.QtWidgets import QApplication as _QA
                s = _QA.primaryScreen()
                fb = s.availableGeometry().bottom() - self._window.height() if s else new_y
                self._cached_effective_bottom = fb
                effective_bottom = fb
            else:
                effective_bottom = self._cached_effective_bottom

        at_bottom = new_y >= effective_bottom
        if at_bottom:
            new_y = effective_bottom
        self._window.move(self._window.x(), new_y)

        if at_bottom and self._gravity_falling:
            self._gravity_falling = False
            self.play("idle")
        elif not at_bottom and not self._gravity_falling:
            self._gravity_falling = True
            self.play("floating")

    def move_to(self, start_pos, end_pos, duration=500, callback=None):
        """将窗口从 start_pos 移动到 end_pos。"""
        self._cleanup_stopped_anims()
        self.enable_gravity(False)
        print("from", start_pos, " move to:", end_pos)
        anim = QPropertyAnimation(self._window, b"pos")
        anim.setDuration(duration)
        anim.setStartValue(start_pos)
        anim.setEndValue(end_pos)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(lambda: self.enable_gravity(True))
        if callback:
            anim.finished.connect(callback)
        anim.start()
        self._win_anims.append(anim)
        return anim

    def fade_in(self, duration=300):
        """窗口淡入。"""
        self._cleanup_stopped_anims()
        anim = QPropertyAnimation(self._window, b"windowOpacity")
        anim.setDuration(duration)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.start()
        self._win_anims.append(anim)
        return anim

    def fade_out(self, duration=300, callback=None):
        """窗口淡出。"""
        self._cleanup_stopped_anims()
        anim = QPropertyAnimation(self._window, b"windowOpacity")
        anim.setDuration(duration)
        anim.setStartValue(self._window.windowOpacity())
        anim.setEndValue(0.0)
        if callback:
            anim.finished.connect(callback)
        anim.start()
        self._win_anims.append(anim)
        return anim

    def bounce(self, duration=600):
        """窗口弹跳。"""
        self._cleanup_stopped_anims()
        self.enable_gravity(False)
        original_pos = self._window.pos()
        anim = QPropertyAnimation(self._window, b"pos")
        anim.setDuration(duration)
        anim.setKeyValueAt(0, original_pos)
        anim.setKeyValueAt(0.3, QPoint(original_pos.x(), original_pos.y() - 40))
        anim.setKeyValueAt(0.5, original_pos)
        anim.setKeyValueAt(0.7, QPoint(original_pos.x(), original_pos.y() - 20))
        anim.setKeyValueAt(1, original_pos)
        anim.setEasingCurve(QEasingCurve.Type.OutBounce)
        anim.finished.connect(lambda: self.enable_gravity(True))
        anim.start()
        self._win_anims.append(anim)
        return anim

    def idle_sway(self, amplitude=3):
        """窗口左右轻微摇摆（返回 QTimer，可手动停止）。"""
        timer = QTimer(self)
        original_x = self._window.x()
        direction = 1

        def sway():
            nonlocal direction
            new_x = original_x + amplitude * direction
            self._window.move(new_x, self._window.y())
            direction *= -1

        timer.timeout.connect(sway)
        timer.start(1000)
        return timer

    def _load_action(self, action: str) -> list[QPixmap]:
        if action in self._cache:
            return self._cache[action]

        action_dir = os.path.join(self._pet_dir, action)
        frames: list[QPixmap] = []

        if not os.path.isdir(action_dir):
            return frames

        files = sorted(
            f for f in os.listdir(action_dir)
            if os.path.splitext(f)[1].lower() in _SUPPORTED_EXT
        )

        for f in files:
            pixmap = QPixmap(os.path.join(action_dir, f))
            if pixmap.isNull():
                continue
            pixmap = pixmap.scaled(
                config.PET_WIDTH,
                config.PET_HEIGHT,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            frames.append(pixmap)

        self._cache[action] = frames
        return frames

    def _next_frame(self):
        """切换到下一帧。"""
        self._current_frame += 1
        if self._current_frame >= len(self._frames):
            if self._loop:
                self._current_frame = 0
            else:
                self._frame_timer.stop()
                self.animation_finished.emit(self._current_action)
                return
        self._label.setPixmap(self._frames[self._current_frame])
