from PySide6.QtWidgets import QLabel, QWidget
from PySide6.QtCore import Qt, QTimer, QPoint, QPropertyAnimation, QParallelAnimationGroup, QEasingCurve
from PySide6.QtGui import QPainter, QColor, QPen, QPolygon
from config import config

TAIL_HEIGHT = 10


class SpeechBubble(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(
            "padding: 10px;"
            f"font-size: {config.BUBBLE_FONT_SIZE}px;"
            "color: #333;"
        )
        self.setWordWrap(True)
        self.setMaximumWidth(config.BUBBLE_MAX_WIDTH)
        self.setMinimumWidth(80)
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)
        self._follow_timer = QTimer(self)
        self._follow_timer.timeout.connect(self._follow_pet)
        self._anim_group: QParallelAnimationGroup | None = None

        # 打字机效果相关
        self._stream_buffer = ""
        self._char_queue: list[str] = []
        self._stream_ending = False   # True 表示队列打完后需触发隐藏
        self._type_timer = QTimer(self)
        self._type_timer.timeout.connect(self._type_next_char)
        self._type_interval = 35  # 每字符间隔（ms），可调节

        self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        body_h = h - TAIL_HEIGHT

        body_rect = self.rect()
        body_rect.setHeight(body_h)
        painter.setBrush(QColor(255, 255, 255, 220))
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        painter.drawRoundedRect(body_rect.adjusted(0, 0, -1, -1), 12, 12)

        cx = w // 2
        tail_top = body_h - 1
        tail = QPolygon([
            QPoint(cx - 6, tail_top),
            QPoint(cx + 6, tail_top),
            QPoint(cx,     h - 1),
        ])
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 220))
        painter.drawPolygon(tail)

        painter.end()
        super().paintEvent(event)

    def _resize_to_text(self):
        """根据当前文本重新计算气泡尺寸。"""
        text = self.text()
        self.setMinimumWidth(80)
        self.setMaximumWidth(config.BUBBLE_MAX_WIDTH)
        metrics = self.fontMetrics()
        avg_w = metrics.averageCharWidth()
        target_w = int(avg_w * 28)
        text_w = metrics.horizontalAdvance(text) + 20
        w = text_w if text_w <= target_w else target_w
        w = max(w, self.minimumWidth())
        w = min(w, self.maximumWidth())
        self.setFixedWidth(w)
        self.adjustSize()
        self.resize(self.width(), self.height() + TAIL_HEIGHT)

    def _reposition(self):
        """根据当前父窗口位置重新定位气泡。"""
        pet = self.parent()
        if isinstance(pet, QWidget) and self.isVisible():
            target = pet.geometry().center()
            final = self._final_position(target)
            self.move(final)

    def _start_tracking(self):
        self._follow_timer.start(50)

    def _start_hide_timer_ms(self, duration: int):
        self._hide_timer.start(duration)

    def show_text(self, text, duration=5000, parent_pos=None):
        self.setText(text)
        self._resize_to_text()

        if parent_pos is None and isinstance(self.parent(), QWidget):
            parent_pos = self.parent().geometry().center()

        if parent_pos is not None:
            start_pos = self._head_position(parent_pos)
            self.move(start_pos)
            self.setWindowOpacity(0.0)

        self.show()

        if parent_pos is not None:
            final_pos = self._final_position(parent_pos)
            self._anim_group = QParallelAnimationGroup(self)

            pos_anim = QPropertyAnimation(self, b"pos")
            pos_anim.setDuration(300)
            pos_anim.setStartValue(self.pos())
            pos_anim.setEndValue(final_pos)
            pos_anim.setEasingCurve(QEasingCurve.Type.OutBack)

            opacity_anim = QPropertyAnimation(self, b"windowOpacity")
            opacity_anim.setDuration(250)
            opacity_anim.setStartValue(0.0)
            opacity_anim.setEndValue(0.95)
            opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

            self._anim_group.addAnimation(pos_anim)
            self._anim_group.addAnimation(opacity_anim)
            self._anim_group.finished.connect(self._on_anim_finished)
            self._anim_group.start()
        else:
            self._start_tracking()

        self._start_hide_timer_ms(duration)

    def start_stream(self, parent_pos=None):
        """开始流式 - 显示空气泡并开始跟随桌宠。"""
        self._stream_buffer = ""
        self._char_queue.clear()
        self._stream_ending = False
        self._type_timer.stop()
        self.setText("")
        self._resize_to_text()

        if parent_pos is None and isinstance(self.parent(), QWidget):
            parent_pos = self.parent().geometry().center()

        if parent_pos is not None:
            pos = self._final_position(parent_pos)
            self.move(pos)

        self.show()
        self._start_tracking()

    def append_stream(self, chunk: str):
        """追加文本片段到队列，由定时器逐字显示（打字机效果）。"""
        self._char_queue.extend(chunk)
        if not self._type_timer.isActive():
            self._type_timer.start(self._type_interval)

    def _type_next_char(self):
        """定时器回调：从队列取一个字符显示。队列清空且正在结束流时触发隐藏。"""
        if self._char_queue:
            char = self._char_queue.pop(0)
            self._stream_buffer += char
            self.setText(self._stream_buffer)
            self._resize_to_text()
            self._reposition()
        else:
            self._type_timer.stop()
            if self._stream_ending:
                self._stream_ending = False
                self._finish_stream()

    def end_stream(self, duration: int = 5000):
        """结束流式：队列打完后再启动自动隐藏。"""
        self._end_stream_duration = duration
        if self._char_queue:
            # 还有字符未显示，标记结束状态，由 _type_next_char 队列耗尽后自动触发
            self._stream_ending = True
            if not self._type_timer.isActive():
                self._type_timer.start(self._type_interval)
        else:
            self._type_timer.stop()
            self._finish_stream()

    def _finish_stream(self):
        """流式结束后的收尾。"""
        if self._anim_group:
            self._anim_group.stop()
            self._anim_group = None
            self.setWindowOpacity(1.0)
        self._start_hide_timer_ms(self._end_stream_duration)

    def _head_position(self, target_pos: QPoint) -> QPoint:
        """气泡起始位置：桌宠头部（窗口上 1/3），气泡底部对齐头部下沿。"""
        pet_top = target_pos.y() - config.PET_HEIGHT // 2
        head_bottom = pet_top + config.PET_HEIGHT // 3
        x = target_pos.x() - self.width() // 2
        y = head_bottom - self.height()
        return QPoint(max(0, x), max(0, y))

    def _final_position(self, target_pos: QPoint) -> QPoint:
        """气泡最终位置：桌宠窗口正上方。"""
        x = target_pos.x() - self.width() // 2
        pet_top = target_pos.y() - config.PET_HEIGHT // 2
        y = pet_top - self.height() - 15
        return QPoint(max(0, x), max(0, y))

    def _on_anim_finished(self):
        self.setWindowOpacity(1.0)
        self._follow_timer.start(50)

    def hide(self):
        self._follow_timer.stop()
        if self._anim_group:
            self._anim_group.stop()
            self._anim_group.deleteLater()
            self._anim_group = None
        super().hide()

    def _follow_pet(self):
        pet = self.parent()
        if isinstance(pet, QWidget) and self.isVisible():
            target = pet.geometry().center()
            final = self._final_position(target)
            self.move(final)
