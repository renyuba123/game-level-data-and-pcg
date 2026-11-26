# 运维与导出工具

本目录放人工启动、批处理和源数据导出工具，不放 Godot 运行时代码。

| 工具 | 用途 |
|---|---|
| `open_viewer.ps1` | 打开指定的只读 Evolution Viewer，默认 B 组 G0–G20 |
| `run_phase4_sampling.ps1` | 按登记状态启动或续跑 Phase 4 B/C 抽样 |
| `export_source_profile.py` | 从兼容输入导出旧版基线使用的源数据轮廓 |

所有命令均从项目根目录执行。新的正式 run 必须使用独立 run ID，并遵守 `PLANS.md`、`PROGRESS.md` 和阶段报告中的冻结参数。
