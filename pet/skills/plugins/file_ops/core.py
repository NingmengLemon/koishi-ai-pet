"""文件操作核心逻辑。"""

import os
import logging

logger = logging.getLogger(__name__)

# 安全限制：只允许操作用户桌面和文档目录
_ALLOWED_ROOTS = [
    os.path.expanduser("~/Desktop"),
    os.path.expanduser("~/Documents"),
]


class FileOpsTool:
    def _check_path(self, path: str) -> str:
        abs_path = os.path.abspath(os.path.expanduser(path))
        for root in _ALLOWED_ROOTS:
            try:
                if os.path.commonpath([abs_path, root]) == root:
                    return abs_path
            except ValueError:
                continue
        raise PermissionError(f"不允许访问: {abs_path}")

    def list_dir(self, path: str = "~/Desktop") -> dict:
        abs_path = self._check_path(path)
        if not os.path.isdir(abs_path):
            return {"error": "目录不存在"}
        items = os.listdir(abs_path)[:30]
        return {"path": abs_path, "items": items, "count": len(items)}

    def read_file(self, path: str, max_chars: int = 500) -> dict:
        abs_path = self._check_path(path)
        if not os.path.isfile(abs_path):
            return {"error": "文件不存在"}
        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                content = f.read(max_chars)
            return {"path": abs_path, "content": content, "truncated": len(content) >= max_chars}
        except Exception as e:
            return {"error": str(e)}

    def write_note(self, filename: str, content: str) -> dict:
        desktop = os.path.expanduser("~/Desktop")
        path = os.path.join(desktop, filename)
        abs_path = self._check_path(path)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"status": "written", "path": abs_path}