# todo 技能简化 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 精简 todo 技能到极简待办清单——只保留 title + status(pending/done)，去掉 due_date/priority/category/notes 及整套提醒系统。

**Architecture:** 自底向上：先改 storage schema，再改 core，然后改 __init__ 注册，最后改 panel UI。删除 reminder.py 和 parser.py。

**Tech Stack:** Python 3.x, SQLite (pet.db), PySide6

**Spec:** [2026-06-21-todo-simplify-design.md](../specs/2026-06-21-todo-simplify-design.md)

## Global Constraints

- 所有 SQLite 操作使用 `threading.Lock`
- 插件 handler 返回 dict 含 `summary` 键
- `complete()` 改为 `toggle()`，支持 pending ↔ done 双向切换
- 旧 `todos` 表直接 DROP 重建，无需迁移

---

## File Structure

```
# 修改的文件：
pet/skills/plugins/todo/storage.py      — 新 schema + 精简方法
pet/skills/plugins/todo/core.py         — 删 check_due，精简参数，complete→toggle
pet/skills/plugins/todo/__init__.py     — 删 reminder 代码，精简 args，方法改名
pet/skills/plugins/todo/panel.py        — 删筛选栏，简化列表项和对话框

# 删除的文件：
pet/skills/plugins/todo/reminder.py     — 提醒系统整体移除
pet/skills/plugins/todo/parser.py       — 日期解析不再需要
```

---

### Task 1: storage.py — 新 schema + 精简方法

**Files:**
- Modify: `pet/skills/plugins/todo/storage.py`

**Interfaces:**
- Produces: `TodoStorage` class
  - `__init__(db_path: str = None)`
  - `add(title: str) -> dict`
  - `list(status: str | None = None) -> list[dict]`
  - `toggle(id: int) -> dict | None`
  - `update(id: int, title: str) -> dict | None`
  - `delete(id: int) -> bool`
  - `close()`

- [ ] **Step 1: 用新内容覆盖 storage.py**

用以下内容覆盖 `pet/skills/plugins/todo/storage.py`：

```python
"""Todo 持久化存储 — SQLite 数据层。"""

from __future__ import annotations

import sqlite3
import threading
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_DB = str(Path(__file__).resolve().parent.parent.parent.parent.parent / "pet.db")


class TodoStorage:
    def __init__(self, db_path: str | None = None):
        self._db_path = db_path or _DEFAULT_DB
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._create_table()

    def _create_table(self):
        with self._lock:
            self._conn.execute("DROP TABLE IF EXISTS todos")
            self._conn.execute("""
                CREATE TABLE todos (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    title      TEXT NOT NULL,
                    status     TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL
                )
            """)
            self._conn.commit()

    def add(self, title: str) -> dict:
        """添加任务，返回完整行 dict。"""
        now = datetime.now().isoformat()
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO todos (title, created_at) VALUES (?, ?)",
                (title.strip(), now))
            self._conn.commit()
            row = self._conn.execute(
                "SELECT * FROM todos WHERE id = ?", (cur.lastrowid,)
            ).fetchone()
            return dict(row) if row else {}

    def list(self, status: str | None = None) -> list[dict]:
        """查询任务列表。status=None 时返回全部。"""
        with self._lock:
            if status is not None:
                rows = self._conn.execute(
                    "SELECT * FROM todos WHERE status=? ORDER BY created_at DESC",
                    (status,)
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM todos ORDER BY created_at DESC"
                ).fetchall()
        return [dict(r) for r in rows]

    def toggle(self, todo_id: int) -> dict | None:
        """切换任务完成状态 pending ↔ done。"""
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM todos WHERE id=?", (todo_id,)
            ).fetchone()
            if not row:
                return None
            new_status = "done" if row["status"] == "pending" else "pending"
            self._conn.execute(
                "UPDATE todos SET status=? WHERE id=?", (new_status, todo_id))
            self._conn.commit()
            row = self._conn.execute(
                "SELECT * FROM todos WHERE id=?", (todo_id,)
            ).fetchone()
        return dict(row) if row else None

    def update(self, todo_id: int, title: str) -> dict | None:
        """修改任务标题。"""
        if not title.strip():
            return None
        with self._lock:
            self._conn.execute(
                "UPDATE todos SET title=? WHERE id=?", (title.strip(), todo_id))
            self._conn.commit()
            row = self._conn.execute(
                "SELECT * FROM todos WHERE id=?", (todo_id,)
            ).fetchone()
        return dict(row) if row else None

    def delete(self, todo_id: int) -> bool:
        """删除任务。返回是否成功。"""
        with self._lock:
            cur = self._conn.execute("DELETE FROM todos WHERE id=?", (todo_id,))
            self._conn.commit()
        return cur.rowcount > 0

    def close(self):
        with self._lock:
            self._conn.close()
```

