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

- 保留 001–005 五份用户原始 AI 字节不变；每局只交付一份对应修改版 AI。当前鼠王关的唯一 graph 数据源是 `shuwang.graph`，底图以 `鼠王关.dxf` 为准；旧 `shuwangguan.graph` 和旧 9 房间导出只能作历史参考。
- 所有交付 SVG/PNG 都从最终修改版 AI 的命名图层视图导出；导出后保存源文件哈希、图层状态和输出清单。不要用独立重绘图冒称 AI 导出。
- 用户确认的总体方向与逐段顺序分开记录。只有录像或同等证据核实的段落才赋正式 `sequence_index`；候选顺序单列。未知时间、事件含义、门洞和米制比例保持空值。
- 单局事件优先复用用户 AI 中的原生图标。沿候选路线从 Spawn 到 End 编号 `001…N`，Spawn 为 `001`；End 是独立路线标签，不占事件编号。把几何候选编号与录像核实的事件时间分开，保留原件对象 ID。移动图层可能改变编辑版 UUID，此时记录原件 ID→编辑版 ID 的几何核对表。
- Illustrator 中每种图以 `*-Labels` 为父层，把该图的数值/路线/原生事件图标和图例放在其下；DXF 底图与墙体可共用。当前 graph 导出为 11 个凸空间和 3,468 个 VGA 点，新增 `Metric Mean Shortest-Path Distance` 独立图层。只用与当前 graph 哈希一致的指标；原图若属于旧 graph，不能拿它校准新数据。采用真实数值的派生色阶时注明计算方式，不冒称软件官方色阶。`Gate Counts` 不解释成玩家经过次数。
- 地图 ID、房间 ID、地图坐标在同一关卡的各局中稳定。只有已核准的凸多边形和可通行连接才能参与拓扑统计。
- 必须把无法导出的指标和配准失败作为 QA 结果；不制作假 Visibility 图。

## 交付与核验

输出每局 AI 修改版、六组独立图、`maps/ratking/shuwang/` 与 `runs/<run_id>/` 数据、QA 报告。运行 `scripts/validate_run.py`，检查五份原件哈希、graph/DXF 哈希、AI 可重新打开、图件来自该 AI、标注在汇报尺寸与放大 SVG 中可读。当前鼠王关具体已知问题见 [首局核验](references/rat-king-first-pass.md)。
