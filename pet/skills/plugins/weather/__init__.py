from pet.skills.plugins.weather.core import get_current, get_forecast

SKILL_NAME = "weather"
SKILL_DESCRIPTION = "天气查询（当前天气、未来预报）"


def register(registry):
    skill = registry.register(SKILL_NAME, SKILL_DESCRIPTION)
    skill.when = "用户询问天气、温度、是否下雨、出门穿衣建议时"

    registry.add_method(
        SKILL_NAME, "get_current",
        "查询指定城市当前天气（含未来3日简要预报）",
        handler=get_current,
        when="用户问\"今天天气怎么样\"\"外面冷吗\"\"要不要带伞\"时",
        args={
            "city": {"type": "str", "required": False, "default": "Beijing",
                     "desc": "城市名（中英文均可，如 Beijing/北京/Tokyo/東京）"},
        },
    )
    registry.add_method(
        SKILL_NAME, "get_forecast",
        "查询指定城市未来N日天气预报",
        handler=get_forecast,
        when="用户问\"未来几天天气\"\"周末天气\"\"下周天气\"时",
        args={
            "city": {"type": "str", "required": False, "default": "Beijing",
                     "desc": "城市名（中英文均可）"},
            "days": {"type": "int", "required": False, "default": 3,
                     "desc": "预报天数（1-7）"},
        },
    )