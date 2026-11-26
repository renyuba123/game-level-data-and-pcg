# 目录职责复核（2026-11-26）

本次只整理文件边界，不修改评分口径、布局算法、战斗逻辑或正式实验数据。

## 已处理

- 将 `open_viewer.ps1`、`run_phase4_sampling.ps1` 从 Godot `scripts/` 移到运维 `tools/`。
- 新增 `scripts/README.md` 与 `tools/README.md`，区分当前运行时、旧版基线、自动检查、人工运维与源数据导出。
- 扩充根 `README.md` 的目录职责表，并更新所有当前命令引用。
- 删除 `combat_pcg/`、`full_pcg/`、`evolution/` 顶层共 30 个可再生成的 Python 字节码缓存文件。

## 首轮整理时保留

- `evolution/.venv/`：当前实验和生成命令直接依赖。
- `evolution/analysis_cache/`、`evolution/cache/`：可再生成但成本高，保留用于复算与追溯。
- `evolution/runs/search_v1/`、`full_pcg_output/` 当前审计目录及 F 盘正式 run 归档：属于实验与验收证据。
- `scripts/` 中的旧版基线和测试 GDScript：仍被历史复现命令与场景资源路径引用。
- 原 DXF、`shuwang.graph`、兼容输入快照、已有未提交代码和 Inspector 参数修改。

此前首轮清理的逐文件哈希见 `cleanup_20261126.json`。该 JSON 记录的是工具迁移前的快照，当前最终入口以根 README 和本文件为准。

## 后续并仓

同日主工程迁入课程仓库 `03_PCG工程/`。上节是迁移前的首轮决策；并仓时为去除可再生成内容，没有迁移 `.godot/`、`evolution/.venv/`、`evolution/analysis_cache/`、`evolution/cache/` 和 `__pycache__/`。正式 run、报告、源码、未提交文件和 `full_pcg_output/` 已保留；根兼容输入快照改为直接读取 `02_鼠王关研究/` 后移除。旧 D 盘 Git 历史与工作树 patch 存在课程整理记录中。
