"""技能插件目录 — 每个子目录是一个独立插件，代码和配置隔离。

子目录结构：
  <plugin_name>/__init__.py          — 插件代码（必须定义 SKILL_NAME、register()）
  <plugin_name>/config.json          — 插件私有配置（gitignored）
  <plugin_name>/config.example.json  — 配置模板（tracked，首次加载自动复制为 config.json）
"""
