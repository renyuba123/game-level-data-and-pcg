---
name: gameplay-route-analysis
description: 审查、绘制和比较游戏关卡的玩家移动路线、战斗事件与空间句法数据；适用于 Illustrator AI、录屏、CAD、DepthmapX Convex/VGA 和后续 PCG 数据准备。
---

# 玩家路线分析

把单局行动过程、多局共同模式、空间句法指标分开表达。先确认数据来源和质量，再选择图型；路线交叉不自动代表折返或门洞连接，静态对象顺序不自动代表时间。区分 `observed`（原始记录）、`derived`（可复算）、`hypothesis`（设计解释）。

## 选择任务

- **首局或修订**：核对 AI 原件、录像、地图和事件 → 建立候选路线顺序与 QA → 制作单局路线、事件和空间图。读 [图面规范](references/visual-style.md)、[数据合同](references/data-contract.md)、[Illustrator 工作流](references/illustrator-workflow.md)。
- **新增一局**：沿用已核准的地图 ID、空间 ID、坐标变换和图例；为新 `run_id` 建独立记录，不覆盖旧局。
- **多局对比**：按地图版本、玩家、难度、重试和结果筛选；只有多局或有时间采样时才制作密度/频次图。单局路线不平滑成热力图，也不平均成一条“真实路线”。
- **空间句法**：读 [DepthmapX 工作流](references/depthmapx-workflow.md)。Convex 的 Choice/Integration 与 VGA 的视觉指标分别导出、配准、标色标。不得把手工分区色当作数值。
- **PCG 准备**：只导出来源可追溯的拓扑目标和候选假设；单局行为不直接成为强制生成规则。

## 核心约束

- 保留用户原始 AI 字节不变。对于当前鼠王关，用户指定项目中最终只有原件和一份修改版 AI；不要额外复制 AI。删除旧副本前，先从 Illustrator 重新打开修改版并校验。其他地图按用户当次约束处理。
- 所有交付 SVG/PNG 都从最终修改版 AI 的命名图层视图导出；导出后保存源文件哈希、图层状态和输出清单。不要用独立重绘图冒称 AI 导出。
- 用户确认的总体方向与逐段顺序分开记录。只有录像或同等证据核实的段落才赋正式 `sequence_index`；候选顺序单列。未知时间、事件含义、门洞和米制比例保持空值。
- 地图 ID、房间 ID、地图坐标在同一关卡的各局中稳定。只有已核准的凸多边形和可通行连接才能参与拓扑统计。
- 必须把无法导出的指标和配准失败作为 QA 结果；不制作假 Visibility 图。

## 交付与核验

输出 AI 修改版、与当前数据质量相称的独立图组、`maps/<map_id>/` 与 `runs/<run_id>/` 数据、QA 报告。运行 `scripts/validate_run.py`，检查原件哈希、AI 可重新打开、图件来自该 AI、标注在汇报尺寸与放大 SVG 中可读。首局鼠王关具体已知问题见 [首局核验](references/rat-king-first-pass.md)。
