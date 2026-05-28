"""技能注册表 — 自动发现、注册、描述可用技能。"""

from dataclasses import dataclass, field
from typing import Callable, Any


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
                 "",
                 "可用技能列表："]
        for skill in self._skills.values():
            lines.append(f"\n【{skill.name}】{skill.description}")
            for m in skill.methods.values():
                args_desc = ", ".join(f"{k}: {v}" for k, v in m.args.items())
                args_part = f"  参数: {{{args_desc}}}" if args_desc else "  无参数"
                lines.append(f"  - {skill.name}.{m.name}: {m.description}")
                lines.append(f"    {args_part}")
        return "\n".join(lines)

    @property
    def skill_names(self) -> list[str]:
        return list(self._skills.keys())


# 全局单例
SKILL_REGISTRY = SkillRegistry()
