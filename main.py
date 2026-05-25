import sys
from datetime import datetime
from PySide6.QtWidgets import QApplication
from pet.ui.pet_window import PetWindow
from pet.ui.system_tray import SystemTrayManager
from pet.ui.bubble import SpeechBubble
from pet.agent import PetAgent
from config import config


def main():
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [Main] ===== DeskPet 启动 =====")
    print(f"[{ts}] [Main] BRAIN={config.BRAIN}, MODEL={config.LLM_MODEL}")

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
    print(f"[{ts}] [Main] SystemTrayManager ready")

    def _shutdown():
        ts2 = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts2}] [Main] shutting down...")
        agent.stop()
        window.shutdown()
        window.close()
        tray.tray_icon.hide()

    app.aboutToQuit.connect(_shutdown)

    print(f"[{ts}] [Main] Entering event loop")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
