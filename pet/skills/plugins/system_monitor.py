"""系统监控技能 —— 查询 CPU、内存、磁盘、电池、进程等系统信息。

工具调用格式：
  Tool: {"name": "system_monitor.get_overview", "args": {}}
  Tool: {"name": "system_monitor.get_top_processes", "args": {"count": 5}}
"""

import psutil
import logging
import platform
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

SKILL_NAME = "system_monitor"
SKILL_DESCRIPTION = "系统资源监控（CPU、内存、磁盘、电池、进程）"


def _format_bytes(b: int) -> str:
    """字节数转可读字符串。"""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(b) < 1024:
            return f"{b:.1f}{unit}"
        b /= 1024
    return f"{b:.1f}PB"


def _get_overview() -> dict:
    """获取系统整体概况：CPU、内存、磁盘、电池、运行时长。"""
    cpu_percent = psutil.cpu_percent(interval=0.3)
    cpu_count = psutil.cpu_count()

    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    # 系统运行时长
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime = datetime.now() - boot_time
    uptime_str = str(timedelta(seconds=int(uptime.total_seconds())))

    result = {
        "cpu_percent": cpu_percent,
        "cpu_cores": cpu_count,
        "memory_percent": mem.percent,
        "memory_used": _format_bytes(mem.used),
        "memory_total": _format_bytes(mem.total),
        "disk_percent": disk.percent,
        "disk_used": _format_bytes(disk.used),
        "disk_total": _format_bytes(disk.total),
        "uptime": uptime_str,
        "os": f"{platform.system()} {platform.release()}",
    }

    # 电池信息（笔记本才有）
    battery = psutil.sensors_battery()
    if battery:
        result["battery_percent"] = battery.percent
        result["battery_charging"] = battery.power_plugged

    # 生成 summary
    parts = [
        f"CPU {cpu_percent}% ({cpu_count}核)",
        f"内存 {mem.percent}% ({_format_bytes(mem.used)}/{_format_bytes(mem.total)})",
        f"磁盘 {disk.percent}%",
    ]
    if battery:
        status = "充电中" if battery.power_plugged else "放电中"
        parts.append(f"电池 {battery.percent}% ({status})")
    parts.append(f"已运行 {uptime_str}")

    result["summary"] = " | ".join(parts)
    return result


def _get_top_processes(count: int = 5) -> dict:
    """获取占用 CPU 最高的前 N 个进程。"""
    count = max(1, min(count, 20))  # 限制范围 1-20
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            info = p.info
            if info["cpu_percent"] is not None:
                procs.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    procs.sort(key=lambda x: x["cpu_percent"] or 0, reverse=True)
    top = procs[:count]

    lines = [f"CPU 占用最高的 {len(top)} 个进程："]
    for i, p in enumerate(top, 1):
        lines.append(
            f"  {i}. {p['name']} (PID {p['pid']}) "
            f"- CPU {p['cpu_percent']:.1f}% / 内存 {p['memory_percent']:.1f}%"
        )

    return {
        "processes": top,
        "summary": "\n".join(lines),
    }


def _get_memory_detail() -> dict:
    """获取详细内存信息。"""
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()

    result = {
        "ram_total": _format_bytes(mem.total),
        "ram_used": _format_bytes(mem.used),
        "ram_available": _format_bytes(mem.available),
        "ram_percent": mem.percent,
        "swap_total": _format_bytes(swap.total),
        "swap_used": _format_bytes(swap.used),
        "swap_percent": swap.percent,
    }

    result["summary"] = (
        f"物理内存: {mem.percent}% ({_format_bytes(mem.used)}/{_format_bytes(mem.total)}, "
        f"可用 {_format_bytes(mem.available)}) | "
        f"交换分区: {swap.percent}% ({_format_bytes(swap.used)}/{_format_bytes(swap.total)})"
    )
    return result


def _get_network() -> dict:
    """获取网络流量统计。"""
    counters = psutil.net_io_counters()
    result = {
        "bytes_sent": _format_bytes(counters.bytes_sent),
        "bytes_recv": _format_bytes(counters.bytes_recv),
        "packets_sent": counters.packets_sent,
        "packets_recv": counters.packets_recv,
    }
    result["summary"] = (
        f"网络: 已发送 {_format_bytes(counters.bytes_sent)} / "
        f"已接收 {_format_bytes(counters.bytes_recv)}"
    )
    return result


def register(registry):
    """插件接口 — 由 SkillLoader 调用。"""
    registry.register(SKILL_NAME, SKILL_DESCRIPTION)

    registry.add_method(
        SKILL_NAME, "get_overview",
        "获取系统整体概况（CPU、内存、磁盘、电池、运行时长）",
        handler=_get_overview,
        args={},
    )
    registry.add_method(
        SKILL_NAME, "get_top_processes",
        "获取占用CPU最高的前N个进程",
        handler=_get_top_processes,
        args={"count": "返回进程数量(int, 默认5, 最大20)"},
    )
    registry.add_method(
        SKILL_NAME, "get_memory_detail",
        "获取详细内存信息（物理内存+交换分区）",
        handler=_get_memory_detail,
        args={},
    )
    registry.add_method(
        SKILL_NAME, "get_network",
        "获取网络流量统计（累计发送/接收字节数）",
        handler=_get_network,
        args={},
    )
