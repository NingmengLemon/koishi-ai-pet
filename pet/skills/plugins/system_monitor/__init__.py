"""系统监控插件"""

from pet.skills.plugins.system_monitor.core import get_overview, get_top_processes, get_memory_detail, get_network

SKILL_NAME = "system_monitor"
SKILL_DESCRIPTION = "系统资源监控（CPU、内存、磁盘、电池、进程）"


def register(registry):
    """插件接口 — 由 SkillLoader 调用。"""
    skill = registry.register(SKILL_NAME, SKILL_DESCRIPTION)
    skill.when = "用户询问电脑状态、卡不卡、内存/磁盘/电池/网络用量时"

    registry.add_method(
        SKILL_NAME, "get_overview",
        "获取系统整体概况（CPU、内存、磁盘、电池、运行时长）",
        handler=get_overview,
        when="用户问\"电脑怎么样\"\"卡不卡\"\"还剩多少电\"时",
        args={},
    )
    registry.add_method(
        SKILL_NAME, "get_top_processes",
        "获取占用CPU最高的前N个进程",
        handler=get_top_processes,
        when="用户问\"什么程序占CPU\"\"谁在吃资源\"时",
        args={
            "count": {"type": "int", "required": False, "default": 5,
                      "desc": "返回进程数量（1-20）"},
        },
    )
    registry.add_method(
        SKILL_NAME, "get_memory_detail",
        "获取详细内存信息（物理内存+交换分区）",
        handler=get_memory_detail,
        when="用户问\"内存还剩多少\"\"内存不够了\"时",
        args={},
    )
    registry.add_method(
        SKILL_NAME, "get_network",
        "获取网络流量统计（累计发送/接收字节数）",
        handler=get_network,
        when="用户问\"网络用了多少流量\"\"网速怎么样\"时",
        args={},
    )