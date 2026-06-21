# Settings UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a settings UI window that replaces .env-based configuration with a graphical interface, persisting user overrides to `settings.json` and applying many changes at runtime.

**Architecture:** New `pet/settings.py` handles JSON persistence (read/write `QStandardPaths.AppDataLocation/DeskPet/settings.json`). `Config` class gains a `save()` method that writes overrides and returns which keys need restart. A new `SettingsWindow` with 4 tabs (连接/行为/外观/人格) edits all config fields. Tray menu gains a "⚙ 设置" entry. Runtime hooks (`rebuild_client()`, `scheduler.update_config()`) apply changes live.

**Tech Stack:** PySide6 (QTabWidget, QLineEdit, QCheckBox, QComboBox, QTextEdit, QStandardPaths), JSON persistence, existing `Config` singleton pattern.

## Global Constraints

- All styles use existing `pet/ui/styles.py` color tokens (`_COLOR_*`) and variable names (`BUTTON_QSS`, `BUTTON_PRIMARY_QSS`, etc.)
- New styles added to `styles.py`, not inline
- Config keys map 1:1 to `Config` class attribute names (e.g., `BRAIN`, `LLM_URL`)
- Feature uses `QStandardPaths.AppDataLocation` for cross-platform settings path — no third-party deps
- Setting controls: QLineEdit for all text/numeric fields, QCheckBox for booleans, QComboBox for Brain mode, QTextEdit for long text (prompts/personality)
- Window follows same frameless + rounded style as `DebugWindow`

---

## File Structure

| File | Responsibility |
|------|---------------|
| `pet/settings.py` | **New.** `settings_path()`, `load_user_settings()`, `save_user_setting()`, `delete_user_settings()` — JSON persistence layer |
| `config.py` | **Modify.** Add `_load_user_settings()` to `__init__`, add `save()` method returning `(applied, needs_restart)` |
| `pet/brain/behavior.py` | **Modify.** Add `rebuild_client()` public method (re-runs `_setup()` under lock) |
| `pet/agent/scheduler.py` | **Modify.** Add `update_config()` method (re-creates timers with current config values, preserves callbacks) |
| `pet/ui/styles.py` | **Modify.** Add `TAB_BAR_QSS` constant |
| `pet/ui/settings_window.py` | **New.** `SettingsWindow` — 4-tab settings UI, singleton pattern |
| `pet/ui/system_tray.py` | **Modify.** Add "⚙ 设置" menu item |
| `main.py` | **Modify.** Wire settings window creation, add cleanup in `_shutdown` |

---

### Task 1: Settings persistence layer (`pet/settings.py`)

**Files:**
- Create: `pet/settings.py`

**Interfaces:**
- Consumes: `QStandardPaths` from PySide6, `os`, `json`, `logging`
- Produces: `settings_path() -> str`, `load_user_settings() -> dict`, `save_user_setting(key, value)`, `delete_user_settings(keys)` — all used by `Config` in Task 2

- [ ] **Step 1: Create `pet/settings.py`**

```python
"""用户设置持久化 — JSON 文件读写（覆盖 .env 默认值）。"""

import json
import logging
import os
from PySide6.QtCore import QStandardPaths

logger = logging.getLogger(__name__)


def settings_path() -> str:
    """返回跨平台 settings.json 路径，确保目录存在。

    Windows: %APPDATA%/DeskPet/settings.json
    macOS:   ~/Library/Application Support/DeskPet/settings.json
    """
    base = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "settings.json")


def load_user_settings() -> dict:
    """从 settings.json 读取用户覆盖值。文件不存在或解析失败返回空 dict。"""
    path = settings_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
        logger.warning(f"[Settings] {path}: expected dict, got {type(data).__name__}")
        return {}
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"[Settings] Failed to load {path}: {e}")
        return {}


def save_user_setting(key: str, value) -> None:
    """写入单个设置到 settings.json。value 必须可 JSON 序列化。"""
    current = load_user_settings()
    current[key] = value
    _write_settings(current)


def delete_user_settings(keys: list[str]) -> None:
    """从 settings.json 中删除指定 key。key 不存在则忽略。"""
    current = load_user_settings()
    changed = False
    for k in keys:
        if k in current:
            del current[k]
            changed = True
    if changed:
        _write_settings(current)


def _write_settings(data: dict) -> None:
    """原子写入 settings.json（写临时文件 → 重命名）。"""
    path = settings_path()
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except OSError as e:
        logger.error(f"[Settings] Failed to write {path}: {e}")
        if os.path.exists(tmp):
            os.remove(tmp)
```

- [ ] **Step 2: Commit**

```bash
git add pet/settings.py
git commit -m "feat(settings): add JSON persistence layer"
```

---

### Task 2: Config class — `save()` and `_load_user_settings()`

**Files:**
- Modify: `config.py`

**Interfaces:**
- Consumes: `pet/settings.py` (`load_user_settings`, `save_user_setting`, `delete_user_settings`)
- Produces: `Config.save(key, value) -> tuple[bool, list[str]]`, `Config.reset(keys)` method — used by SettingsWindow in Task 5

