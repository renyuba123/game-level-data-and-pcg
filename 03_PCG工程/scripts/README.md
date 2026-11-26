# Godot 脚本

本目录只放 Godot GDScript 及其 `.uid`。PowerShell 启动器、批处理和导出脚本统一放在 `../tools/`。

| 功能 | 文件 | 状态 |
|---|---|---|
| 当前外壳主场景 | `shell_main.gd` | `scenes/Main.tscn` 当前入口 |
| 旧版可交互基线 | `main.gd`、`pcg_model.gd` | 为 `evolution/search_v1` 复现保留 |
| Python ↔ Godot 旧桥接 | `evolution_bridge.gd` | 旧版进化基线依赖 |
| 预览与审计 | `layout_preview.gd`、`model_probe.gd`、`batch_report.gd`、`review_candidate.gd` | 人工或无界面检查 |
| 自动检查 | `smoke_test.gd`、`squeeze_test.gd`、`chase_test.gd`、`candidate_navigation_test.gd`、`editor_preview_test.gd`、`evolution_acceptance.gd` | 按对应报告复跑 |

不要仅因文件名含 `test` 就删除：这些脚本是旧版基线验收证据的一部分。移动 GDScript 前必须同步更新 `res://scripts/...` 引用、场景资源路径、文档命令和历史复现说明。
