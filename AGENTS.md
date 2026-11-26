# 游戏空间设计微专业：目录与操作约定

本仓库包含课程案例、鼠王关空间分析、Godot/PCG 主工程与各次实验输出。先读根 README 与 `02_鼠王关研究/README.md`。找材料去 `02_鼠王关研究/`，改代码去 `03_PCG工程/`，看每次实验结果去 `04_PCG实验输出/`。

- 鼠王关分析项目根已从仓库根迁入 `02_鼠王关研究/`；分析命令须以该目录为工作目录。
- 原始 AI 在 `source/illustrator/`，CAD 在 `source/cad/`，当前 graph 在 `source/depthmap/shuwang.graph`，录像在 `source/video/`，均相对于分析项目根。
- 当前再生成流程为 `tools/prepare_shuwang_runs.py` → `tools/build_shuwang_jsx.py` → Illustrator 执行 `tools/render_shuwang.jsx` → `tools/finalize_shuwang.py`。
- 使用分析项目内 `tools/validate_run.py`；它适配了新路径。共享分析方法中的旧目录表达，按这里的路径映射理解。
- `maps/ratking/shuwang/` 是当前数据，`maps/ratking/` 根部的旧导出只供历史追溯；不要混用新旧 graph。
- Godot / PCG 主工程为本仓库的 `03_PCG工程/`，计划和进度以其 `PLANS.md`、`PROGRESS.md` 为准。不要在仓库外创建第二份可继续开发的主工程。
- 保留用户未提交修改、原始 AI/CAD/graph、录像、历史证据与实验数据。移动文件时同步维护相对引用和来源清单，不自动提交或推送。
- 根目录既有工具依赖、工作暂存及共享代理配置保持原位，避免破坏已有绝对路径。
- 每次进化实验输出、战斗诊断、检查输出与日志统一放在 `04_PCG实验输出/`；run ID 与原目录内部结构不变。原始实验输出（约 20 GB）本地完整保留，GitHub 只跟踪 README、实验索引与各 run 的登记/配置/汇总/逐代小文件，由该目录 `.gitignore` 控制。
- Viewer 和 `output_root` 指向 `04_PCG实验输出/runs/<run_id>`；历史报告中的 `.phase14-work/<run_id>` 按相同 run ID 映射到该目录。`03_PCG工程/full_pcg_output/` 因 Godot `res://full_pcg_output/...` 依赖仍留在工程内。
- 历史说明在 `02_鼠王关研究/docs/history/`，整理记录在 `00_课程说明/整理记录/2026-11-26/`。

- PCG 直接读取 `02_鼠王关研究/source/` 与 `02_鼠王关研究/maps/ratking/shuwang/`；仓库根不保留兼容输入快照。所有源资料与分析只在 `02_鼠王关研究/` 更新。
