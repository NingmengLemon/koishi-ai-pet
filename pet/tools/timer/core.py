"""定时器核心 — 基于 Scheduler 的倒计时提醒。"""

import logging
import threading
import time
import uuid

from pet.tools.context import TOOL_CTX

logger = logging.getLogger(__name__)


class TimerTool:
    """倒计时定时器，到时间后主动说话 + 弹通知。"""

    def __init__(self):
        self._timers: dict[
            str, dict
        ] = {}  # timer_id → {key, label, duration_s, fire_at}
        self._lock = threading.Lock()

    # ── 公开方法 ──

    def set_timer(self, duration: int, label: str = "时间到") -> dict:
        """设定一个倒计时定时器。"""
        if duration <= 0:
            return {"error": "时长必须大于 0 秒"}
        if duration > 86400:
            return {"error": "定时器上限 24 小时"}

        timer_id = uuid.uuid4().hex[:8]
        key = f"timer_{timer_id}"
        now_s = time.time()
        fire_at = now_s + duration

        def _on_fire():
            with self._lock:
                self._timers.pop(timer_id, None)
            msg = f"叮叮！「{label}」"
            TOOL_CTX.speech(msg, duration=4000)
            TOOL_CTX.notify("⏰ 定时器", label)
            logger.info(f"[Timer] fired: {timer_id} '{label}'")

        # 先写字典再注册 alarm：防止极短定时器在 _timers 写入前就触发回调
        with self._lock:
            self._timers[timer_id] = {
                "key": key,
                "label": label,
                "duration_s": duration,
                "fire_at": fire_at,
            }
        try:
            TOOL_CTX.register_alarm(round(fire_at * 1000), _on_fire, key=key)
        except Exception:
            with self._lock:
                self._timers.pop(timer_id, None)
            return {"error": "定时器注册失败"}
        logger.info(f"[Timer] set: {timer_id} '{label}' {duration}s")
        return {
            "id": timer_id,
            "label": label,
            "duration": duration,
            "summary": f"已设定「{label}」，{self._format_duration(duration)}后提醒",
        }

    def list_timers(self) -> dict:
        """列出所有活跃定时器。"""
        with self._lock:
            snapshot = list(self._timers.items())
        if not snapshot:
            return {"summary": "当前没有活跃的定时器", "timers": [], "count": 0}

        now_s = time.time()
        items = []
        for tid, t in snapshot:
            remain = max(0, int(t["fire_at"] - now_s))
            items.append(
                {
                    "id": tid,
                    "label": t["label"],
                    "remaining_s": remain,
                    "remaining_str": self._format_duration(remain),
                }
            )

        lines = [f"共 {len(items)} 个活跃定时器:"]
        for item in items:
            lines.append(
                f"  [{item['id']}] {item['label']} — 剩余 {item['remaining_str']}"
            )
        return {"summary": "\n".join(lines), "timers": items, "count": len(items)}

    def cancel_timer(self, timer_id: str) -> dict:
        """取消指定定时器。"""
        with self._lock:
            timer = self._timers.pop(timer_id, None)

        if timer is None:
            return {"error": f"未找到定时器 {timer_id}"}

        cleaned = True
        try:
            TOOL_CTX.unregister_alarm(timer["key"])
        except Exception as e:
            logger.warning(f"[Timer] unregister failed for {timer_id}: {e}")
            cleaned = False

        logger.info(f"[Timer] cancelled: {timer_id} '{timer['label']}'")
        return {
            "cancelled": timer_id,
            "label": timer["label"],
            "alarm_cleared": cleaned,
            "summary": f"已取消定时器「{timer['label']}」"
            + ("" if cleaned else "（但提醒可能仍会触发）"),
        }

    def cancel_all(self) -> dict:
        """取消所有活跃定时器。"""
        with self._lock:
            ids = list(self._timers.keys())
        cancelled = 0
        for tid in ids:
            result = self.cancel_timer(tid)
            if "cancelled" in result:
                cancelled += 1
        return {
            "cancelled": cancelled,
            "total": len(ids),
            "summary": f"已取消 {cancelled}/{len(ids)} 个定时器",
        }

    def close(self):
        with self._lock:
            ids = list(self._timers.keys())
        for tid in ids:
            try:
                self.cancel_timer(tid)
            except Exception as e:
                logger.error(f"[Timer] close failed for {tid}: {e}")

    # ── 辅助 ──

    @staticmethod
    def _format_duration(seconds: int) -> str:
        if seconds < 60:
            return f"{seconds}秒"
        if seconds < 3600:
            m, s = divmod(seconds, 60)
            return f"{m}分{s}秒" if s else f"{m}分钟"
        h, r = divmod(seconds, 3600)
        m, s = divmod(r, 60)
        parts = [f"{h}小时"]
        if m:
            parts.append(f"{m}分")
        if s:
            parts.append(f"{s}秒")
        return "".join(parts)
