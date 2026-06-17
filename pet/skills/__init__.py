"""技能插件加载器 — 自动发现 + 配置选择性加载。

插件组织方式：每个插件是一个独立目录，位于 skills/plugins/ 下。
  plugins/<plugin_name>/__init__.py       — 必须定义 SKILL_NAME、SKILL_DESCRIPTION、register()
  plugins/<plugin_name>/config.json       — 插件私有配置（可选，gitignored）
  plugins/<plugin_name>/config.example.json — 配置模板（tracked，首次加载时自动复制为 config.json）
"""

import importlib
import logging
import shutil
from pathlib import Path

from pet.skills.registry import SKILL_REGISTRY

logger = logging.getLogger(__name__)


def _ensure_plugin_config(plugin_dir: Path):
    """若插件目录下有 config.example.json 但无 config.json，自动复制一份。"""
    example = plugin_dir / "config.example.json"
    target = plugin_dir / "config.json"
    if example.is_file() and not target.is_file():
        try:
            shutil.copy2(example, target)
            logger.info(f"[SkillLoader] Created config.json from example for {plugin_dir.name}")
        except OSError as e:
            logger.warning(f"[SkillLoader] Failed to copy config.example.json: {e}")


def load_skills(enabled: list[str]):
    """扫描 skills/plugins/ 下的子目录，按配置加载启用的插件。

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

    for sub_dir in sorted(plugins_dir.iterdir()):
        if not sub_dir.is_dir() or sub_dir.name.startswith("_"):
            continue

        init_file = sub_dir / "__init__.py"
        if not init_file.is_file():
            continue

        # 自动从 config.example.json 复制生成 config.json
        _ensure_plugin_config(sub_dir)

        module_path = f"pet.skills.plugins.{sub_dir.name}"
        try:
            module = importlib.import_module(module_path)
        except Exception as e:
            logger.warning(f"[SkillLoader] Failed to import {sub_dir.name}: {e}")
            continue

        skill_name = getattr(module, "SKILL_NAME", None)
        if not skill_name:
            continue

        if "*" not in enabled and skill_name not in enabled:
            logger.debug(f"[SkillLoader] Skip disabled skill: {skill_name}")
            continue

        register_fn = getattr(module, "register", None)
        if not callable(register_fn):
            logger.warning(f"[SkillLoader] {sub_dir.name} has no register() function")
            continue

        try:
            register_fn(SKILL_REGISTRY)
            loaded.append(skill_name)
            logger.info(f"[SkillLoader] Loaded skill: {skill_name}")
        except Exception as e:
            logger.error(f"[SkillLoader] Failed to register {skill_name}: {e}")

    logger.info(f"[SkillLoader] {len(loaded)} skills loaded: {loaded}")