- [ ] **Step 1: Define key metadata and modify Config class**

Rewrite `config.py` to add:

1. A `_KEY_META` dict mapping key name → `(type_converter, default_env_var, category, needs_restart)`. This is the single source of truth for which keys exist, their types, and runtime behavior.

2. Convert all class-level constants to instance attributes set in `__init__` (so they stay writable at runtime).

3. Add `_load_user_settings()` called at end of `__init__`.

4. Add `save(key, value)` method.

5. Add `reset(keys)` method.

Replace `config.py` contents with:

```python
import os
from dotenv import load_dotenv
from pet.settings import load_user_settings, save_user_setting, delete_user_settings

load_dotenv()


# key: (type, env_default, category, needs_restart)
# type: "str", "int", "float", "bool", "str_list"
# category: "connection", "behavior", "appearance", "personality"
_KEY_META = {
    # Connection
    "BRAIN":                     ("str",      "local",       "connection",  False),
    "LLM_MODEL":                 ("str",      "",            "connection",  False),
    "LLM_KEY":                   ("str",      "",            "connection",  False),
    "LLM_URL":                   ("str",      "",            "connection",  False),
    "OLLAMA_BASE_URL":           ("str",      "http://localhost:11434/v1", "connection", False),
    "LLM_TIMEOUT":               ("int",      "30",          "connection",  False),
    "LLM_MAX_RETRIES":           ("int",      "3",           "connection",  False),
    "LLM_RETRY_DELAY":           ("float",    "1",           "connection",  False),
    "LLM_RETRY_MAX_DELAY":       ("float",    "8",           "connection",  False),
    "LLM_CACHE_PROMPT":          ("bool",     False,         "connection",  False),
    # Behavior
    "SCHEDULER_FAST_MS":         ("int",      "1000",        "behavior",    False),
    "SCHEDULER_MID_MS":          ("int",      "300000",      "behavior",    False),
    "SCHEDULER_SLOW_MS":         ("int",      "300000",      "behavior",    False),
    "SCHEDULER_AUTO_START_FAST": ("bool",     True,          "behavior",    False),
    "SCHEDULER_AUTO_START_MID":  ("bool",     True,          "behavior",    False),
    "SCHEDULER_AUTO_START_SLOW": ("bool",     True,          "behavior",    False),
    "SCHEDULER_IDLE_TIMEOUT_MS": ("int",      "900000",      "behavior",    False),
    "ACTION_TIMEOUT_MS":         ("int",      "15000",       "behavior",    False),
    "SANITY_CRITICAL_THRESHOLD": ("int",      "20",          "behavior",    False),
    "INTERACT_GRABBED_PROMPT":      ("str",  "",  "behavior", False),
    "INTERACT_RELEASED_PROMPT":     ("str",  "",  "behavior", False),
    "INTERACT_WINDOW_DISAPPEARED_PROMPT": ("str", "", "behavior", False),
    "INTERACT_FED_PROMPT":          ("str",  "",  "behavior", False),
    # Appearance
    "VISION_ENABLED":     ("bool",  False,    "appearance",  False),
    "VISION_SCALE":       ("float", "1",      "appearance",  False),
    "SKILLS_ENABLED":     ("str_list", "",     "appearance",  True),
    "PET_WIDTH":          ("int",   "125",     "appearance",  True),
    "PET_HEIGHT":         ("int",   "125",     "appearance",  True),
    "PET_FPS":            ("int",   "15",      "appearance",  True),
    "BUBBLE_MAX_WIDTH":   ("int",   "300",     "appearance",  True),
    "BUBBLE_FONT_SIZE":   ("int",   "14",      "appearance",  True),
    "SHOW_TRAY":          ("bool",  True,      "appearance",  True),
    "HIDE_CONSOLE":       ("bool",  True,      "appearance",  True),
    "LOG_LEVEL":          ("str",   "DEBUG",   "appearance",  False),
    # Personality
    "PET_PERSONALITY":     ("str",   "",        "personality", False),
}


def _convert(raw, type_name):
    """将字符串/原始值按类型转换。"""
    if type_name == "bool":
        if isinstance(raw, bool):
            return raw
        return str(raw).lower() in ("1", "true", "yes")
    if type_name == "int":
        return int(raw)
    if type_name == "float":
        return float(raw)
    if type_name == "str_list":
        if isinstance(raw, list):
            return raw
        return [s.strip() for s in str(raw).split(",") if s.strip()] if raw else []
    return str(raw)


class Config:

    def __init__(self):
        self._load_env()
        self._load_user_settings()

    def _load_env(self):
        """从环境变量加载默认值到实例属性。"""
        self.BRAIN = os.getenv("BRAIN", "local")
        self.LLM_MODEL = os.getenv("LLM_MODEL", "")
        self.LLM_KEY = os.getenv("LLM_KEY", "")
        self.LLM_URL = os.getenv("LLM_URL", "")
        self.OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")

        self.LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "30"))
        self.LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "3"))
        self.LLM_RETRY_DELAY = float(os.getenv("LLM_RETRY_DELAY", "1"))
        self.LLM_RETRY_MAX_DELAY = float(os.getenv("LLM_RETRY_MAX_DELAY", "8"))
        self.LLM_CACHE_PROMPT = os.getenv("LLM_CACHE_PROMPT", "").lower() in ("1", "true", "yes")

        self.VISION_ENABLED = os.getenv("VISION_ENABLED", "false").lower() == "true"
        self.VISION_SCALE = float(os.getenv("VISION_SCALE", "1"))

        self.PET_WIDTH = int(os.getenv("PET_WIDTH", "125"))
        self.PET_HEIGHT = int(os.getenv("PET_HEIGHT", "125"))
        self.PET_FPS = int(os.getenv("PET_FPS", "15"))
        self.BUBBLE_MAX_WIDTH = int(os.getenv("BUBBLE_MAX_WIDTH", "300"))
        self.BUBBLE_FONT_SIZE = int(os.getenv("BUBBLE_FONT_SIZE", "14"))
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG")

        self.ACTION_TIMEOUT_MS = int(os.getenv("ACTION_TIMEOUT_MS", "15000"))

        self.SCHEDULER_AUTO_START_FAST = os.getenv("SCHEDULER_AUTO_START_FAST", "true").lower() == "true"
        self.SCHEDULER_AUTO_START_MID = os.getenv("SCHEDULER_AUTO_START_MID", "true").lower() == "true"
        self.SCHEDULER_AUTO_START_SLOW = os.getenv("SCHEDULER_AUTO_START_SLOW", "true").lower() == "true"
        self.SCHEDULER_FAST_MS = int(os.getenv("SCHEDULER_FAST_MS", "1000"))
        self.SCHEDULER_MID_MS = int(os.getenv("SCHEDULER_MID_MS", "300000"))
        self.SCHEDULER_SLOW_MS = int(os.getenv("SCHEDULER_SLOW_MS", "300000"))
        self.SCHEDULER_IDLE_TIMEOUT_MS = int(os.getenv("SCHEDULER_IDLE_TIMEOUT_MS", "900000"))

        self.PET_PERSONALITY = os.getenv("PET_PERSONALITY", "")

        self.INTERACT_GRABBED_PROMPT = os.getenv("INTERACT_GRABBED_PROMPT", "")
        self.INTERACT_RELEASED_PROMPT = os.getenv("INTERACT_RELEASED_PROMPT", "")
        self.INTERACT_WINDOW_DISAPPEARED_PROMPT = os.getenv("INTERACT_WINDOW_DISAPPEARED_PROMPT", "")
        self.INTERACT_FED_PROMPT = os.getenv("INTERACT_FED_PROMPT", "")

        self.SKILLS_ENABLED = os.getenv("SKILLS_ENABLED", "").split(",") if os.getenv("SKILLS_ENABLED") else []

        self.SANITY_CRITICAL_THRESHOLD = int(os.getenv("SANITY_CRITICAL_THRESHOLD", "20"))
        self.SHOW_TRAY = os.getenv("SHOW_TRAY", "true").lower() == "true"
        self.HIDE_CONSOLE = os.getenv("HIDE_CONSOLE", "true").lower() == "true"

    def _load_user_settings(self):
        """从 settings.json 读取覆盖值，更新实例属性。"""
        data = load_user_settings()
        self._user_settings = data
        for key, value in data.items():
            if key not in _KEY_META:
                continue
            type_name = _KEY_META[key][0]
            try:
                setattr(self, key, _convert(value, type_name))
            except (ValueError, TypeError):
                pass  # 跳过类型转换失败的条目

    def save(self, key: str, value) -> tuple[bool, list[str]]:
        """保存单个设置到 settings.json 并更新实例属性。

        返回 (applied, needs_restart):
          applied: 是否已更新到当前实例
          needs_restart: 需要重启才能生效的 key 列表（可能包含本次 key）
        """
        type_name = _KEY_META[key][0]
        converted = _convert(value, type_name)
        setattr(self, key, converted)
        save_user_setting(key, converted)
        needs_restart = [key] if _KEY_META[key][3] else []
        return (True, needs_restart)

    def reset(self, keys: list[str]):
        """从 settings.json 删除指定 key，回退到 .env 默认值。"""
        delete_user_settings(keys)
        # 从环境变量重新读取默认值
        self._load_env()
        self._load_user_settings()


config = Config()
```

