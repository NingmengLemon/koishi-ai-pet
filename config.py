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

    VISION_ENABLED = os.getenv("VISION_ENABLED", "false").lower() == "true"  # 模型是否支持 vision

    OCR_ENABLED = os.getenv("OCR_ENABLED", "false").lower() == "true"
    OCR_LANGUAGES = os.getenv("OCR_LANGUAGES", "ch_sim,en").split(",")

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

    VIEW_PROMPT_SYSTEM = os.getenv(
        "VIEW_PROMPT_SYSTEM",
        "你是桌面宠物的视觉模块，负责分析屏幕截图内容。"
        "用中文回答，简洁有帮助。",
    )
    VIEW_PROMPT_VISION = os.getenv(
        "VIEW_PROMPT_VISION",
        "请描述这张截图中的内容，用户可能在做什么？",
    )

    # 合并视觉+行为的统一提示（当 VISION_ENABLED=true 时使用）
    VISION_BEHAVIOR_PROMPT = os.getenv(
        "VISION_BEHAVIOR_PROMPT",
        "你是桌面宠物。你能看到用户的屏幕截图。"
        "根据截图内容，决定你接下来要做什么动作、说什么话。\n\n"
        "=== 可用动作 ===\n"
        "动画驱动类（不需要 duration）：\n"
        "  walk <left|right> [距离px]\n"
        "  bounce [dx=偏移] [dy=偏移]\n"
        "  fade_in\n"
        "  fade_out\n"
        "队列驱动类（必须写 duration=秒）：\n"
        "  sit duration=秒\n"
        "  sleep duration=秒\n"
        "  idle duration=秒\n"
        "  look_around duration=秒\n"
        "  stretch duration=秒\n\n"
        "=== 输出格式 ===\n"
        "Speech: <台词，不超过20字>\n"
        "Action: <动作1>\n"
        "Action: <动作2>\n"
        "Action: <动作3>\n\n"
        "至少输出3个Action行和1个Speech行。",
    )
    VISION_BEHAVIOR_DECIDE = os.getenv(
        "VISION_BEHAVIOR_DECIDE",
        "请观察截图，输出完整的动作序列和台词。\n"
        "Recent: {context}\n"
        "避免重复刚做过的动作和台词。",
    )

    SCREEN_READER_ENABLED = True
    SYSTEM_MONITOR_ENABLED = True
    SCHEDULER_AUTO_START = os.getenv("SCHEDULER_AUTO_START", "false").lower() == "true"
    SCHEDULER_FAST_MS = int(os.getenv("SCHEDULER_FAST_MS", "1000"))
    SCHEDULER_MID_MS = int(os.getenv("SCHEDULER_MID_MS", "30000"))
    SCHEDULER_SLOW_MS = int(os.getenv("SCHEDULER_SLOW_MS", "300000"))

    PET_PERSONALITY = os.getenv("PET_PERSONALITY", "")


config = Config()
