"""todo 技能专属样式 — 独立副本，不依赖主应用样式模块。"""

_COLOR_BG = "#f0f0f0"
_COLOR_SURFACE = "#ffffff"
_COLOR_BORDER = "#ddd"
_COLOR_BORDER_FOCUS = "#aaa"
_COLOR_TEXT = "#333"
_COLOR_TEXT_SEC = "#666"
_COLOR_ACCENT = "#4a90d9"

BUTTON_QSS = """
QPushButton {
    background: """ + _COLOR_SURFACE + """;
    border: 1px solid """ + _COLOR_BORDER + """;
    border-radius: 6px;
    padding: 4px 12px;
    font-size: 12px;
    color: """ + _COLOR_TEXT + """;
    min-width: 64px;
}
QPushButton:hover {
    background: #e8e8e8;
    border-color: """ + _COLOR_BORDER_FOCUS + """;
}
QPushButton:pressed {
    background: #d8d8d8;
}
"""

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
    padding: 6px 8px;
    border-bottom: 1px solid """ + _COLOR_BORDER + """;
}
QListWidget::item:selected {
    background: #e0e0e0;
    color: """ + _COLOR_TEXT + """;
}
"""