- [ ] **Step 2: Commit**

```bash
git add config.py
git commit -m "feat(settings): add save/reset and user settings overlay to Config"
```

---

### Task 3: Runtime update hooks — `rebuild_client()` and `update_config()`

**Files:**
- Modify: `pet/brain/behavior.py` (add `rebuild_client()`)
- Modify: `pet/agent/scheduler.py` (add `update_config()`)

**Interfaces:**
- Consumes: `config` singleton (already imported)
- Produces: `Behavior.rebuild_client()`, `Scheduler.update_config()` — called by SettingsWindow after saving connection/behavior settings

- [ ] **Step 1: Add `rebuild_client()` to `Behavior`**

In `pet/brain/behavior.py`, add a public method after `_setup()`:

```python
def rebuild_client(self):
    """运行时重建 LLM 客户端（设置界面修改连接配置后调用）。"""
    with self._lock:
        self._setup()
    client_type = "None (local)" if self._client is None else f"{type(self._client).__name__}(model={self._model})"
    logger.info(f"[Behavior] rebuild_client: {client_type}")
```

- [ ] **Step 2: Add `update_config()` to `Scheduler`**

In `pet/agent/scheduler.py`, add a public method after `init()`:

```python
def update_config(self):
    """运行时更新调度器配置（设置界面修改调度参数后调用）。

    重建定时器但保留已注册的回调和手动暂停状态。
    """
    if not self._initialized:
        return
    auto_fast = "fast" not in self._manually_paused and self._timers.get("fast", QTimer()).isActive()
    auto_mid = "mid" not in self._manually_paused and self._timers.get("mid", QTimer()).isActive()
    auto_slow = "slow" not in self._manually_paused and self._timers.get("slow", QTimer()).isActive()
    self._idle_timeout_ms = config.SCHEDULER_IDLE_TIMEOUT_MS
    self.init(auto_fast=auto_fast, auto_mid=auto_mid, auto_slow=auto_slow)
    logger.info("[Scheduler] config updated — timers rebuilt")
```

