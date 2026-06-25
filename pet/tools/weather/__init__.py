from pet.tools.weather.core import get_current, get_forecast
from pet.tools.context import TOOL_CTX

TOOL_NAME = "weather"
TOOL_DESCRIPTION = "天气查询（当前天气、未来预报）"


def _get_current(**kw):
    TOOL_CTX.speech("查查天气…", 3000)
    return get_current(**kw)


def _get_forecast(**kw):
    TOOL_CTX.speech("看看未来天气…", 3000)
    return get_forecast(**kw)


def register(registry):
    tool = registry.register(TOOL_NAME, TOOL_DESCRIPTION)

    registry.add_method(
        TOOL_NAME, "get_current",
        "查询指定城市当前天气（含未来3日简要预报）",
        handler=_get_current,
        args={
            "city": {"type": "str", "required": False, "default": "Beijing",
                     "desc": "城市名（中英文均可，如 Beijing/北京/Tokyo/東京）"},
        },
    )
    registry.add_method(
        TOOL_NAME, "get_forecast",
        "查询指定城市未来N日天气预报",
        handler=_get_forecast,
        args={
            "city": {"type": "str", "required": False, "default": "Beijing",
                     "desc": "城市名（中英文均可）"},
            "days": {"type": "int", "required": False, "default": 3,
                     "desc": "预报天数（1-7）"},
        },
    )