- [ ] **Step 2: 验证 storage.py**

```bash
cd d:/Source/github/DeskPet && python -c "
from pet.skills.plugins.todo.storage import TodoStorage
import tempfile, os

db = tempfile.mktemp(suffix='.db')
s = TodoStorage(db)

# add
t = s.add('测试任务')
assert t['id'] == 1 and t['title'] == '测试任务' and t['status'] == 'pending'
print(f'PASS add: {t}')

# list
items = s.list()
assert len(items) == 1
items_done = s.list('done')
assert len(items_done) == 0
print(f'PASS list: {len(items)} pending, {len(items_done)} done')

# toggle → done
t2 = s.toggle(1)
assert t2['status'] == 'done', f'expected done, got {t2[\"status\"]}'
print(f'PASS toggle to done: {t2}')

# toggle → pending
t3 = s.toggle(1)
assert t3['status'] == 'pending', f'expected pending, got {t3[\"status\"]}'
print(f'PASS toggle to pending: {t3}')

# update
u = s.update(1, '改名了')
assert u['title'] == '改名了'
print(f'PASS update: {u}')

# delete
assert s.delete(1)
assert s.list() == []
print('PASS delete')

s.close()
os.unlink(db)
print('ALL PASS')
"
```

- [ ] **Step 3: Commit**

```bash
git add pet/skills/plugins/todo/storage.py
git commit -m "refactor(todo): simplify storage schema — title + status only, complete→toggle"
```

---

### Task 2: core.py — 删 check_due，精简参数，complete→toggle

**Files:**
- Modify: `pet/skills/plugins/todo/core.py`

**Interfaces:**
- Consumes: `TodoStorage` from Task 1
- Produces: `TodoListTool` class
  - `add(title) -> dict`
  - `list_todos(status="pending") -> dict`
  - `toggle(id) -> dict`
  - `delete(id) -> dict`
  - `update(id, title) -> dict`

- [ ] **Step 1: 用新内容覆盖 core.py**

用以下内容覆盖 `pet/skills/plugins/todo/core.py`：