> Note: `init()` already stops old timers, reads `config.SCHEDULER_*_MS`, creates new timers, and preserves the callback list in `self._callbacks`. The `auto_*` flags are derived from current pause/active states to minimize disruption.

- [ ] **Step 3: Commit**

```bash
git add pet/brain/behavior.py pet/agent/scheduler.py
git commit -m "feat(settings): add rebuild_client() and update_config() runtime hooks"
```

---

### Task 4: Tab bar style (`pet/ui/styles.py`)

**Files:**
- Modify: `pet/ui/styles.py`

**Interfaces:**
- Produces: `TAB_BAR_QSS` constant — used by `SettingsWindow` in Task 5

- [ ] **Step 1: Add `TAB_BAR_QSS` to `styles.py`**

Append after `SEPARATOR_QSS` at the end of the file:

```python

# ── Tab Bar（设置界面用）

TAB_BAR_QSS = """
QTabWidget::pane {
    border: 1px solid """ + _COLOR_BORDER + """;
    border-radius: 6px;
    background: """ + _COLOR_SURFACE + """;
    padding: 4px;
}
QTabBar::tab {
    background: """ + _COLOR_SURFACE + """;
    border: 1px solid """ + _COLOR_BORDER + """;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 6px 14px;
    font-size: 12px;
    color: """ + _COLOR_TEXT_SEC + """;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background: """ + _COLOR_SURFACE + """;
    color: """ + _COLOR_TEXT + """;
    font-weight: bold;
    border-bottom: 2px solid """ + _COLOR_ACCENT + """;
}
QTabBar::tab:hover:!selected {
    background: #e8e8e8;
}
"""
```

- [ ] **Step 2: Commit**

```bash
git add pet/ui/styles.py
git commit -m "feat(styles): add TAB_BAR_QSS for settings tabs"
```

---

### Task 5: Settings window UI (`pet/ui/settings_window.py`)

**Files:**
- Create: `pet/ui/settings_window.py`

**Interfaces:**
- Consumes: `Config` from `config.py`, `TAB_BAR_QSS` + `BUTTON_QSS` + `BUTTON_PRIMARY_QSS` + `INPUT_QSS` + `CHECKBOX_QSS` + `TEXTEDIT_QSS` + `COMBOBOX_QSS` + `LABEL_SECONDARY_QSS` + `ICON_PATH` + `PANEL_QSS` from `pet/ui/styles.py`, runtime hooks (`rebuild_client`, `update_config`)
- Produces: `SettingsWindow` class with `show_instance(agent)` class method (singleton)

This is the largest task. The file creates the 4-tab settings window.

- [ ] **Step 1: Create `pet/ui/settings_window.py`**

