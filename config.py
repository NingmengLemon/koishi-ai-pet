import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    APP_NAME = "DeskPet"
    WINDOW_WIDTH = 200
    WINDOW_HEIGHT = 200
    FPS = 30
    BUBBLE_MAX_WIDTH = 300
    BUBBLE_FONT_SIZE = 14
    LOG_LEVEL = "DEBUG"

    # AI Brains
    BRAIN_TYPE = os.getenv("BRAIN_TYPE", "openai")  # "openai" or "local"
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "deepseek-v4-pro")
    LOCAL_MODEL_PATH = os.getenv("LOCAL_MODEL_PATH", "")

    # Skills
    SCREEN_READER_ENABLED = True
    SYSTEM_MONITOR_ENABLED = True


config = Config()
