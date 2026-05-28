"""技能插件加载器 — 自动发现 + 配置选择性加载。"""

import importlib
import logging
from pathlib import Path

from pet.skills.registry import SKILL_REGISTRY

logger = logging.getLogger(__name__)


def load_skills(enabled: list[str]):
    """扫描 skills/plugins/ 目录，按配置加载启用的插件。

    Args:
        enabled: 启用列表。["*"] 表示全部启用，[] 表示全部禁用。
    """
    if not enabled:
        logger.info("[SkillLoader] No skills enabled")
        return

    plugins_dir = Path(__file__).parent / "plugins"
    if not plugins_dir.is_dir():
        logger.warning("[SkillLoader] plugins directory not found")
        return

    loaded = []

    for py_file in sorted(plugins_dir.glob("*.py")):
        module_name = py_file.stem
        if module_name.startswith("_"):
            continue

        try:
            module = importlib.import_module(f"pet.skills.plugins.{module_name}")
        except Exception as e:
            logger.warning(f"[SkillLoader] Failed to import {module_name}: {e}")
            continue

        skill_name = getattr(module, "SKILL_NAME", None)
        if not skill_name:
            continue

        if "*" not in enabled and skill_name not in enabled:
            logger.debug(f"[SkillLoader] Skip disabled skill: {skill_name}")
            continue

        register_fn = getattr(module, "register", None)
        if not callable(register_fn):
            logger.warning(f"[SkillLoader] {module_name} has no register() function")
            continue

        try:
            register_fn(SKILL_REGISTRY)
            loaded.append(skill_name)
            logger.info(f"[SkillLoader] Loaded skill: {skill_name}")
        except Exception as e:
            logger.error(f"[SkillLoader] Failed to register {skill_name}: {e}")

    logger.info(f"[SkillLoader] {len(loaded)} skills loaded: {loaded}")