```python
"""TodoList 核心处理逻辑 — LLM 可见方法实现。"""

import logging

from pet.skills.plugins.todo.storage import TodoStorage

logger = logging.getLogger(__name__)


class TodoListTool:
    def __init__(self):
        self._storage = TodoStorage()

    def add(self, title: str) -> dict:
        """添加待办事项。"""
        if not title or not title.strip():
            return {"error": "标题不能为空"}
        todo = self._storage.add(title=title.strip())
        return {
            **todo,
            "summary": f"已添加待办: #{todo['id']}「{todo['title']}」",
        }

    def list_todos(self, status: str = "pending") -> dict:
        """查询任务列表。"""
        items = self._storage.list(status=None if status == "all" else status)
        if not items:
            return {"summary": "没有待办事项。", "items": []}
        lines = [f"共 {len(items)} 条："]
        for t in items:
            mark = "✓" if t["status"] == "done" else "○"
            lines.append(f"  #{t['id']} {mark} {t['title']}")
        return {"summary": "\n".join(lines), "items": items}

    def toggle(self, todo_id: int) -> dict:
        """切换任务完成状态。「帮我完成/恢复 #3」→ 切换 pending↔done。"""
        result = self._storage.toggle(todo_id)
        if result is None:
            return {"error": f"未找到 id={todo_id} 的任务"}
        label = "已完成" if result["status"] == "done" else "已恢复为待办"
        return {
            "summary": f"{label}: #{todo_id}「{result['title']}」",
            "item": result,
        }

    def delete(self, todo_id: int) -> dict:
        """删除待办事项。"""
        ok = self._storage.delete(todo_id)
        if not ok:
            return {"error": f"未找到 id={todo_id} 的任务或删除失败"}
        return {"summary": f"已删除任务 #{todo_id}"}

    def update(self, todo_id: int, title: str = "") -> dict:
        """修改待办标题。"""
        if not title or not title.strip():
            return {"error": "标题不能为空"}
        result = self._storage.update(todo_id, title.strip())
        if result is None:
            return {"error": f"未找到 id={todo_id} 的任务"}
        return {
            "summary": f"已更新 #{todo_id}「{result['title']}」",
            "item": result,
        }

    def close(self):
        self._storage.close()
```

- [ ] **Step 2: 验证 core.py**

```bash
cd d:/Source/github/DeskPet && python -c "
from pet.skills.plugins.todo.core import TodoListTool
import tempfile, os

# 使用独立 db 避免污染 pet.db
db = tempfile.mktemp(suffix='.db')
t = TodoListTool()
t._storage._conn.close()
# 重新指向 temp db
from pet.skills.plugins.todo.storage import TodoStorage
t._storage = TodoStorage(db)

# add
r = t.add('买牛奶')
assert '#1' in r['summary'], f'add failed: {r}'
print(f'PASS add: {r[\"summary\"]}')

# list
r = t.list_todos()
assert len(r['items']) == 1
print(f'PASS list: {r[\"summary\"]}')

# toggle → done
r = t.toggle(1)
assert '已完成' in r['summary'], f'toggle failed: {r}'
print(f'PASS toggle done: {r[\"summary\"]}')

# toggle → pending
r = t.toggle(1)
assert '已恢复' in r['summary'], f'toggle back failed: {r}'
print(f'PASS toggle pending: {r[\"summary\"]}')

# update
r = t.update(1, '改名了')
assert '改名了' in r['summary']
print(f'PASS update: {r[\"summary\"]}')

# delete
r = t.delete(1)
assert '已删除' in r['summary']
print(f'PASS delete: {r[\"summary\"]}')

t.close()
os.unlink(db)
print('ALL PASS')
"
```

- [ ] **Step 3: Commit**

```bash
git add pet/skills/plugins/todo/core.py
git commit -m "refactor(todo): simplify core — remove check_due, complete→toggle, reduce params"
```

---

### Task 3: \_\_init\_\_.py — 删 reminder 代码，精简 args

**Files:**
- Modify: `pet/skills/plugins/todo/__init__.py`

**Interfaces:**
- Consumes: `TodoListTool` from Task 2, `SKILL_CTX`, `SKILL_REGISTRY`
- Produces: `SKILL_NAME`, `SKILL_DESCRIPTION`, `register(registry)` — 简化的注册入口

- [ ] **Step 1: 用新内容覆盖 \_\_init\_\_.py**

用以下内容覆盖 `pet/skills/plugins/todo/__init__.py`：

