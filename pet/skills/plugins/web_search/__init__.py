"""网络搜索插件 — 支持 SearXNG（自建）和 Bing Web Search API。"""

from pet.skills.plugins.web_search.core import search, deep_search, check_connectivity

SKILL_NAME = "web_search"
SKILL_DESCRIPTION = "网络搜索，获取实时信息、新闻、百科知识"


def register(registry):
    """插件接口 — 由 SkillLoader（后台线程）调用。"""
    # 连通性检测（同步，但在 loader 后台线程中，不阻塞主线程）
    if not check_connectivity():
        raise RuntimeError("web_search: 所有搜索后端均不可达，跳过加载")

    skill = registry.register(SKILL_NAME, SKILL_DESCRIPTION)
    skill.when = "用户询问时事/新闻/实时数据等不确定信息，或你需要查证事实才能回答时"

    registry.add_method(
        SKILL_NAME, "search",
        "搜索网络获取最新信息（返回标题和摘要，速度快）",
        handler=search,
        when="快速查询，只需概要信息时",
        args={
            "query": {
                "type": "str",
                "required": True,
                "desc": "搜索关键词",
            },
            "count": {
                "type": "int",
                "required": False,
                "default": 5,
                "desc": "返回结果数量（1-10）",
            },
            "language": {
                "type": "str",
                "required": False,
                "default": "zh-CN",
                "desc": "语言/区域代码（zh-CN / en-US / ja-JP 等）",
            },
        },
    )
    registry.add_method(
        SKILL_NAME, "deep_search",
        "深度搜索：搜索后自动抓取前几条结果的页面正文，信息更完整详细（比 search 慢）",
        handler=deep_search,
        when="需要具体细节、数据、完整内容时（如比赛比分、数据对比、文章详情等普通搜索摘要无法回答的问题）",
        args={
            "query": {
                "type": "str",
                "required": True,
                "desc": "搜索关键词",
            },
            "count": {
                "type": "int",
                "required": False,
                "default": 5,
                "desc": "搜索结果数量（1-10）",
            },
            "language": {
                "type": "str",
                "required": False,
                "default": "zh-CN",
                "desc": "语言/区域代码",
            },
            "extract_top": {
                "type": "int",
                "required": False,
                "default": 2,
                "desc": "抓取正文的结果条数（1-3，越多越慢）",
            },
        },
    )