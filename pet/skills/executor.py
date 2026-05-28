"""技能执行器 — 解析 LLM 输出中的 Skill JSON，路由执行，返回结果。"""

import json
import logging
from dataclasses import dataclass
from typing import Any

from pet.skills.registry import SKILL_REGISTRY

logger = logging.getLogger(__name__)


@dataclass
class SkillCall:
    name: str
    args: dict


@dataclass
class SkillResult:
    name: str
    success: bool
    data: Any = None
    error: str = ""


class SkillExecutor:
    """串行执行技能调用，架构可扩展为并行。"""

    def execute(self, calls: list[SkillCall]) -> list[SkillResult]:
        results = []
        for call in calls:
            results.append(self._execute_one(call))
        return results

    def _execute_one(self, call: SkillCall) -> SkillResult:
        handler = SKILL_REGISTRY.get_handler(call.name)
        if handler is None:
            logger.warning(f"[SkillExecutor] unknown skill: {call.name}")
            return SkillResult(name=call.name, success=False, error="unknown skill")
        try:
            data = handler(**call.args)
            logger.info(f"[SkillExecutor] ✓ {call.name} → {str(data)[:100]}")
            return SkillResult(name=call.name, success=True, data=data)
        except Exception as e:
            logger.error(f"[SkillExecutor] ✗ {call.name} failed: {e}")
            return SkillResult(name=call.name, success=False, error=str(e))

    @staticmethod
    def parse_skill_lines(content: str) -> list[SkillCall]:
        calls = []
        for line in content.split("\n"):
            line = line.strip()
            if line.lower().startswith("skill:"):
                raw = line.split(":", 1)[1].strip()
                try:
                    obj = json.loads(raw)
                    calls.append(SkillCall(
                        name=obj.get("name", ""),
                        args=obj.get("args", {}),
                    ))
                except json.JSONDecodeError:
                    logger.warning(f"[SkillExecutor] invalid JSON: {raw[:80]}")
        return calls

    @staticmethod
    def _normalize(data: Any) -> str:
        """统一格式化返回值：dict 支持 summary 键，兼容 str/基本类型。"""
        if isinstance(data, dict):
            summary = data.pop("summary", None)
            json_str = json.dumps(data, ensure_ascii=False)
            return f"{summary}\n{json_str}" if summary else json_str
        elif isinstance(data, str):
            return data
        return str(data)

    @classmethod
    def format_results(cls, results: list[SkillResult]) -> str:
        lines = []
        for r in results:
            if r.success:
                lines.append(f"[✓ {r.name}]\n{cls._normalize(r.data)}")
            else:
                lines.append(f"[✗ {r.name}] 失败: {r.error}")
        return "\n\n".join(lines)
