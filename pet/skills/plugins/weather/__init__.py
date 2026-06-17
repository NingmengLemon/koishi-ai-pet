"""天气查询插件"""

from pet.skills.plugins.weather.core import get_current, get_forecast

SKILL_NAME = "weather"
SKILL_DESCRIPTION = "天气查询（当前天气、未来预报），调用 Open-Meteo 免费 API，无需密钥"


def register(registry):
    """插件接口 — 由 SkillLoader 调用。"""
    registry.register(SKILL_NAME, SKILL_DESCRIPTION)
    registry.add_method(
        SKILL_NAME, "get_current",
        "查询指定城市当前天气（含未来3日简要预报）",
        handler=get_current,
        args={
            "city": {"type": "str", "required": False, "default": "Beijing",
                     "desc": "城市名（中英文均可，如 Beijing/北京/Tokyo/東京）"},
        },
    )
    registry.add_method(
        SKILL_NAME, "get_forecast",
        "查询指定城市未来N日天气预报",
        handler=get_forecast,
        args={
            "city": {"type": "str", "required": False, "default": "Beijing",
                     "desc": "城市名（中英文均可）"},
            "days": {"type": "int", "required": False, "default": 3,
                     "desc": "预报天数（1-7）"},
        },
    )