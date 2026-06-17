"""浏览器操作插件"""

from pet.skills.plugins.browser.core import BrowserTool

SKILL_NAME = "browser"
SKILL_DESCRIPTION = "浏览器操作（打开网页、搜索）"

_instance = BrowserTool()


def register(registry):
    """插件接口 — 由 SkillLoader 调用。"""
    registry.register(SKILL_NAME, SKILL_DESCRIPTION)
    registry.add_method(
        SKILL_NAME, "open_url",
        "用默认浏览器打开指定URL",
        handler=_instance.open_url,
        args={
            "url": {"type": "str", "required": True, "desc": "要打开的网址（包含 http/https）"},
        },
    )
    registry.add_method(
        SKILL_NAME, "search",
        "用默认浏览器搜索关键词",
        handler=_instance.search,
        args={
            "query": {"type": "str", "required": True, "desc": "搜索关键词"},
        },
    )