```python
"""todo 技能 — 极简单代办事项管理。
支持添加/查看/完成/删除任务。
"""

from __future__ import annotations

import logging

from pet.skills.plugins.todo.core import TodoListTool
from pet.skills.context import SKILL_CTX

logger = logging.getLogger(__name__)

SKILL_NAME = "todo"
SKILL_DESCRIPTION = "待办事项管理。支持添加、查看、完成、删除任务。"

try:
    _instance = TodoListTool()
except Exception as e:
    logger.error(f"[todo] Failed to initialize TodoListTool: {e}")
    _instance = None

# 持有面板引用防 GC 回收
_panel = None


def _show_panel():
    """右键菜单「查看待办」回调 — 弹出任务管理面板。"""
    global _panel
    from pet.skills.plugins.todo.panel import TodoPanel

    if _panel is not None:
        try:
            alive = _panel.isVisible()
        except RuntimeError:
            alive = False
        if not alive:
            _panel.deleteLater()
            _panel = None

    if _panel is None:
        _panel = TodoPanel()

    _panel.show()
    _panel.raise_()


def register(registry):
    if _instance is None:
        logger.error("[todo] Skipping registration — TodoListTool init failed")
        return
    skill = registry.register(SKILL_NAME, SKILL_DESCRIPTION)
    skill.when = "用户需要管理待办事项、记录任务、或查看任务列表时"

    # ── LLM 方法 ──

    registry.add_method(
        SKILL_NAME, "add",
        "添加新待办事项",
        handler=_instance.add,
        when="用户说「帮我记一个待办」「添加任务」时",
        args={
            "title": {"type": "str", "required": True, "desc": "任务标题"},
        },
    )

    registry.add_method(
        SKILL_NAME, "list",
        "查询任务列表",
        handler=_instance.list_todos,
        when="用户问「待办有什么」「任务列表」「我还有哪些没做」时",
        args={
            "status": {"type": "str", "required": False, "default": "pending",
                       "desc": "状态: pending/done/all"},
        },
    )

    registry.add_method(
        SKILL_NAME, "complete",
        "切换任务完成状态（已完成↔恢复待办）",
        handler=_instance.toggle,
        when="用户说「完成了」「做完了」「恢复这个任务」时",
        args={
            "id": {"type": "int", "required": True, "desc": "任务ID"},
        },
    )

    registry.add_method(
        SKILL_NAME, "delete",
        "删除指定任务",
        handler=_instance.delete,
        when="用户说「删除任务」「取消这个待办」时",
        args={
            "id": {"type": "int", "required": True, "desc": "任务ID"},
        },
    )

    registry.add_method(
        SKILL_NAME, "update",
        "修改已有任务的标题",
        handler=_instance.update,
        when="用户说「修改待办」「把xxx改成」时",
        args={
            "id": {"type": "int", "required": True, "desc": "任务ID"},
            "title": {"type": "str", "required": True, "desc": "新标题"},
        },
    )

    # ── 右键菜单 ──

    registry.add_menu_action(SKILL_NAME, "查看待办", _show_panel)

    # ── 面板注册 ──

    SKILL_CTX.register_panel(SKILL_NAME, _show_panel)

    logger.info("[todo] skill registered")
```

- [ ] **Step 2: 验证注册逻辑**

```bash
cd d:/Source/github/DeskPet && python -c "
from pet.skills.registry import SKILL_REGISTRY
from pet.skills.plugins.todo import register

# 清空可能的旧注册
SKILL_REGISTRY._skills.pop('todo', None)

register(SKILL_REGISTRY)

skill = SKILL_REGISTRY._skills['todo']
print(f'SKILL_NAME: todo')
print(f'Methods: {list(skill.methods.keys())}')
print(f'Menu items: {[m[\"label\"] for m in skill.menu_items]}')

# 验证 5 个方法
assert set(skill.methods.keys()) == {'add', 'list', 'complete', 'delete', 'update'}
for name, m in skill.methods.items():
    assert callable(m.handler), f'{name} handler not callable'
    print(f'  ✓ {name}({list(m.args.keys())})')

# 验证 add 只有 title 参数
assert list(skill.methods['add'].args.keys()) == ['title']
# 验证 update 只有 id + title
assert list(skill.methods['update'].args.keys()) == ['id', 'title']

assert len(skill.menu_items) == 1
print('ALL PASS: todo registered successfully')
"
```

