"""技能注册表 — 自动发现、注册、描述可用技能。

args 参数格式：
  {"name": {"type": "int", "required": False, "default": 5, "desc": "说明"}}
  type 支持: int / float / str / bool / list / dict
  required=True 表示必选，缺少时校验不通并返回错误给 LLM。
"""

import logging
from dataclasses import dataclass, field
from typing import Callable, Any

logger = logging.getLogger(__name__)


@dataclass
class SkillMethod:
    name: str
    description: str
    args: dict = field(default_factory=dict)
    handler: Callable = None


@dataclass
class SkillDef:
    name: str
    description: str
    methods: dict[str, SkillMethod] = field(default_factory=dict)


class SkillRegistry:
    """全局技能注册表。"""

    def __init__(self):
        self._skills: dict[str, SkillDef] = {}
        self._disabled: set[str] = set()

    def register(self, skill_name: str, description: str) -> "SkillDef":
        skill = SkillDef(name=skill_name, description=description)
        self._skills[skill_name] = skill
        return skill

    def add_method(self, skill_name: str, method_name: str,
                   description: str, handler: Callable, args: dict = None):
        skill = self._skills[skill_name]
        skill.methods[method_name] = SkillMethod(
            name=method_name, description=description,
            args=args or {}, handler=handler,
        )

    def get_handler(self, full_name: str) -> Callable | None:
        parts = full_name.split(".", 1)
        if len(parts) != 2:
            return None
        skill_name, method_name = parts
        if not self.is_enabled(skill_name):
            return None
        skill = self._skills.get(skill_name)
        if not skill:
            return None
        method = skill.methods.get(method_name)
        return method.handler if method else None

    def generate_prompt_section(self) -> str:
        """生成注入 LLM prompt 的技能描述段。"""
        if not self._skills:
            return ""
        lines = ["=== 可用技能 ===",
                 "以上是你能调用的全部技能，禁止编造不存在的技能名。",
                 "输出格式：",
                 '  Skill: {"name": "skill.method", "args": {}}',
                 "可一次输出多个 Skill 行；工具结果返回后你可以继续输出新的 Skill 行（多轮调用，最多 3 轮）。",
                 "",
                 "可用技能列表："]
        for skill in self._skills.values():
            if not self.is_enabled(skill.name):
                continue
            lines.append(f"\n【{skill.name}】{skill.description}")
            for m in skill.methods.values():
                args_desc = self._format_args(m.args)
                args_part = f"  参数: {args_desc}" if args_desc else "  无参数"
                lines.append(f"  - {skill.name}.{m.name}: {m.description}")
                lines.append(f"    {args_part}")
        return "\n".join(lines)

    @staticmethod
    def _format_args(args: dict) -> str:
        """格式化结构化 args 为 prompt 描述文本。"""
        if not args:
            return ""
        parts = []
        for k, v in args.items():
            t = v.get("type", "any")
            req = v.get("required", False)
            desc = v.get("desc", "")
            default = v.get("default")
            tag = "必选" if req else f"可选, 默认 {default!r}"
            parts.append(f"{k}({t}, {tag}): {desc}")
        return "{" + "; ".join(parts) + "}"

    @property
    def skill_names(self) -> list[str]:
        return list(self._skills.keys())

    def is_enabled(self, skill_name: str) -> bool:
        return skill_name not in self._disabled

    def set_enabled(self, skill_name: str, enabled: bool):
        if enabled:
            self._disabled.discard(skill_name)
            logger.info(f"[Skill] ✓ enabled: {skill_name}")
        else:
            self._disabled.add(skill_name)
            logger.info(f"[Skill] ✗ disabled: {skill_name}")

    @property
    def disabled_set(self) -> set[str]:
        return set(self._disabled)


# 全局单例
SKILL_REGISTRY = SkillRegistry()
