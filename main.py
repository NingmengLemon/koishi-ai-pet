import logging
import sys
from datetime import datetime
from PySide6.QtWidgets import QApplication
from pet.ui.pet_window import PetWindow
from pet.ui.system_tray import SystemTrayManager
from pet.ui.bubble import SpeechBubble
from pet.agent import PetAgent
from config import config

logger = logging.getLogger(__name__)


def main():
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL, logging.INFO),
        format="[%(name)s] %(message)s",
    )
    logger.info(f"===== DeskPet 启动 =====")
    logger.info(f"BRAIN={config.BRAIN}, MODEL={config.LLM_MODEL}")

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    agent = PetAgent()
    window = PetWindow()
    bubble = SpeechBubble(window)

    agent.action_requested.connect(window.queue_enqueue_action)
    agent.speak_requested.connect(bubble.show_text)

    window.show()
    agent.start()

    tray = SystemTrayManager(app, window, agent)
    logger.info(f"SystemTrayManager ready")

    def _shutdown():
        logger.info(f"shutting down...")
        agent.stop()
        window.shutdown()
        window.close()
        tray.tray_icon.hide()

    app.aboutToQuit.connect(_shutdown)

    logger.info(f"Entering event loop")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