- [ ] **Step 3: Commit**

```bash
git add pet/skills/plugins/todo/__init__.py
git commit -m "refactor(todo): simplify init — remove reminder wiring, reduce method args"
```

---

### Task 4: panel.py — 删筛选栏，简化列表项和对话框

**Files:**
- Modify: `pet/skills/plugins/todo/panel.py`

**Interfaces:**
- Consumes: `_instance` from `pet.skills.plugins.todo` (TodoListTool)
- Produces: `TodoPanel(QWidget)` — 简化面板：标题栏 + 列表 + 操作按钮 + 统计

- [ ] **Step 1: 用新内容覆盖 panel.py**

用以下内容覆盖 `pet/skills/plugins/todo/panel.py`：

```python
"""Todo 管理面板 — 无边框圆角窗口。"""

from __future__ import annotations

import logging

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QMessageBox,
    QDialog, QLineEdit, QFormLayout, QDialogButtonBox,
)
from PySide6.QtCore import Qt, QPoint

from pet.skills.plugins.todo import _instance as _todo_instance
from pet.skills.plugins.todo.style import LIST_QSS, BUTTON_QSS

logger = logging.getLogger(__name__)

_W = 420
_H = 520


class TodoPanel(QWidget):
    """任务管理面板 — 无边框圆角窗口，标题栏可拖动。"""

    def __init__(self):
        super().__init__()
        self._core = _todo_instance
        self._storage = self._core._storage
        self._drag_pos: QPoint | None = None

        self.setObjectName("todoPanel")
        self.setWindowTitle("待办事项")
        self.resize(_W, _H)
        self.setFixedSize(_W, _H)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._setup_ui()
        self._refresh()

    # ── UI ──

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 背景容器
        bg = QWidget()
        bg.setObjectName("todoBg")
        bg.setStyleSheet("""
            QWidget#todoBg {
                background: #f0f0f0;
                border-radius: 8px;
                font-size: 12px;
            }
        """)
        layout = QVBoxLayout(bg)
        layout.setContentsMargins(16, 0, 16, 16)
        layout.setSpacing(8)
        root.addWidget(bg)

        # ── 标题栏（可拖动区域） ──
        title_bar = QWidget()
        title_bar.setFixedHeight(40)
        title_row = QHBoxLayout(title_bar)
        title_row.setContentsMargins(0, 0, 0, 0)

        title = QLabel("📋 待办事项")
        title.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #333;"
        )
        title_row.addWidget(title)
        title_row.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(28, 28)
        btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 14px;
                font-size: 14px;
                color: #999;
            }
            QPushButton:hover {
                background: #e81123;
                color: #fff;
            }
        """)
        btn_close.clicked.connect(self.close)
        title_row.addWidget(btn_close)

        layout.addWidget(title_bar)

        # ── 任务列表 ──
        self._list = QListWidget()
        self._list.setStyleSheet(LIST_QSS)
        self._list.setFrameShape(QListWidget.Shape.NoFrame)
        self._list.setAlternatingRowColors(True)
        layout.addWidget(self._list, stretch=1)

        # ── 操作按钮 ──
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        for text, handler, extra_qss in [
            ("➕ 添加", self._on_add, """
                QPushButton:hover {
                    background: #4a90d9;
                    border-color: #4a90d9;
                    color: #fff;
                }
            """),
            ("✓ 完成", self._on_toggle, """
                QPushButton:hover {
                    background: #27ae60;
                    border-color: #27ae60;
                    color: #fff;
                }
            """),
            ("✗ 删除", self._on_delete, """
                QPushButton:hover {
                    background: #e74c3c;
                    border-color: #e74c3c;
                    color: #fff;
                }
            """),
        ]:
            btn = QPushButton(text)
            btn.setStyleSheet(BUTTON_QSS + extra_qss)
            btn.clicked.connect(handler)
            btn_row.addWidget(btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        # ── 底部统计 ──
        self._stats = QLabel("")
        self._stats.setStyleSheet("font-size: 11px; color: #666;")
        layout.addWidget(self._stats)

    # ── 窗口拖动 ──

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.move(self.pos() + delta)
            self._drag_pos = event.globalPosition().toPoint()
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        event.accept()

    # ── 数据 ──

    def _refresh(self):
        items = self._storage.list()
        self._list.clear()
        for t in items:
            if t["status"] == "done":
                text = f"  ✅  ~~{t['title']}~~"
            else:
                text = f"  ○  {t['title']}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, t["id"])
            self._list.addItem(item)
        done_count = sum(1 for t in items if t["status"] == "done")
        self._stats.setText(f"共 {len(items)} 条，{done_count} 已完成")

    def _current_id(self) -> int | None:
        item = self._list.currentItem()
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None

    def _on_add(self):
        """弹出标题对话框添加待办。"""
        dlg = QDialog(self)
        dlg.setWindowTitle("添加待办")
        dlg.resize(320, 100)
        form = QFormLayout(dlg)
        form.setSpacing(10)

        edt_title = QLineEdit()
        edt_title.setPlaceholderText("输入任务标题")
        form.addRow("标题:", edt_title)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(dlg.accept)
        btn_box.rejected.connect(dlg.reject)
        form.addRow(btn_box)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        title = edt_title.text().strip()
        if not title:
            return

        self._storage.add(title=title)
        self._refresh()

    def _on_toggle(self):
        tid = self._current_id()
        if tid is None:
            return
        self._storage.toggle(tid)
        self._refresh()

    def _on_delete(self):
        tid = self._current_id()
        if tid is None:
            return
        reply = QMessageBox.question(
            self, "确认删除", "确定要删除这个任务吗？")
        if reply == QMessageBox.StandardButton.Yes:
            self._storage.delete(tid)
            self._refresh()
```

