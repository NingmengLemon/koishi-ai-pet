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


class _Base64Filter(logging.Filter):
    """全局过滤掉含 base64 图片编码的日志。"""
    def filter(self, record):
        msg = record.getMessage()
        if "base64" in msg or "data:image" in msg:
            return False
        if record.name in ("httpx", "httpcore") and len(msg) > 500:
            return False
        return True


def main():
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL, logging.INFO),
        format="[%(name)s] %(message)s",
    )
    # 全局加 base64 过滤器，不管哪个 logger 输出只要含 base64 都拦截
    root_filter = _Base64Filter()
    for _lib in ("httpx", "httpcore", "openai", "urllib3", ""):
        logging.getLogger(_lib).addFilter(root_filter)
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
        try:
            agent.stop()
            window.shutdown()
            window.close()
            tray.tray_icon.hide()
        except RuntimeError:
            pass  # C++ 对象可能已被 Qt 提前销毁

    app.aboutToQuit.connect(_shutdown)

    logger.info(f"Entering event loop")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
