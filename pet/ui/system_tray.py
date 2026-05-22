from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction
from PySide6.QtCore import Qt, QObject

from pet.ui.debug_window import DebugWindow


class SystemTrayManager(QObject):
    """管理系统托盘图标和菜单"""

    def __init__(self, app, pet_window, agent=None):
        super().__init__()
        self.app = app
        self.pet = pet_window
        self.agent = agent
        self._debug_window = None

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self._create_temp_icon())
        self.tray_icon.setToolTip("Pet")
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

        self.toggle_action = QAction("显示/隐藏桌宠")
        self.toggle_action.triggered.connect(self._toggle_pet_visibility)
        self.menu.addAction(self.toggle_action)
        self.menu.addSeparator()

        self.debug_action = QAction("调试")
        self.debug_action.triggered.connect(self._show_debug_window)
        self.menu.addAction(self.debug_action)
        self.menu.addSeparator()

        self.quit_action = QAction("退出")
        self.quit_action.triggered.connect(self._quit_app)
        self.menu.addAction(self.quit_action)

        self.tray_icon.setContextMenu(self.menu)

    def _toggle_pet_visibility(self):
        self.pet.setVisible(not self.pet.isVisible())

    def _show_debug_window(self):
        if self._debug_window is None:
            self._debug_window = DebugWindow(self.pet, agent=self.agent)
        self._debug_window.show()
        self._debug_window.activateWindow()
        self._debug_window.raise_()

    def _quit_app(self):
        self.pet.close()
        self.tray_icon.hide()
        self.app.quit()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._toggle_pet_visibility()
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            if not self.pet.isVisible():
                self.pet.show()