```python
"""设置界面 — 替代 .env 的图形化配置。"""

from __future__ import annotations

import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QCheckBox, QComboBox, QTextEdit, QTabWidget,
    QFormLayout, QGroupBox, QMessageBox,
)
from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtGui import QIcon, QFont, QPainter, QPainterPath, QPen, QColor

from config import config, _KEY_META
from pet.ui.styles import (
    ICON_PATH, PANEL_QSS, BUTTON_QSS, BUTTON_PRIMARY_QSS,
    INPUT_QSS, COMBOBOX_QSS, TEXTEDIT_QSS, CHECKBOX_QSS,
    LABEL_SECONDARY_QSS, TAB_BAR_QSS,
)

logger = logging.getLogger(__name__)

_W = 520
_H = 600


class _LLMTestWorker(QObject):
    """子线程执行 LLM 连通性测试。"""
    finished = Signal(bool, str, float)  # success, content_or_error, elapsed

    def __init__(self, brain):
        super().__init__()
        self._brain = brain

    def run(self):
        import time
        start = time.time()
        try:
            reply = self._brain._llm_call([
                {"role": "system", "content": "你是调试助手。"},
                {"role": "user", "content": "请回复 'OK' 表示联通正常。"},
            ], max_tokens=50)
            elapsed = time.time() - start
            content = reply.choices[0].message.content or "(空响应)"
            self.finished.emit(True, content, elapsed)
        except Exception as e:
            elapsed = time.time() - start
            self.finished.emit(False, str(e), elapsed)


class SettingsWindow(QWidget):
    _instance: SettingsWindow | None = None

    @classmethod
    def show_instance(cls, agent, parent=None):
        """单例模式 — 获取或创建设置窗口并显示。"""
        if cls._instance is not None:
            try:
                cls._instance.isVisible()
            except RuntimeError:
                cls._instance = None
        if cls._instance is None:
            cls._instance = cls(agent, parent=parent)
        cls._instance._load_values()
        cls._instance.show()
        cls._instance.raise_()

    def __init__(self, agent, parent=None):
        super().__init__(parent)
        self.agent = agent
        self._llm_thread = None
        self._llm_worker = None

        self.setObjectName("settingsWindow")
        self.setWindowTitle("⚙ 设置")
        self.resize(_W, _H)
        self.setFixedSize(_W, _H)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Window
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        try:
            self.setWindowIcon(QIcon(ICON_PATH))
        except Exception:
            pass

        self._setup_ui()
        self.setStyleSheet(
            PANEL_QSS + BUTTON_QSS + BUTTON_PRIMARY_QSS +
            INPUT_QSS + COMBOBOX_QSS + TEXTEDIT_QSS + CHECKBOX_QSS +
            TAB_BAR_QSS
        )

    # ── UI 构建 ──

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 背景
        bg = QWidget()
        bg.setObjectName("settingsBg")
        bg.setStyleSheet("""
            QWidget#settingsBg {
                background: #f0f0f0;
                border-radius: 8px;
                font-size: 12px;
            }
        """)
        layout = QVBoxLayout(bg)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        root.addWidget(bg)

        # 标题栏
        title_bar = QWidget()
        title_bar.setFixedHeight(30)
        title_row = QHBoxLayout(title_bar)
        title_row.setContentsMargins(10, 0, 4, 0)
        title_row.setSpacing(6)
        title = QLabel("⚙ 设置")
        title.setStyleSheet("font-size:13px; color:#444; font-weight:bold; background:transparent;")
        title_row.addWidget(title)
        title_row.addStretch()
        btn_close = QPushButton("✕")
        btn_close.setFixedSize(28, 28)
        btn_close.setStyleSheet("""
            QPushButton { background: transparent; border: none; border-radius: 14px;
                         font-size: 14px; color: #999; }
            QPushButton:hover { background: #e81123; color: #fff; }
        """)
        btn_close.clicked.connect(self.close)
        title_row.addWidget(btn_close)
        layout.addWidget(title_bar)

        # 标题栏拖拽
        self._drag_pos = None
        title_bar.mousePressEvent = self._header_press
        title_bar.mouseMoveEvent = self._header_move

        # Tab Widget
        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_connection_tab(), "连接")
        self._tabs.addTab(self._build_behavior_tab(), "行为")
        self._tabs.addTab(self._build_appearance_tab(), "外观")
        self._tabs.addTab(self._build_personality_tab(), "人格")
        layout.addWidget(self._tabs, stretch=1)

        # 底部操作栏
        bottom = QHBoxLayout()
        bottom.setContentsMargins(12, 4, 12, 8)
        btn_reset = QPushButton("重置为默认")
        btn_reset.setStyleSheet(BUTTON_QSS)
        btn_reset.clicked.connect(self._on_reset)
        bottom.addWidget(btn_reset)
        bottom.addStretch()
        btn_save = QPushButton("保存")
        btn_save.setStyleSheet(BUTTON_PRIMARY_QSS)
        btn_save.clicked.connect(self._on_save)
        bottom.addWidget(btn_save)
        layout.addLayout(bottom)

    # ── 值控件映射 ──
    # _fields: dict[str, QWidget] — key 是 Config 属性名

    def _line(self, key: str, placeholder: str = "") -> QLineEdit:
        """创建 QLineEdit 并注册到 _fields。"""
        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        self._fields[key] = edit
        return edit

    def _check(self, key: str, label: str) -> QCheckBox:
        """创建 QCheckBox 并注册到 _fields。"""
        cb = QCheckBox(label)
        self._fields[key] = cb
        return cb

    def _text_area(self, key: str) -> QTextEdit:
        """创建 QTextEdit 并注册到 _fields。"""
        te = QTextEdit()
        te.setAcceptRichText(False)
        self._fields[key] = te
        return te

    # ── Tab 1: 连接 ──

    def _build_connection_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)

        form = QFormLayout()
        form.setSpacing(6)

        self._fields = {}

        # Brain 模式
        self._brain_combo = QComboBox()
        self._brain_combo.addItems(["local", "llm", "ollama"])
        self._fields["BRAIN"] = self._brain_combo
        form.addRow("Brain 模式:", self._brain_combo)

        form.addRow("API 地址:", self._line("LLM_URL", "https://api.example.com/v1"))
        form.addRow("Ollama 地址:", self._line("OLLAMA_BASE_URL", "http://localhost:11434/v1"))

        # API Key + toggle
        key_row = QHBoxLayout()
        self._llm_key_edit = QLineEdit()
        self._llm_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._llm_key_edit.setPlaceholderText("sk-...")
        self._fields["LLM_KEY"] = self._llm_key_edit
        key_row.addWidget(self._llm_key_edit)
        self._key_toggle = QPushButton("👁")
        self._key_toggle.setFixedWidth(28)
        self._key_toggle.setCheckable(True)
        self._key_toggle.setStyleSheet("""
            QPushButton { background: transparent; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; }
            QPushButton:checked { background: #e0e0e0; }
        """)
        self._key_toggle.toggled.connect(
            lambda checked: self._llm_key_edit.setEchoMode(
                QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
            )
        )
        key_row.addWidget(self._key_toggle)
        form.addRow("API Key:", key_row)

        form.addRow("模型名称:", self._line("LLM_MODEL", "gpt-4o"))
        form.addRow("请求超时(秒):", self._line("LLM_TIMEOUT", "30"))
        form.addRow("最大重试次数:", self._line("LLM_MAX_RETRIES", "3"))
        form.addRow("重试延迟(秒):", self._line("LLM_RETRY_DELAY", "1"))
        form.addRow("最大重试延迟(秒):", self._line("LLM_RETRY_MAX_DELAY", "8"))
        form.addRow("", self._check("LLM_CACHE_PROMPT", "Prompt 缓存"))

        layout.addLayout(form)

        # 测试连接按钮
        test_row = QHBoxLayout()
        self._btn_test = QPushButton("测试连接")
        self._btn_test.setStyleSheet(BUTTON_QSS)
        self._btn_test.clicked.connect(self._test_llm)
        test_row.addWidget(self._btn_test)
        self._label_test = QLabel("就绪")
        self._label_test.setStyleSheet("color:#666; font-size:11px;")
        test_row.addWidget(self._label_test)
        test_row.addStretch()
        layout.addLayout(test_row)

        self._test_output = QTextEdit()
        self._test_output.setReadOnly(True)
        self._test_output.setMaximumHeight(60)
        self._test_output.setFont(QFont("Consolas", 9) if hasattr(QFont, "__init__") else self._test_output.font())
        self._test_output.setStyleSheet(TEXTEDIT_QSS)
        layout.addWidget(self._test_output)

        layout.addStretch()
        return w

    # ── Tab 2: 行为 ──

    def _build_behavior_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)

        # 调度器
        sched_group = QGroupBox("调度器")
        sched_form = QFormLayout(sched_group)
        sched_form.setSpacing(6)
        sched_form.addRow("Fast 间隔(ms):", self._line("SCHEDULER_FAST_MS", "1000"))
        sched_form.addRow("Mid 间隔(ms):", self._line("SCHEDULER_MID_MS", "300000"))
        sched_form.addRow("Slow 间隔(ms):", self._line("SCHEDULER_SLOW_MS", "300000"))
        sched_form.addRow("空闲超时(ms):", self._line("SCHEDULER_IDLE_TIMEOUT_MS", "900000"))
        sched_form.addRow("动作超时(ms):", self._line("ACTION_TIMEOUT_MS", "15000"))
        sched_form.addRow("", self._check("SCHEDULER_AUTO_START_FAST", "自动启动 Fast"))
        sched_form.addRow("", self._check("SCHEDULER_AUTO_START_MID", "自动启动 Mid"))
        sched_form.addRow("", self._check("SCHEDULER_AUTO_START_SLOW", "自动启动 Slow"))
        layout.addWidget(sched_group)

        # 理智
        sanity_row = QFormLayout()
        sanity_row.addRow("理智临界值:", self._line("SANITY_CRITICAL_THRESHOLD", "20"))
        layout.addLayout(sanity_row)

        # 交互 prompt
        prompt_group = QGroupBox("交互 Prompt")
        prompt_layout = QVBoxLayout(prompt_group)
        for label, key in [("抓取", "INTERACT_GRABBED_PROMPT"),
                           ("放下", "INTERACT_RELEASED_PROMPT"),
                           ("窗口消失", "INTERACT_WINDOW_DISAPPEARED_PROMPT")]:
            prompt_layout.addWidget(QLabel(label))
            prompt_layout.addWidget(self._text_area(key))
        layout.addWidget(prompt_group)

        layout.addStretch()
        return w

    # ── Tab 3: 外观 ──

    def _build_appearance_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)

        form = QFormLayout()
        form.setSpacing(6)

        form.addRow("", self._check("VISION_ENABLED", "Vision（截图理解）"))
        form.addRow("截图缩放比例:", self._line("VISION_SCALE", "1"))
        form.addRow("技能插件(逗号分隔,*=全部):", self._line("SKILLS_ENABLED", "*"))

        # 需重启提示
        restart_label = QLabel("以下设置需要重启后生效：")
        restart_label.setStyleSheet("color:#e67e22; font-size:11px; font-weight:bold;")
        form.addRow(restart_label)

        form.addRow("宠物宽度:", self._line("PET_WIDTH", "125"))
        form.addRow("宠物高度:", self._line("PET_HEIGHT", "125"))
        form.addRow("FPS:", self._line("PET_FPS", "15"))
        form.addRow("气泡最大宽度:", self._line("BUBBLE_MAX_WIDTH", "300"))
        form.addRow("气泡字号:", self._line("BUBBLE_FONT_SIZE", "14"))
        form.addRow("", self._check("HIDE_CONSOLE", "隐藏控制台"))
        form.addRow("", self._check("SHOW_TRAY", "显示托盘图标"))
        form.addRow("日志级别:", self._line("LOG_LEVEL", "INFO"))

        layout.addLayout(form)
        layout.addStretch()
        return w

    # ── Tab 4: 人格 ──

    def _build_personality_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)

        layout.addWidget(QLabel("宠物人格 Prompt"))
        layout.addWidget(self._text_area("PET_PERSONALITY"), stretch=1)

        return w

    # ── 加载 / 保存 ──

    def _load_values(self):
        """从 config 读取当前值填充各控件。"""
        for key, widget in self._fields.items():
            value = getattr(config, key, None)
            if value is None:
                continue
            if isinstance(widget, QLineEdit):
                if isinstance(value, list):
                    widget.setText(",".join(value))
                else:
                    widget.setText(str(value))
            elif isinstance(widget, QCheckBox):
                widget.setChecked(bool(value))
            elif isinstance(widget, QComboBox):
                idx = widget.findText(str(value))
                widget.setCurrentIndex(max(idx, 0))
            elif isinstance(widget, QTextEdit):
                widget.setPlainText(str(value))

    def _collect_values(self) -> dict:
        """从控件收集当前值，返回 {key: value}。"""
        result = {}
        for key, widget in self._fields.items():
            type_name = _KEY_META[key][0]
            if isinstance(widget, QLineEdit):
                raw = widget.text().strip()
                if type_name == "int":
                    try:
                        result[key] = int(raw)
                    except ValueError:
                        continue
                elif type_name == "float":
                    try:
                        result[key] = float(raw)
                    except ValueError:
                        continue
                elif type_name == "str_list":
                    result[key] = [s.strip() for s in raw.split(",") if s.strip()] if raw and raw != "*" else ["*"] if raw == "*" else []
                else:
                    result[key] = raw
            elif isinstance(widget, QCheckBox):
                result[key] = widget.isChecked()
            elif isinstance(widget, QComboBox):
                result[key] = widget.currentText()
            elif isinstance(widget, QTextEdit):
                result[key] = widget.toPlainText()
        return result

    def _on_save(self):
        """保存所有修改并即时生效。"""
        values = self._collect_values()
        needs_restart_keys = []
        needs_rebuild_client = False
        needs_scheduler_update = False

        connection_keys = {"BRAIN", "LLM_URL", "OLLAMA_BASE_URL", "LLM_KEY",
                          "LLM_MODEL", "LLM_TIMEOUT", "LLM_MAX_RETRIES",
                          "LLM_RETRY_DELAY", "LLM_RETRY_MAX_DELAY", "LLM_CACHE_PROMPT"}
        scheduler_keys = {"SCHEDULER_FAST_MS", "SCHEDULER_MID_MS", "SCHEDULER_SLOW_MS",
                         "SCHEDULER_IDLE_TIMEOUT_MS", "ACTION_TIMEOUT_MS",
                         "SCHEDULER_AUTO_START_FAST", "SCHEDULER_AUTO_START_MID",
                         "SCHEDULER_AUTO_START_SLOW"}

        for key, value in values.items():
            _, needs_restart = config.save(key, value)
            if needs_restart:
                needs_restart_keys.append(key)
            if key in connection_keys:
                needs_rebuild_client = True
            if key in scheduler_keys:
                needs_scheduler_update = True

        # 运行时钩子
        if needs_rebuild_client and self.agent and hasattr(self.agent, 'behavior'):
            try:
                self.agent.behavior.rebuild_client()
            except Exception as e:
                logger.exception(f"[Settings] rebuild_client failed: {e}")

        if needs_scheduler_update and self.agent and hasattr(self.agent, 'scheduler'):
            try:
                self.agent.scheduler.update_config()
            except Exception as e:
                logger.exception(f"[Settings] scheduler.update_config failed: {e}")

        if needs_restart_keys:
            QMessageBox.warning(
                self, "设置已保存",
                f"以下设置将在下次启动后生效：\n{', '.join(needs_restart_keys)}"
            )
        else:
            QMessageBox.information(self, "设置已保存", "所有设置已即时生效。")

    def _on_reset(self):
        """重置当前 tab 的所有字段为 .env 默认值。"""
        current_tab = self._tabs.currentIndex()
        category_map = {0: "connection", 1: "behavior", 2: "appearance", 3: "personality"}
        category = category_map.get(current_tab, "connection")
        keys = [k for k, v in _KEY_META.items() if v[2] == category]
        config.reset(keys)
        self._load_values()
        QMessageBox.information(self, "已重置", f"{category} 设置已重置为默认值。")

    # ── LLM 连通性测试 ──

    def _test_llm(self):
        """在子线程测试 LLM 连通性。"""
        if not self.agent or not hasattr(self.agent, 'behavior'):
            return
        brain_cfg = self._brain_combo.currentText()
        if brain_cfg == "local" or not self.agent.behavior._client:
            self._test_output.clear()
            self._test_output.append("⚠ 当前为 local 模式或未配置客户端")
            self._label_test.setText("未配置")
            return

        self._test_output.clear()
        self._test_output.append("测试中...")
        self._btn_test.setEnabled(False)
        self._label_test.setText("测试中...")

        self._llm_thread = QThread()
        self._llm_worker = _LLMTestWorker(self.agent.behavior)
        self._llm_worker.moveToThread(self._llm_thread)
        self._llm_thread.started.connect(self._llm_worker.run)
        self._llm_worker.finished.connect(self._on_llm_test_result)
        self._llm_worker.finished.connect(self._llm_thread.quit)
        self._llm_thread.start()

    def _on_llm_test_result(self, success: bool, content: str, elapsed: float):
        self._test_output.clear()
        if success:
            self._test_output.append(f"✅ 连接成功 ({elapsed:.1f}s)")
            self._test_output.append(f"响应: {content[:200]}")
            self._label_test.setText("✅ 正常")
        else:
            self._test_output.append(f"❌ 连接失败 ({elapsed:.1f}s)")
            self._test_output.append(f"错误: {content}")
            self._label_test.setText("❌ 失败")
        self._btn_test.setEnabled(True)

    # ── 窗口拖拽 ──

    def _header_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()

    def _header_move(self, event):
        if self._drag_pos is not None:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.move(self.pos() + delta)
            self._drag_pos = event.globalPosition().toPoint()

    # ── 圆角背景 ──

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(0, 0, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(rect, 10, 10)
        painter.fillPath(path, QColor("#f0f0f0"))
        painter.setPen(QPen(QColor("#cccccc"), 1))
        painter.drawPath(path)
```

