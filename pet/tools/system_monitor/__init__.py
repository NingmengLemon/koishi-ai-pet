from pet.tools.system_monitor.core import get_overview, get_top_processes, get_memory_detail, get_network

TOOL_NAME = "system_monitor"
TOOL_DESCRIPTION = "系统资源监控（CPU、内存、磁盘、电池、进程）"


def register(registry):
    tool = registry.register(TOOL_NAME, TOOL_DESCRIPTION)

    registry.add_method(
        TOOL_NAME, "get_overview",
        "获取系统整体概况（CPU、内存、磁盘、电池、运行时长）",
        handler=get_overview,
        args={},
    )
    registry.add_method(
        TOOL_NAME, "get_top_processes",
        "获取占用CPU最高的前N个进程",
        handler=get_top_processes,
        args={
            "count": {"type": "int", "required": False, "default": 5,
                      "desc": "返回进程数量（1-20）"},
        },
    )
    registry.add_method(
        TOOL_NAME, "get_memory_detail",
        "获取详细内存信息（物理内存+交换分区）",
        handler=get_memory_detail,
        args={},
    )
    registry.add_method(
        TOOL_NAME, "get_network",
        "获取网络流量统计（累计发送/接收字节数）",
        handler=get_network,
        args={},
    )