"""TodoList 核心处理逻辑 — LLM 可见方法实现。"""

import logging
from datetime import datetime

from pet.skills.plugins.todo_list.storage import TodoStorage

logger = logging.getLogger(__name__)


class TodoListTool:
    def __init__(self):
        self._storage = TodoStorage()

    def add(self, title: str, priority: str = "medium",
            category: str = "", due_date: str = "",
            notes: str = "") -> dict:
        """添加待办事项。"""
        if not title or not title.strip():
            return {"error": "标题不能为空"}
        valid_priority = {"high", "medium", "low"}
        if priority not in valid_priority:
            priority = "medium"
        todo = self._storage.add(
            title=title.strip(),
            priority=priority,
            category=category.strip(),
            due_date=due_date.strip() or None,
            notes=notes.strip(),
        )
        parts = [f"已添加待办: #{todo['id']}「{todo['title']}」"]
        if todo["due_date"]:
            parts.append(f"截止: {todo['due_date']}")
        if todo["priority"] != "medium":
            parts.append(f"优先级: {todo['priority']}")
        todo["summary"] = " | ".join(parts)
        return todo

    def list_todos(self, status: str = "pending", priority: str = "",
                   category: str = "", limit: int = 20) -> dict:
        """查询任务列表。"""
        items = self._storage.list(
            status=status,
            priority=priority or None,
            category=category or None,
            limit=min(limit, 50),
        )
        if not items:
            return {"summary": "没有符合条件的待办事项。", "items": []}
        lines = [f"共 {len(items)} 条待办："]
        for t in items:
            line = f"  #{t['id']} [{t['priority']}] {t['title']}"
            if t["due_date"]:
                line += f" | 截止: {t['due_date']}"
            if t["category"]:
                line += f" | {t['category']}"
            lines.append(line)
        return {"summary": "\n".join(lines), "items": items}

    def complete(self, todo_id: int) -> dict:
        """标记待办为已完成。"""
        result = self._storage.complete(todo_id)
        if result is None:
            return {"error": f"未找到 id={todo_id} 的任务"}
        return {"summary": f"已完成: #{todo_id}「{result['title']}」", "item": result}

    def delete(self, todo_id: int) -> dict:
        """删除待办事项。"""
        ok = self._storage.delete(todo_id)
        if not ok:
            return {"error": f"未找到 id={todo_id} 的任务或删除失败"}
        return {"summary": f"已删除任务 #{todo_id}"}

    def update(self, todo_id: int, title: str = "", priority: str = "",
               category: str = "", due_date: str = "",
               notes: str = "") -> dict:
        """修改待办事项。只传需要修改的字段。"""
        fields = {}
        if title:
            fields["title"] = title.strip()
        if priority:
            if priority not in {"high", "medium", "low"}:
                return {"error": f"无效优先级 '{priority}'，可选: high/medium/low"}
            fields["priority"] = priority
        if category:
            fields["category"] = category.strip()
        if due_date is not None and due_date != "":
            fields["due_date"] = due_date.strip() or None
        if notes:
            fields["notes"] = notes.strip()
        if not fields:
            return {"error": "未提供任何要修改的字段"}
        result = self._storage.update(todo_id, **fields)
        if result is None:
            return {"error": f"未找到 id={todo_id} 的任务"}
        return {"summary": f"已更新 #{todo_id}「{result['title']}」", "item": result}

    def check_due(self) -> dict:
        """查询到期/逾期任务，供 LLM 判断是否需要提醒用户。"""
        now = datetime.now().isoformat()
        items = self._storage.get_due(now, precision_minutes=5)
        if not items:
            return {"summary": "当前没有到期或即将到期的任务。", "items": []}
        overdue = []
        upcoming = []
        for t in items:
            due = t["due_date"]
            if due and due <= now:
                overdue.append(t)
            else:
                upcoming.append(t)
        parts = []
        if overdue:
            parts.append(f"已过期 {len(overdue)} 条：")
            for t in overdue:
                parts.append(f"  #{t['id']}「{t['title']}」(截止: {t['due_date']})")
        if upcoming:
            parts.append(f"即将到期 {len(upcoming)} 条：")
            for t in upcoming:
                parts.append(f"  #{t['id']}「{t['title']}」(截止: {t['due_date']})")
        if not parts:
            return {"summary": "当前没有到期或即将到期的任务。", "items": []}
        return {"summary": "\n".join(parts), "items": items}

    def close(self):
        self._storage.close()