- [ ] **Step 2: 验证 panel 语法**

```bash
cd d:/Source/github/DeskPet && python -c "
from pet.skills.plugins.todo.panel import TodoPanel
print('PASS: TodoPanel imported successfully')
"
```

- [ ] **Step 3: Commit**

```bash
git add pet/skills/plugins/todo/panel.py
git commit -m "refactor(todo): simplify panel — remove filters, reduce to title-only items"
```

---

### Task 5: 删除 reminder.py 和 parser.py

**Files:**
- Delete: `pet/skills/plugins/todo/reminder.py`
- Delete: `pet/skills/plugins/todo/parser.py`

- [ ] **Step 1: 删除文件并验证导入**

```bash
cd d:/Source/github/DeskPet && git rm pet/skills/plugins/todo/reminder.py pet/skills/plugins/todo/parser.py
```

- [ ] **Step 2: 验证 todo 模块完整导入**

```bash
cd d:/Source/github/DeskPet && python -c "
from pet.skills.plugins.todo.storage import TodoStorage
from pet.skills.plugins.todo.core import TodoListTool
from pet.skills.plugins.todo import register, SKILL_NAME
print(f'SKILL_NAME: {SKILL_NAME}')
print('All todo modules import successfully (no reminder/parser dependency)')
"
```

- [ ] **Step 3: 验证原 reminder.py 引用不存在**

```bash
cd d:/Source/github/DeskPet && grep -r "reminder\|parser" pet/skills/plugins/todo/ --include="*.py" || echo "No references to reminder/parser — clean"
```

- [ ] **Step 4: Commit**

```bash
git commit -m "refactor(todo): remove reminder.py and parser.py"
```

---

## 自检完成

5 个任务覆盖所有文件改动。无占位符，无 TBD，所有代码步骤完整可执行。
