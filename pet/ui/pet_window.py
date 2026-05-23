from PySide6.QtWidgets import QLabel, QVBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtGui import QMouseEvent
from pet.ui.base_window import TransparentWindow
from pet.ui.pet_animations_player import PetAnimator
from config import config


class PetWindow(TransparentWindow):
    def __init__(self):
        super().__init__()
        self._setup_ui()
        self._old_pos = None

    def _setup_ui(self):
        self.setFixedSize(config.PET_WIDTH, config.PET_HEIGHT)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.pet_label = QLabel()
        self.pet_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.pet_label)

        self.pet_anim = PetAnimator(self, self.pet_label, parent=self)

        # 初始位置：屏幕底部居中
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = (geo.width() - config.PET_WIDTH) // 2
            y = geo.bottom() - config.PET_HEIGHT
            self.move(x, y)

        if not self.pet_anim.play("idle"):
            self._use_emoji_fallback()

    def play_action(self, action: str, loop: bool = True) -> bool:
        if self.pet_anim.play(action, loop=loop):
            return True
        self._use_emoji_fallback()
        return False

    def _use_emoji_fallback(self):
        self.pet_label.setText("\U0001f436")
        font = self.pet_label.font()
        font.setPointSize(48)
        self.pet_label.setFont(font)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._old_pos = event.globalPosition().toPoint()
            self.pet_anim.enable_gravity(False)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._old_pos is not None:
            delta = event.globalPosition().toPoint() - self._old_pos
            self.move(self.pos() + delta)
            self._old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._old_pos = None
        self.pet_anim.enable_gravity(True)
