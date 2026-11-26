# 游戏空间设计微专业：目录与操作约定

本仓库包含课程案例及鼠王关空间分析。先读根 README 与 `02_鼠王关研究/README.md`。

- 鼠王关分析项目根已从仓库根迁入 `02_鼠王关研究/`；分析命令须以该目录为工作目录。
- 原始 AI 在 `source/illustrator/`，CAD 在 `source/cad/`，当前 graph 在 `source/depthmap/shuwang.graph`，录像在 `source/video/`，均相对于分析项目根。
- 当前再生成流程为 `tools/prepare_shuwang_runs.py` → `tools/build_shuwang_jsx.py` → Illustrator 执行 `tools/render_shuwang.jsx` → `tools/finalize_shuwang.py`。
- 使用分析项目内 `tools/validate_run.py`；它适配了新路径。共享分析方法中的旧目录表达，按这里的路径映射理解。
- `maps/ratking/shuwang/` 是当前数据，`maps/ratking/` 根部的旧导出只供历史追溯；不要混用新旧 graph。
- Godot / PCG 主工程为 `D:\GODOT Prams\boss-level-pcg`，计划和进度以其 `PLANS.md`、`PROGRESS.md` 为准。此处不创建第二份可继续开发的主工程。
- 保留用户未提交修改、原始 AI/CAD/graph、录像、历史证据与实验数据。移动文件时同步维护相对引用和来源清单，不自动提交或推送。
- 根目录既有工具依赖、工作暂存及共享代理配置保持原位，避免破坏已有绝对路径。
- 历史说明在 `02_鼠王关研究/docs/history/`，整理记录在 `00_课程说明/整理记录/2026-11-26/`。
