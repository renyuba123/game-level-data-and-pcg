# boss-level-pcg

当前使用 **B 组重点抽样 + 单亲档案进化**。最新完整开发归档为 `shell_sampling_focused_g20_v1`，G0–G20、168 次请求。正式实验准入仍以 PROGRESS 和 PLANS 为准。

## 查看最新 B 组

在项目目录执行 `& .\tools\open_viewer.ps1`，然后打开 <http://127.0.0.1:8503/>。Viewer 使用当前 `full_pcg/viewer/` 代码及已有未提交修正。

## 找每次 run 的输出

所有进化实验输出已迁入课程仓库的 [`../04_PCG实验输出/`](../04_PCG实验输出/README.md)，本工程只保留代码、配置、报告与 Viewer 入口。

- [逐次 run 输出总览](RUN_OUTPUTS.html)：汇总、逐代文件、日志和原始目录。
- [简明 run 索引](RUNS.md)：每次 run 的范围和路径。
- [实验输出索引](../04_PCG实验输出/实验索引.csv)：逐 run 的用途、状态、代次、结果与路径。
- 查看其他历史 run：`& .\tools\open_viewer.ps1 -Run '实际run名称' -Port 8506`。

## 项目入口

| 需要做什么 | 入口 |
|---|---|
| 当前状态、下一步 | [PROGRESS.md](PROGRESS.md) |
| 已确认的研究与开发约束 | [PLANS.md](PLANS.md) |
| 贡献规则 | [AGENTS.md](AGENTS.md) |
| Viewer | [full_pcg/viewer](full_pcg/viewer/README.md) |
| 布局与进化引擎 | [full_pcg](full_pcg/README.md) |
| 战斗、空间分析与评分 | `combat_pcg/` |
| Godot 主场景 | `scenes/Main.tscn` → `scripts/shell_main.gd` |
| 当前 B 组与对照依据 | [抽样对照报告](reports/combat_v3/PHASE4_SAMPLING_COMPARISON.md) |
| 最新回放诊断 | [Seed1102 与 B 对照](reports/combat_v3/PHASE4_SEED1102_REVIEW.md) |

旧开发草案和四批被后续方案替代的外形审阅快照已清理；可复用代码、有效实验、源资料和最新 Viewer 依赖继续保留。大型 run 原始输出已按原 run ID 迁入 `../04_PCG实验输出/runs/`，本地完整保留，GitHub 只跟踪索引与元数据。

## 目录职责

| 目录 | 只放什么 | 主要入口 |
|---|---|---|
| `scenes/`、`scripts/` | Godot 场景、运行时代码与无界面检查脚本 | `scenes/Main.tscn`、`scripts/README.md` |
| `full_pcg/` | 当前 Python Layout、进化引擎、Godot 战斗后端与 Viewer | `full_pcg/README.md` |
| `combat_pcg/` | 版本化战斗合同、模拟、空间分析与评分 | 包内 CLI 与测试 |
| `evolution/` | 已验收的旧版 Depthmap 反馈进化基线及 `search_v1` 证据 | `evolution/README.md` |
| `configs/` | 正式或试跑配置；配置与 run ID 一一对应 | `shell_*.json` |
| `data/` | 小型、版本化的输入与兼容数据 | `data/evolution/` |
| `tools/` | 人工启动、批处理和源数据导出工具 | `tools/README.md` |
| `reports/` | 阶段验收、比较、诊断和维护记录 | `reports/combat_v3/` |
| `requirements/` | 分用途依赖清单 | `phase1_tools.txt` |
| `addons/` | Godot 插件；不与项目业务代码混放 | `addons/godot_ai/` |
| `full_pcg_output/` | 本地生成的审计与运行输出，Git 忽略；Godot 以 `res://full_pcg_output/...` 读取，故不移出工程 | 由对应报告引用 |

每次实验的原始输出、诊断、检查与日志在 [`../04_PCG实验输出/`](../04_PCG实验输出/README.md)；本表只列工程内部文件。

根目录只保留项目入口、计划/进度、run 索引与 Godot 工程文件。当前 graph、DXF 和空间分析导出直接读取相邻的 `../02_鼠王关研究/`，不再使用课程仓库根快照。

迁入课程仓库时没有复制可再生成的 `.godot/`、`evolution/.venv/`、`evolution/analysis_cache/`、`evolution/cache/` 和 `__pycache__/`。首次运行旧版 evolution 命令前，执行 `py -3.13 -m venv evolution/.venv`，再执行 `& evolution/.venv/Scripts/python.exe -m pip install -r evolution/requirements-lock.txt`。正式 run、报告、版本化基线与 `full_pcg_output/` 审计证据已保留。
