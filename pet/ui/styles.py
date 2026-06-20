"""共享 QSS 样式库 —— 扁平化圆角风格。"""

# ── 色彩 ──

_COLOR_BG         = "#f0f0f0"
_COLOR_SURFACE     = "#ffffff"
_COLOR_BORDER      = "#ddd"
_COLOR_BORDER_FOCUS = "#aaa"
_COLOR_TEXT        = "#333"
_COLOR_TEXT_SEC    = "#666"
_COLOR_ACCENT      = "#4a90d9"

# ── 窗口 / 根 ──

WINDOW_QSS = """
QWidget#FlatWindow {
    background: """ + _COLOR_BG + """;
}
"""

# ── 面板 ──

PANEL_QSS = """
QGroupBox {
    font-size: 12px;
    font-weight: bold;
    color: """ + _COLOR_TEXT_SEC + """;
    background: transparent;
    border: 1px solid """ + _COLOR_BORDER + """;
    border-radius: 8px;
    margin-top: 10px;
    padding: 14px 8px 8px 8px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: """ + _COLOR_TEXT_SEC + """;
}
"""

# ── 按钮通用 ──

_BTN_BASE = """
    background: """ + _COLOR_SURFACE + """;
    border: 1px solid """ + _COLOR_BORDER + """;
    border-radius: 6px;
    padding: 4px 12px;
    font-size: 12px;
    color: """ + _COLOR_TEXT + """;
"""

BUTTON_QSS = """
QPushButton {
""" + _BTN_BASE + """
}
QPushButton:hover {
    background: #e8e8e8;
    border-color: """ + _COLOR_BORDER_FOCUS + """;
}
QPushButton:pressed {
    background: #d8d8d8;
}
QPushButton:checked {
    background: """ + _COLOR_ACCENT + """;
    color: #fff;
    border-color: """ + _COLOR_ACCENT + """;
}
"""

BUTTON_PRIMARY_QSS = """
QPushButton {
""" + _BTN_BASE + """
    background: """ + _COLOR_ACCENT + """;
    color: #fff;
    border-color: """ + _COLOR_ACCENT + """;
}
QPushButton:hover {
    background: #3a7bc8;
}
QPushButton:pressed {
    background: #2d6ab5;
}
"""

# ── 按钮 - 危险/关闭 ──

BUTTON_DANGER_QSS = """
QPushButton {
    background: transparent;
    border: none;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 14px;
    color: #888;
}
QPushButton:hover {
    background: #e81123;
    color: #fff;
}
"""

# ── 输入框 ──

INPUT_QSS = """
QLineEdit, QSpinBox {
    background: """ + _COLOR_SURFACE + """;
    border: 1px solid """ + _COLOR_BORDER + """;
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 12px;
    color: """ + _COLOR_TEXT + """;
}
QLineEdit:focus, QSpinBox:focus {
    border-color: """ + _COLOR_BORDER_FOCUS + """;
}
"""

# ── 下拉框 ──

COMBOBOX_QSS = """
QComboBox {
    background: """ + _COLOR_SURFACE + """;
    border: 1px solid """ + _COLOR_BORDER + """;
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 12px;
    color: """ + _COLOR_TEXT + """;
    min-width: 64px;
}
QComboBox:hover {
    border-color: """ + _COLOR_BORDER_FOCUS + """;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: right center;
    width: 16px;
    border: none;
}
QComboBox QAbstractItemView {
    background: """ + _COLOR_SURFACE + """;
    border: 1px solid """ + _COLOR_BORDER + """;
    border-radius: 4px;
    selection-background-color: #e0e0e0;
    color: """ + _COLOR_TEXT + """;
    font-size: 12px;
    outline: none;
}
"""

# ── 多行文本框 ──

TEXTEDIT_QSS = """
QTextEdit, QPlainTextEdit {
    background: """ + _COLOR_SURFACE + """;
    border: 1px solid """ + _COLOR_BORDER + """;
    border-radius: 8px;
    padding: 6px 8px;
    font-family: "Consolas", "Microsoft YaHei", monospace;
    font-size: 12px;
    color: """ + _COLOR_TEXT + """;
    selection-background-color: #b3d9ff;
}
QTextEdit:focus, QPlainTextEdit:focus {
    border-color: """ + _COLOR_BORDER_FOCUS + """;
}
"""

# ── 列表 ──

LIST_QSS = """
QListWidget {
    background: """ + _COLOR_SURFACE + """;
    border: 1px solid """ + _COLOR_BORDER + """;
    border-radius: 6px;
    font-family: "Consolas", "Microsoft YaHei", monospace;
    font-size: 11px;
    color: """ + _COLOR_TEXT + """;
    outline: none;
}
QListWidget::item {
    padding: 2px 4px;
}
QListWidget::item:selected {
    background: #e0e0e0;
    color: """ + _COLOR_TEXT + """;
}
"""

# ── 菜单 ──

MENU_QSS = """
QMenu {
    background: """ + _COLOR_SURFACE + """;
    border: 1px solid """ + _COLOR_BORDER + """;
    border-radius: 8px;
    padding: 4px;
}
QMenu::item {
    padding: 6px 28px 6px 12px;
    font-size: 13px;
    color: """ + _COLOR_TEXT + """;
    border-radius: 4px;
}
QMenu::item:selected {
    background: #e8e8e8;
}
QMenu::separator {
    height: 1px;
    background: """ + _COLOR_BORDER + """;
    margin: 3px 8px;
}
"""

# ── 复选框 ──

CHECKBOX_QSS = """
QCheckBox {
    font-size: 12px;
    color: """ + _COLOR_TEXT + """;
    spacing: 6px;
}
"""

# ── 标签 ──

LABEL_SECONDARY_QSS = """
    font-size: 12px;
    color: """ + _COLOR_TEXT_SEC + """;
"""

LABEL_MONO_QSS = """
    font-family: "Consolas", "Microsoft YaHei", monospace;
    font-size: 12px;
    color: """ + _COLOR_TEXT + """;
"""

# ── 水平分隔线 ──

SEPARATOR_QSS = """
QFrame[frameShape="4"] {
    color: """ + _COLOR_BORDER + """;
}
"""
