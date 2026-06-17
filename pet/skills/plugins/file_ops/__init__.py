"""文件操作插件"""

from pet.skills.plugins.file_ops.core import FileOpsTool

SKILL_NAME = "file"
SKILL_DESCRIPTION = "文件操作（读取、列目录、写笔记，限桌面/文档）"

_instance = FileOpsTool()


def register(registry):
    """插件接口 — 由 SkillLoader 调用。"""
    registry.register(SKILL_NAME, SKILL_DESCRIPTION)
    registry.add_method(
        SKILL_NAME, "list_dir",
        "列出指定目录内容（限桌面/文档）",
        handler=_instance.list_dir,
        args={
            "path": {"type": "str", "required": False, "default": "~/Desktop",
                     "desc": "目录路径，默认桌面"},
        },
    )
    registry.add_method(
        SKILL_NAME, "read_file",
        "读取文本文件前500字符（限桌面/文档）",
        handler=_instance.read_file,
        args={
            "path": {"type": "str", "required": True, "desc": "文件路径"},
            "max_chars": {"type": "int", "required": False, "default": 500,
                          "desc": "最大读取字符数"},
        },
    )
    registry.add_method(
        SKILL_NAME, "write_note",
        "在桌面创建一个文本笔记",
        handler=_instance.write_note,
        args={
            "filename": {"type": "str", "required": True, "desc": "文件名（含扩展名）"},
            "content": {"type": "str", "required": True, "desc": "写入内容"},
        },
    )