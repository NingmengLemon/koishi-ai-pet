# todo 操作触发 Windows 通知 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** LLM 完成 todo 记录（添加、完成）时弹出 Windows 托盘通知确认操作。

**Architecture:** 遵循现有 `speech()` / `action()` 模式 — 技能通过 `SKILL_CTX.notify()` → `PetAgent.notify_requested` 信号 → `main.py` 连接 `SystemTrayIcon.showMessage()`。

**Tech Stack:** Python 3.x, PySide6 QSystemTrayIcon

**Spec:** [2026-06-21-todo-notify-design.md](../specs/2026-06-21-todo-notify-design.md)

## Global Constraints

- 技能 handler 不直接碰 UI，通过 SKILL_CTX 信号机制
- notify() 仅在 agent 已绑定时生效（与 speech/action 一致）
- 通知持续 5000ms

---

## File Structure

```
# 修改的文件：
pet/agent/pet_agent.py              — +1 行 signal
pet/skills/context.py               — +notify() 方法 (~5 行)
main.py                             — +import + 信号连接 (~5 行)
pet/skills/plugins/todo/__init__.py — +包装函数，替换 handler (~+12/-2)
```

---

### Task 1: 通知基础设施 — PetAgent signal + SkillContext + main.py

**Files:**
- Modify: `pet/agent/pet_agent.py:54`
- Modify: `pet/skills/context.py`
- Modify: `main.py:130`

**Interfaces:**
- Produces: `PetAgent.notify_requested = Signal(str, str, int)` — title, message, duration_ms
- Produces: `SKILL_CTX.notify(title: str, message: str, duration: int = 5000) -> None`
- Consumes: `SystemTrayManager.tray_icon` in main.py

- [ ] **Step 1: PetAgent 添加 notify_requested signal**

在 `pet/agent/pet_agent.py` 第 54 行（`speak_stream_end` 之后）添加一行：

```python
    notify_requested = Signal(str, str, int)  # title, message, duration_ms
```

Edit 操作：在 `speak_stream_end   = Signal(int)` 后插入新行。

- [ ] **Step 2: SkillContext 添加 notify 方法**

在 `pet/skills/context.py` 的 `request_interact` 方法之后（约 line 57 后），`register_tick` 方法之前，添加：

```python
    def notify(self, title: str, message: str, duration: int = 5000):
        """弹出 Windows 托盘通知。"""
        if self._check_agent():
            self._agent.notify_requested.emit(title, message, duration)
```

- [ ] **Step 3: main.py 连接信号**

在 `main.py` 顶部添加导入 `QSystemTrayIcon`。将第 5 行：

```python
from PySide6.QtWidgets import QApplication
```

改为：

```python
from PySide6.QtWidgets import QApplication, QSystemTrayIcon
```

在 `main.py` 中 `agent.speak_stream_end.connect` 之后（约 line 129 之后）添加：

```python
    agent.notify_requested.connect(
        lambda t, m, d: tray.tray_icon.showMessage(t, m, QSystemTrayIcon.MessageIcon.Information, d)
        if tray.tray_icon else None
    )
```

- [ ] **Step 4: 验证基础设施**

```bash
cd d:/Source/github/DeskPet && python -c "
from PySide6.QtWidgets import QApplication, QSystemTrayIcon
import sys
app = QApplication(sys.argv)

from pet.agent.pet_agent import PetAgent
from pet.skills.context import SKILL_CTX

# 验证 signal 存在
assert hasattr(PetAgent, 'notify_requested')
print('PASS: PetAgent.notify_requested signal exists')

# 验证 SKILL_CTX.notify 方法存在
assert hasattr(SKILL_CTX, 'notify')
print('PASS: SKILL_CTX.notify method exists')

# 验证无 agent 绑定时 notify 不崩溃
SKILL_CTX.notify('test', 'hello')
print('PASS: notify no-op without agent bound')
"
```

- [ ] **Step 5: Commit**

```bash
git add pet/agent/pet_agent.py pet/skills/context.py main.py
git commit -m "feat(notify): add notify infrastructure — SKILL_CTX.notify → tray showMessage"
```

---

### Task 2: todo 技能接入通知

**Files:**
- Modify: `pet/skills/plugins/todo/__init__.py`

**Interfaces:**
- Consumes: `SKILL_CTX.notify(title, message)` from Task 1
- Consumes: `_instance.add(title)`, `_instance.toggle(todo_id)` from TodoListTool
- Produces: `_add_with_notify(title) -> dict`, `_complete_with_notify(todo_id) -> dict`

- [ ] **Step 1: 添加包装函数并替换 handler**

在 `pet/skills/plugins/todo/__init__.py` 中 `_show_panel` 函数之后、`register` 函数之前，添加两个包装函数：

```python
def _add_with_notify(title: str) -> dict:
    """添加待办 + Windows 通知。"""
    result = _instance.add(title=title)
    if "error" not in result:
        SKILL_CTX.notify("待办已添加", title.strip())
    return result


def _complete_with_notify(todo_id: int) -> dict:
    """切换完成状态 + Windows 通知。"""
    result = _instance.toggle(todo_id)
    if "error" not in result:
        item = result.get("item", {})
        label = "已完成" if item.get("status") == "done" else "已恢复"
        SKILL_CTX.notify(f"待办{label}", item.get("title", ""))
    return result
```

然后将 `register` 函数中：

- `handler=_instance.add` → `handler=_add_with_notify`
- `handler=_instance.toggle` → `handler=_complete_with_notify`

- [ ] **Step 2: 验证 todo 注册和导入**

```bash
cd d:/Source/github/DeskPet && python -c "
from pet.skills.registry import SKILL_REGISTRY
from pet.skills.plugins.todo import register, _add_with_notify, _complete_with_notify

# 验证包装函数存在
assert callable(_add_with_notify)
assert callable(_complete_with_notify)
print('PASS: wrapper functions exist')

# 验证注册
SKILL_REGISTRY._skills.pop('todo', None)
register(SKILL_REGISTRY)
skill = SKILL_REGISTRY._skills['todo']

# add handler 是 _add_with_notify
assert skill.methods['add'].handler.__name__ == '_add_with_notify'
print(f'PASS: add handler = {skill.methods[\"add\"].handler.__name__}')

# complete handler 是 _complete_with_notify
assert skill.methods['complete'].handler.__name__ == '_complete_with_notify'
print(f'PASS: complete handler = {skill.methods[\"complete\"].handler.__name__}')

print('ALL PASS')
"
```

- [ ] **Step 3: Commit**

```bash
git add pet/skills/plugins/todo/__init__.py
git commit -m "feat(todo): wire add/complete to Windows tray notification"
```

---

## 自检完成

2 个任务覆盖所有 spec 需求。无占位符，无 TBD，所有代码步骤完整可执行。
