from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction
from PySide6.QtCore import Qt, QObject

from config import config


class SystemTrayManager(QObject):
    """管理系统托盘图标（可通过 SHOW_TRAY 配置关闭）。"""

    def __init__(self, app, pet_window):
        super().__init__()
        self.app = app
        self.pet = pet_window
        self.tray_icon = None

        if not config.SHOW_TRAY:
            return

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self._create_temp_icon())
        self.tray_icon.setToolTip("DeskPet")
        self._build_menu()
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _create_temp_icon(self):
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(255, 150, 100))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(2, 2, 28, 28)
        painter.end()
        return QIcon(pixmap)

    def _build_menu(self):
        self.menu = QMenu()

        quit_action = QAction("退出")
        quit_action.triggered.connect(self.app.quit)
        self.menu.addAction(quit_action)

        self.tray_icon.setContextMenu(self.menu)

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.pet.setVisible(not self.pet.isVisible())
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            if not self.pet.isVisible():
                self.pet.show()

    def hide(self):
        if self.tray_icon:
            self.tray_icon.hide()
