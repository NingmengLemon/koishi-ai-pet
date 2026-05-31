import ctypes
import logging
import os

from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QAction, QCursor
from PySide6.QtCore import QObject

from config import config

logger = logging.getLogger(__name__)

_ICON_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "assets", "icon", "sys_tray.png",
)


class SystemTrayManager(QObject):

    def __init__(self, app, pet_window):
        super().__init__()
        self.app = app
        self.pet = pet_window
        self.tray_icon = None

        if not config.SHOW_TRAY:
            return

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(_ICON_PATH))
        self.tray_icon.setToolTip("DeskPet")

        self.tray_icon.activated.connect(self._on_activated)
        self.tray_icon.show()

    def _show_menu(self):
        self.pet.raise_()
        try:
            ctypes.windll.user32.SetForegroundWindow(int(self.pet.winId()))
        except Exception:
            pass

        menu = QMenu(self.pet)

        if self.pet.isVisible():
            hide_action = QAction("隐藏", menu)
            hide_action.triggered.connect(self.pet.hide)
            menu.addAction(hide_action)
        else:
            show_action = QAction("显示", menu)
            show_action.triggered.connect(self.pet.show)
            menu.addAction(show_action)

        quit_action = QAction("退出", menu)
        quit_action.triggered.connect(self.app.quit)
        menu.addAction(quit_action)

        menu.exec(QCursor.pos())

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Context:
            self._show_menu()

    def hide(self):
        if self.tray_icon:
            self.tray_icon.hide()
