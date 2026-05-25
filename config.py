import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    
    APP_NAME = "DeskPet"
    PET_WIDTH = 125
    PET_HEIGHT = 125
    PET_FPS = 15
    BUBBLE_MAX_WIDTH = 300
    BUBBLE_FONT_SIZE = 14
    LOG_LEVEL = "DEBUG"

    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")

    BRAIN = os.getenv("BRAIN", "local")                  # local / llm / ollama
    LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-v4-pro") # 模型名
    LLM_KEY = os.getenv("LLM_KEY", "")                   # API Key
    LLM_URL = os.getenv("LLM_URL", "")                   # API 地址

    BEHAVIOR_PROMPT_SYSTEM = os.getenv(
        "BEHAVIOR_PROMPT_SYSTEM",
        "You are a cute desktop pet. Based on the context, "
        "decide what action to perform and what to say.\n"
        "Output format:\n"
        "Action: <action name>\n"
        "Speech: <your message or \"none\">",
    )
    BEHAVIOR_PROMPT_DECIDE = os.getenv(
        "BEHAVIOR_PROMPT_DECIDE",
        "Available actions: {actions}\n"
        "Context: {context}\n"
        "Respond with Action and Speech.",
    )

    CHAT_PROMPT_SYSTEM = os.getenv(
        "CHAT_PROMPT_SYSTEM",
        "You are a cute desktop pet. "
        "Keep responses brief and playful.",
    )

    VIEW_BRAIN = os.getenv("VIEW_BRAIN", "local")
    VIEW_MODEL = os.getenv("VIEW_MODEL", "")
    VIEW_MODEL_KEY = os.getenv("VIEW_MODEL_KEY", "")
    VIEW_MODEL_URL = os.getenv("VIEW_MODEL_URL", "")
    VIEW_PROMPT_SYSTEM = os.getenv(
        "VIEW_PROMPT_SYSTEM",
        "你是桌面宠物的视觉模块，负责分析屏幕截图内容。"
        "用中文回答，简洁有帮助。",
    )
    VIEW_PROMPT_VISION = os.getenv(
        "VIEW_PROMPT_VISION",
        "请描述这张截图中的内容，用户可能在做什么？",
    )

    SCREEN_READER_ENABLED = True
    SYSTEM_MONITOR_ENABLED = True
    SCHEDULER_AUTO_START = os.getenv("SCHEDULER_AUTO_START", "false").lower() == "true"
    SCHEDULER_FAST_MS = int(os.getenv("SCHEDULER_FAST_MS", "1000"))
    SCHEDULER_MID_MS = int(os.getenv("SCHEDULER_MID_MS", "30000"))
    SCHEDULER_SLOW_MS = int(os.getenv("SCHEDULER_SLOW_MS", "300000"))

    PET_PERSONALITY = os.getenv("PET_PERSONALITY", "")


config = Config()
