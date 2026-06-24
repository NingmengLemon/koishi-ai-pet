"""工具执行器 — 解析 LLM 输出中的 Tool JSON，路由执行，返回结果。"""

import json
import logging
from dataclasses import dataclass
from typing import Any

from pet.tools.registry import TOOL_REGISTRY

logger = logging.getLogger(__name__)

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
class ToolCall:
    name: str
    args: dict


@dataclass
class ToolResult:
    name: str
    success: bool
    data: Any = None
    error: str = ""
    image_b64: str | None = None
    image_mime: str = "image/png"
    context_brief: str = ""


class ToolExecutor:

    def execute(self, calls: list[ToolCall]) -> list[ToolResult]:
        results = []
        for call in calls:
            results.append(self._execute_one(call))
        return results

    def _execute_one(self, call: ToolCall) -> ToolResult:
        method = self._lookup_method(call.name)
        if method is None:
            logger.warning(f"[ToolExecutor] unknown tool: {call.name}")
            return ToolResult(name=call.name, success=False, error=f"unknown tool: {call.name}")

        validated_args, err = self._validate_args(call.args, method.args)
        if err:
            logger.warning(f"[ToolExecutor] arg validation failed: {call.name}: {err}")
            return ToolResult(name=call.name, success=False, error=err)

        try:
            data = method.handler(**validated_args)
            logger.info(f"[ToolExecutor] {call.name} -> {str(data)[:100]}")
            image_b64 = None
            image_mime = "image/png"
            context_brief = ""
            if isinstance(data, dict):
                image_b64 = data.pop("__image__", None)
                image_mime = data.pop("__image_mime__", "image/png")
                context_brief = data.pop("__context__", "")
            return ToolResult(name=call.name, success=True, data=data, image_b64=image_b64, image_mime=image_mime, context_brief=context_brief)
        except TypeError as e:
            logger.error(f"[ToolExecutor] {call.name} TypeError: {e}")
            return ToolResult(name=call.name, success=False, error=f"参数不匹配: {e}")
        except Exception as e:
            logger.error(f"[ToolExecutor] {call.name} failed: {e}")
            return ToolResult(name=call.name, success=False, error=str(e))

    @staticmethod
    def _lookup_method(full_name: str):
        parts = full_name.split(".", 1)
        if len(parts) != 2:
            return None
        tool = TOOL_REGISTRY._tools.get(parts[0])
        if not tool:
            return None
        return tool.methods.get(parts[1])

    @staticmethod
    def _validate_args(provided: dict, schema: dict) -> tuple[dict, str]:
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

        for key, value in provided.items():
            if key not in validated:
                validated[key] = value

        return validated, ""

    @staticmethod
    def _normalize(data: Any) -> str:
        if isinstance(data, dict):
            summary = data.pop("summary", None)
            json_str = json.dumps(data, ensure_ascii=False)
            return f"{summary}\n{json_str}" if summary else json_str
        elif isinstance(data, str):
            return data
        return str(data)

    @classmethod
    def format_results(cls, results: list[ToolResult]) -> tuple[str, list[str]]:
        lines = []
        image_uris = []
        for r in results:
            if r.success:
                lines.append(f"[OK {r.name}]\n{cls._normalize(r.data)}")
                if r.image_b64:
                    image_uris.append(f"data:{r.image_mime};base64,{r.image_b64}")
                    lines.append("(附图: 已提供截图，可直接观察内容)")
            else:
                lines.append(f"[FAIL {r.name}] failed: {r.error}")
        return "\n\n".join(lines), image_uris
