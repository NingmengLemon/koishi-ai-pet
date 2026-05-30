"""技能执行器 — 解析 LLM 输出中的 Skill JSON，路由执行，返回结果。"""

import json
import logging
from dataclasses import dataclass
from typing import Any

from pet.skills.registry import SKILL_REGISTRY

logger = logging.getLogger(__name__)


# 类型名到 Python 类型的映射（用于参数校验）
_TYPE_MAP = {
    "int": int,
    "float": (int, float),
    "str": str,
    "bool": bool,
    "list": list,
    "dict": dict,
    "any": object,
}


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
    image_b64: str | None = None  # 插件可返回 base64 图片，供下一轮 LLM 多模态读取


class SkillExecutor:
    """串行执行技能调用，架构可扩展为并行。"""

    def execute(self, calls: list[SkillCall]) -> list[SkillResult]:
        results = []
        for call in calls:
            results.append(self._execute_one(call))
        return results

    def _execute_one(self, call: SkillCall) -> SkillResult:
        # 获取 SkillMethod 定义，用于参数校验
        method = self._lookup_method(call.name)
        if method is None:
            logger.warning(f"[SkillExecutor] unknown skill: {call.name}")
            return SkillResult(name=call.name, success=False, error=f"unknown skill: {call.name}")

        # 参数校验
        validated_args, err = self._validate_args(call.args, method.args)
        if err:
            logger.warning(f"[SkillExecutor] arg validation failed: {call.name}: {err}")
            return SkillResult(name=call.name, success=False, error=err)

        try:
            data = method.handler(**validated_args)
            logger.info(f"[SkillExecutor] \u2713 {call.name} \u2192 {str(data)[:100]}")
            # 插件返回的图片（__image__ 键）单独提取，不混入文本结果
            image_b64 = None
            if isinstance(data, dict):
                image_b64 = data.pop("__image__", None)
            return SkillResult(name=call.name, success=True, data=data, image_b64=image_b64)
        except TypeError as e:
            # 参数不匹配类错误，反馈明确提示让 LLM 自纠
            logger.error(f"[SkillExecutor] ✗ {call.name} TypeError: {e}")
            return SkillResult(name=call.name, success=False, error=f"参数不匹配: {e}")
        except Exception as e:
            logger.error(f"[SkillExecutor] ✗ {call.name} failed: {e}")
            return SkillResult(name=call.name, success=False, error=str(e))

    @staticmethod
    def _lookup_method(full_name: str):
        """获取 SkillMethod 实例（含 args 定义）。"""
        parts = full_name.split(".", 1)
        if len(parts) != 2:
            return None
        skill = SKILL_REGISTRY._skills.get(parts[0])
        if not skill:
            return None
        return skill.methods.get(parts[1])

    @staticmethod
    def _validate_args(provided: dict, schema: dict) -> tuple[dict, str]:
        """根据结构化 schema 校验参数并填充默认值。

        Returns:
            (validated_args, error_message)，错误为空则代表校验通过。
        """
        validated = {}
        provided = provided or {}

        for key, spec in schema.items():
            type_name = spec.get("type", "any")
            required = spec.get("required", False)
            default = spec.get("default")

            if key in provided:
                value = provided[key]
                expected_type = _TYPE_MAP.get(type_name, object)
                if expected_type is not object and not isinstance(value, expected_type):
                    return {}, f"参数 {key!r} 类型错误，期望 {type_name}，实际 {type(value).__name__}"
                validated[key] = value
            elif required:
                return {}, f"缺少必需参数 {key!r} ({type_name})"
            elif default is not None:
                validated[key] = default

        # 传入了 schema 中没有的参数也保留（宽容）
        for key, value in provided.items():
            if key not in validated:
                validated[key] = value

        return validated, ""

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
    def format_results(cls, results: list[SkillResult]) -> tuple[str, list[str]]:
        """格式化所有技能结果，并单独收集 base64 图片列表。

        Returns:
            (result_text, image_b64_list)
        """
        lines = []
        images = []
        for r in results:
            if r.success:
                lines.append(f"[✓ {r.name}]\n{cls._normalize(r.data)}")
                if r.image_b64:
                    images.append(r.image_b64)
                    lines.append("(附图: 已提供截图，可直接观察内容)")
            else:
                lines.append(f"[✗ {r.name}] 失败: {r.error}")
        return "\n\n".join(lines), images
