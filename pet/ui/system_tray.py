import os

from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import QObject

from pet.ui.debug_window import DebugWindow

_ICON_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "icon", "sys_tray.png")


class SystemTrayManager(QObject):
    """管理系统托盘图标和菜单"""

    def __init__(self, app, pet_window, agent=None):
        super().__init__()
        self.app = app
        self.pet = pet_window
        self.agent = agent
        self._debug_window = None

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(os.path.normpath(_ICON_PATH)))
        self.tray_icon.setToolTip("Pet")
        self._build_menu()
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

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
        self.app.quit()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._toggle_pet_visibility()
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            if not self.pet.isVisible():
                self.pet.show()
