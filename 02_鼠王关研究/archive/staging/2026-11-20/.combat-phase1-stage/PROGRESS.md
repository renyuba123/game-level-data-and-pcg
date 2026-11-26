# 鼠王关 PCG 开发进度

**当前阶段：Phase 1 — 复用审查、评分规范与战斗协议草案。当前模块：1.4 战斗草案、反例入口和阶段验收；进行中。** Phase 2–5 尚未进入正式验收。完整目标见 `PLANS.md`，新任务先读 `AGENTS.md`、`PLANS.md`、本文件。

## 已通过测试并提交的模块

| 模块 | 已完成内容 | 测试证据 | Commit |
|---|---|---|---|
| 1.1 复用审查 | 现有模块、风险、外部候选许可/提交快照；保护旧文件的哈希审计 | `python -m combat_pcg.audit --verify reports/combat_v3/baseline_inventory.json` → `changed: []`；当时 `full_pcg.test_core` 7项通过。690个受保护文件入清单。 | `9f7f036` |
| 1.2 数据合同 | `combat-pcg/3` Genome、同场出生、日志终止、个体出现ID与内容哈希 | `python -m unittest combat_pcg.test_contracts -v` → 7项通过 | `254be8e` |
| 1.3 草案评分核 | S/F/P/D与Q、合成手算样例、错误/缺失/早死防护、固定基准空间归一化及标签无关分类 | `python -m unittest combat_pcg.test_contracts combat_pcg.test_scoring combat_pcg.test_spatial -v` → 30项通过；合成样例S80/F90/P96/D80/Q88.3 | `5dc9f79` |

审查文档在 `reports/combat_v3/REUSE_AUDIT.md`；合同在 `reports/combat_v3/DATA_CONTRACT.md`；计分规范在 `reports/combat_v3/SCORING_SPEC.md`。合成测试分数不是真实游戏/玩家结果；配置 `frozen=false`，不得用于正式选择。

## 正在进行、尚未验收

- 模块1.4的 `combat_pcg/__main__.py`、`protocol.py`、`combat_config.json`、`counterexamples.py`、`test_protocol.py`，以及 `reports/combat_v3/COMBAT_PROTOCOL.md`、`IMPLEMENTATION_PLAN.md` **目前只在 `F:\大学作业\游戏空间设计微专业\.combat-phase1-stage` 中起草**。尚未复制到项目、尚未运行新测试、尚未提交。新任务从这里检查并继续，不要重复模块1.1–1.3。
- Phase 1阶段综合验收报告及1.4的Git Commit尚未生成。通过前不宣称 Phase 1 完成，也不正式开展 Phase 2。

## 现有 Full-PCG 开发成果与限制

`full_pcg/`、`configs/`、`full_pcg_output/` 当前未跟踪。本轮不覆盖、不混入 Phase 1 提交。已有一次100seed几何审计报告90有效、88个精确非同构基本拓扑，房数8–18、环数2–7；这不是新版同场战斗协议验收。已有部分几何拓扑重建检查；Godot实际白模导航/物理与新版战斗未完整验收。初始生成器仍按分开出生及到出口成功，交叉只支持单接口分支；新 S 的真实事件采集、Depthmap校准、完整遗传引擎、逐代Viewer和6048次新协议对照均未完成。查看 `full_pcg/STATUS.md`，其中部分文字可能早于最新未提交的几何检查。

## 工作区保护与运行现场

- 检查时已有修改：`scenes/Main.tscn`、`evolution/process.json`、Word临时锁文件；未跟踪 `configs/`、`full_pcg/`、`full_pcg_output/`。保留原样，不重置、不覆盖、不混入新模块提交。
- Godot编辑器、Godot MCP助手和Depthmap+桌面程序正在运行。进程命令行查询被系统拒绝，未确认其具体任务；未停止或重启。Python本项目虚拟环境未在当前可见进程路径中出现；必要测试仍须按当前运行状态检查后执行。
- 旧数据保护清单：`reports/combat_v3/baseline_inventory.json`。提交时显式暂存本轮文件。Git分支目前为 `feature/genative-v1`，最近相关提交见上表。未推送远程。

## 下一步行动

1. 将模块1.4暂存区草案与当前 `PLANS.md` 比较，只把已确认的研究参数写成“待校准假设”；核实与既有合同不冲突。
2. 复制1.4文件到仓库，运行 `python -m combat_pcg check`、旧核心测试与正式搜索拒绝检查；修复失败。
3. 更新本文件，加入测试结果和实际提交信息，显式暂存模块1.4及进度，Git Commit。写 Phase 1 验收报告并提交；只有门槛通过才进入 Phase 2。
4. Phase 2优先同场核心区/补给及真正可变图的100seed验证，复用已存在 `full_pcg`，不要重新造生成器。

## 更新方式

每模块在测试通过后、Git Commit之前更新本文件，记录命令、结果、限制；Commit成功后在下一次进度更新或阶段报告补入哈希。阶段推进、正式实验版本或计划修订必须与本文件同步。若仓库最新版确认计划与代码矛盾，先报告具体差异，再根据证据实施，不静默改写。
