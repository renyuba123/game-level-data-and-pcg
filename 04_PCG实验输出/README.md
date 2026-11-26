# PCG 实验输出

入口见 [总导航](../README.md)。本目录只放**每次实验的输出与诊断**：找材料去 `02_鼠王关研究/`，改代码去 `03_PCG工程/`，看每次实验结果来这里。

完整逐 run 清单见 [实验索引.csv](实验索引.csv)，逐文件迁移来源见 [迁移记录.json](迁移记录.json)。

## 目录职责

| 目录 | 内容 | 入口 |
|---|---|---|
| `runs/` | 每次进化实验一个目录，沿用原 run ID，内部结构不变 | [实验索引.csv](实验索引.csv) |
| `diagnostics/` | 战斗与策略诊断，如 `seed1102_policy_v1`、`seed1102_phase4_review_01`、`phase3_inspector_177_v1` | 各目录内 `registration.json` / `verification.json` / `*.md` |
| `checks/` | 几何、导航、空间分析与截图检查输出 | 各目录内 `manifest.json` |
| `logs/` | 原先散落在 `.phase14-work/` 根部、尚未归属到具体 run 的 Viewer / 协调器 / Godot 日志 | 文件名保留原样 |

每个 run 内部沿用原结构：`registration.json`（登记与来源）、`config_snapshot.json`（当次配置快照）、`overview.json`（结果汇总）、`genetic/`（G0–G20 逐代记录；随机组为 `random/`）、`packages/`（布局包）、`evaluation/`（评分、对局与事件）、`space/`（Depthmap 原始结果）、`runtime/`（执行日志）。

## 当前与对照实验

| 分组 | Run ID | 结果摘要 |
|---|---|---|
| **当前 B** | `shell_sampling_focused_g20_v1` | G0–G20，168 次请求，162 张唯一布局，157 COMPLETE_DRAFT / 6 INVALID / 5 UNCERTAIN，1944 局认证对局，最高 Q 67.81 |
| A 对照 | `shell_local_g20_pop8_20261125_143448_831` | G0–G20，168 次请求，159 张布局，146 COMPLETE_DRAFT / 9 INVALID / 13 UNCERTAIN，1908 局 |
| C 对照 | `shell_sampling_random_g20_v1` | G0–G20，168 次请求，144 张已评分布局，118 COMPLETE_DRAFT / 26 UNCERTAIN / 24 INVALID，1728 局 |

A/C、单步局部编辑、连续/恢复对照以及冒烟试跑都是可复核的历史结果，不是无效数据；各自保留独立目录与原始 run ID。

## Git 策略

原始输出体量很大（B 组约 5 GB，全部 run 约 20 GB），因此：

- **本地完整保留**：所有 `evaluation/`、`space/`、`packages/` 等原始输出已实际移动至本目录，未删除、未改写内部文件。
- **GitHub 只收轻量内容**：`.gitignore` 默认忽略本目录，只放行本 README、`实验索引.csv`、`迁移记录.json`，以及各 run 的 `registration.json`、`config_snapshot.json`、`overview.json`、`genetic/`、`runtime/` 等小文件。约 19 MB。
- 历史报告与配置里出现的 `.phase14-work/<run_id>` 是迁移前的路径，对应本目录 `runs/<run_id>`；原始 run ID 未变，可按 ID 直接定位。

## 未迁入本目录的两类内容

- `03_PCG工程/full_pcg_output/`：Godot 脚本通过 `res://full_pcg_output/...` 读取其中的布局包与导航检查结果，移出工程会破坏引用，因此仍留在工程内，并在 `03_PCG工程/README.md` 中索引。
- `.phase14-work/`：工具环境、Viewer 缓存与临时暂存脚本（venv、npm/wheel 缓存、隔离 Godot、`ratking_redesign/` 代码快照等）按仓库约定保持原位；本目录只接收实验输出。

历史说明与整理依据见 `00_课程说明/整理记录/2026-11-26/`。
