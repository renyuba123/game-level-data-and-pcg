# Phase 1 阶段验收：复用审查、数据合同与战斗评分草案

日期：2026-11-21。验收范围是新战斗协议的**可复算草案与边界测试**，不是可运行的鼠王战斗，也不是已校准的正式遗传实验。

## 模块与提交

| 模块 | 交付与证据 | Commit |
|---|---|---|
| 1.1 复用审查 | `REUSE_AUDIT.md`、`baseline_inventory.json`；源文件保护清单 | `9f7f036` |
| 1.2 数据合同 | `combat-pcg/3` Genome/事件/来源校验；7 项合同测试 | `254be8e` |
| 1.3 评分核 | S/F/P/D、展示用 Q、空间归一化、手算例；原30项测试 | `5dc9f79` |
| 1.4 战斗草案 | 规则配置、反例、边界裁决；首阶段夹断伤害，第二阶段才能击杀 | `92eeba9` |

## 本次运行验证

在项目 `evolution/.venv/Scripts/python.exe`（Python 3.13.2）中执行：

```text
python -B -m combat_pcg check
python -B -m unittest full_pcg.test_core -q
python -m pip check
python -B -m combat_pcg.audit --verify reports/combat_v3/baseline_inventory.json
```

结果：战斗草案与既有合同/评分 **48项通过**，旧 Full-PCG 核心 **7项通过**，`pip check` 无破损依赖。合成反例全部满足预设状态和分数界限。`check` 的正式搜索 preflight 按预期拒绝：战斗与评分配置未冻结、物理尺度未校准、自动进化引擎未实现。这里的48项是单元/合成测试；没有真实局数、Godot射击对照或 Depthmap 候选分析。

受保护文件审计发现**仅 `scenes/Main.tscn` 与原基线哈希不同**，该文件在本模块开始前已是工作区修改，未重置、暂存或提交。其余689项受保护文件与清单一致；原 `鼠王关.dxf` SHA-256 `99cb95e8c010775ceb3f27a4f3ba7677f04e2aaa71185ea776a446aca9f939d1`、`shuwang.graph` SHA-256 `103c65634720498ec2f71e42b5b4c21091d0c4a5e27ee728418733794790c049` 与清单一致。旧 `search_v1` 未修改。

## 工具与新增依赖判定

当前项目虚拟环境确认 `pymoo 0.6.2`、`NetworkX 3.7`、`Shapely 2.2.0`、`NumPy 2.5.5`；`baseline_inventory.json` 另记 `SciPy 1.18.1`、`ezdxf 1.4.5`、`matplotlib 3.11.2`。来源和许可记录见 `REUSE_AUDIT.md`、`reports/maintenance/tools_inventory.json`；依赖快照见 `reports/maintenance/tools_environment_before.txt`。本模块仅用标准库和现有包，**未新增依赖**。

Godot 负责后续真实白模/物理，DepthmapX 负责后续真实空间测量；本阶段未调用二者验收新战斗。Viewer 的 `Streamlit`/`Plotly`、测试可选 `pytest` 当前虚拟环境未安装。Streamlit/Plotly仅在 Phase 4 离线交互查看器有明确用途，替代为 Godot UI 或静态图；pytest 可继续由已有 `unittest` 替代。它们的许可、版本、与 Godot/现有环境兼容性须在实际接入前复核；本阶段不以“计划采用”冒充已安装或兼容。

## 阶段门槛与下一步

Phase 1 的审查、合同、计算方向、手算样例、异常/反例和战斗规则**草案门槛通过**。研究数值仍是待校准假设，S/F/P/D 未接真实事件采集器，不得用于正式生存选择。第一阶段越过分裂阈值的一枪只触发第二阶段，超额伤害丢弃；下一逻辑步起才允许击杀。当前1000 HP、50%阈值、40伤害下理论最少26发有效命中，不能用总伤害简单除法替代。

Phase 2 从现有 `full_pcg` 的可变拓扑与几何入手，适配同场出生、补给、两阶段战斗和权威 Python Layout；以100个固定种子的合法率及真实 Godot 关键机制测试验收。`scenes/Main.tscn` 的既存改动先单独核对，不覆盖。Phase 3 才进行代理/物理一致性、阈值校准和协议冻结；Phase 4/5 的自动进化和6048请求尚未实施。
