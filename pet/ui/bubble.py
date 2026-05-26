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

    def show_text(self, text, duration=5000, parent_pos=None):
        self.setText(text)

        self.setMinimumWidth(80)
        self.setMaximumWidth(config.BUBBLE_MAX_WIDTH)

        metrics = self.fontMetrics()
        avg_w = metrics.averageCharWidth()
        target_w = int(avg_w * 28)
        text_w  = metrics.horizontalAdvance(text) + 20
        w = text_w if text_w <= target_w else target_w
        w = max(w, self.minimumWidth())
        w = min(w, self.maximumWidth())

        self.setFixedWidth(w)
        self.adjustSize()

        self.setMinimumWidth(80)
        self.setMaximumWidth(config.BUBBLE_MAX_WIDTH)
        self.resize(self.width(), self.height() + TAIL_HEIGHT)

        # 如果未传位置，从父窗口（桌宠窗口）获取
        if parent_pos is None and isinstance(self.parent(), QWidget):
            parent_pos = self.parent().geometry().center()

        if parent_pos is not None:
            # 将气泡置于桌宠头部（窗口上 1/3），透明度 0 → 从头部弹出
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
            self._follow_timer.start(50)

        # 显示时长 = 传入 duration，动画不占用显示时间
        self._hide_timer.start(duration)

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