- [ ] **Step 2: Commit**

```bash
git add pet/ui/settings_window.py
git commit -m "feat(settings): add SettingsWindow with 4 tabs and LLM test"
```

---

### Task 6: Tray menu entry and main.py wiring

**Files:**
- Modify: `pet/ui/system_tray.py`
- Modify: `main.py`

**Interfaces:**
- Consumes: `SettingsWindow` from Task 5, `agent` and `window` references from `main.py`
- Produces: "⚙ 设置" tray menu item, SettingsWindow lifecycle management

- [ ] **Step 1: Add settings menu item to SystemTrayManager**

In `pet/ui/system_tray.py`, modify `_show_menu()` to add a "⚙ 设置" action between the show/hide action and the quit action.

Add import at top:
```python
from pet.ui.settings_window import SettingsWindow
```

In `_show_menu()`, before the `quit_action` lines, add:
```python
        # 设置入口
        settings_action = QAction("⚙ 设置", menu)
        settings_action.triggered.connect(lambda: SettingsWindow.show_instance(self._agent, self.pet))
        menu.addAction(settings_action)
        menu.addSeparator()
```

Also add `self._agent = None` in `__init__` and a `set_agent` method:
```python
    def set_agent(self, agent):
        self._agent = agent
```

- [ ] **Step 2: Wire in `main.py`**

