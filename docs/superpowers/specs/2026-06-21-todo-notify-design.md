# todo 操作触发 Windows 通知 设计文档

日期: 2026-06-21
状态: design-approved

---

## 概述

LLM 完成 todo 记录时（添加、完成），通过 Windows 原生通知（托盘气泡）向用户确认操作结果。

---

## 一、通知基础设施（SkillContext + PetAgent）

遵循现有 `speech()` / `action()` 模式——技能不直接碰 UI，通过 `SKILL_CTX` → PetAgent 信号 → 主线程处理。

### 1.1 PetAgent 新增信号

文件: `pet/agent/pet_agent.py` — 在现有 signal 声明后加一行：

```python
notify_requested = Signal(str, str, int)  # title, message, duration_ms
```

### 1.2 SkillContext 新增方法

文件: `pet/skills/context.py` — 在现有方法后添加：

```python
def notify(self, title: str, message: str, duration: int = 5000):
    """弹出 Windows 托盘通知。"""
    if self._check_agent():
        self._agent.notify_requested.emit(title, message, duration)
```

### 1.3 main.py 连接信号

文件: `main.py` — 在现有信号连接区域添加（约 line 130 附近）：

```python
agent.notify_requested.connect(
    lambda t, m, d: tray.tray_icon.showMessage(t, m, QSystemTrayIcon.MessageIcon.Information, d)
    if tray.tray_icon else None
)
```

需在文件顶部添加导入：
```python
from PySide6.QtWidgets import QSystemTrayIcon
```

---

## 二、todo 技能接入

### 2.1 包装 handler

文件: `pet/skills/plugins/todo/__init__.py`

添加两个包装函数，在 add / complete 成功后调用 `SKILL_CTX.notify()`：

```python
def _add_with_notify(title: str) -> dict:
    result = _instance.add(title=title)
    if "error" not in result:
        SKILL_CTX.notify("待办已添加", title.strip())
    return result

def _complete_with_notify(todo_id: int) -> dict:
    result = _instance.toggle(todo_id)
    if "error" not in result:
        item = result.get("item", {})
        label = "已完成" if item.get("status") == "done" else "已恢复"
        SKILL_CTX.notify(f"待办{label}", item.get("title", ""))
    return result
```

add handler 改为 `_add_with_notify`，complete handler 改为 `_complete_with_notify`。

---

## 三、改动清单

| 文件 | 操作 | 改动量 |
|------|------|--------|
| `pet/agent/pet_agent.py` | 加 1 行 signal | +1 |
| `pet/skills/context.py` | 加 `notify()` 方法 | +5 |
| `main.py` | 加 import + 信号连接 | +5 |
| `pet/skills/plugins/todo/__init__.py` | 加包装函数，替换 handler | +12/-2 |

4 个文件，总增量约 20 行。

---

## 四、范围边界

**本次包含：**
- notify 基础设施（SkillContext + PetAgent signal + main.py 连线）
- todo 的 add 和 complete 操作接入通知

**本次不包含：**
- 其他技能接入通知（后续按需添加）
- 通知持久化 / 历史记录
- 自定义通知图标
