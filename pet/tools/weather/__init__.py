from pet.tools.weather.core import get_current, get_forecast

TOOL_NAME = "weather"
TOOL_DESCRIPTION = "天气查询（当前天气、未来预报）"


def register(registry):
    tool = registry.register(TOOL_NAME, TOOL_DESCRIPTION)

    registry.add_method(
        TOOL_NAME, "get_current",
        "查询指定城市当前天气（含未来3日简要预报）",
        handler=get_current,
        args={
            "city": {"type": "str", "required": False, "default": "Beijing",
                     "desc": "城市名（中英文均可，如 Beijing/北京/Tokyo/東京）"},
        },
    )
    registry.add_method(
        TOOL_NAME, "get_forecast",
        "查询指定城市未来N日天气预报",
        handler=get_forecast,
        args={
            "city": {"type": "str", "required": False, "default": "Beijing",
                     "desc": "城市名（中英文均可）"},
            "days": {"type": "int", "required": False, "default": 3,
                     "desc": "预报天数（1-7）"},
        },
    )