After `tray = SystemTrayManager(app, window)` and `agent.notify_requested.connect(...)`, add:

```python
    tray.set_agent(agent)
```

In `_shutdown()`, add before `agent.stop()`:
```python
        # 清理设置窗口
        try:
            from pet.ui.settings_window import SettingsWindow
            if SettingsWindow._instance:
                SettingsWindow._instance.close()
        except Exception:
            pass
```

- [ ] **Step 3: Commit**

```bash
git add pet/ui/system_tray.py main.py
git commit -m "feat(settings): add tray menu entry and lifecycle wiring"
```

---

### Task 7: Smoke test and final verification

**Files:**
- No new files; verify all pieces work together

**What to verify:**
1. Application starts without errors
2. Tray menu shows "⚙ 设置" item
3. Settings window opens, all 4 tabs render correctly
4. Values are populated from current `config` state
5. Saving a connection setting (e.g., LLM_TIMEOUT) writes to `settings.json` and updates `config`
6. Resetting a tab clears `settings.json` entries and reverts to `.env` defaults
7. LLM connectivity test works from settings window (runs in background thread)
8. Runtime update hooks work: changing a scheduler interval updates timers without restart

- [ ] **Step 1: Run the application and verify each checklist item**

```bash
python main.py
```

- [ ] **Step 2: Verify settings.json is written correctly**

After changing a setting, check:
- Windows: `%APPDATA%\DeskPet\settings.json`
- macOS: `~/Library/Application Support/DeskPet/settings.json`

- [ ] **Step 3: Commit any fixups**

```bash
git add -A
git commit -m "feat(settings): final integration fixes"
```