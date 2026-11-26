# ratking_run-004 QA（shuwang.graph）

- 原件 `004.ai` 保持原哈希 `b45832fc25f441a9e655eaeca1b8e9407327542ef13f32a938ea64baebe7a466`；修改版 AI 由 Illustrator 保存、重新打开，再导出六组 SVG/PNG。
- 共用底图来自 `鼠王关.dxf` 的 129 条 LINE；Graph 与 DXF 共享世界 XY，使用已核查的 graph→AI 仿射。新版 Convex 为 11 个 REGION，VGA 为 3,468 点。
- 六组空间指标和图件仅来自 `shuwang.graph`（SHA-256 `103c65634720498ec2f71e42b5b4c21091d0c4a5e27ee728418733794790c049`）。Gate Counts 83–82,594 count；Visual Integration [HH] 4.5676–17.1735；Metric Mean Shortest-Path Distance 6,209.8452–13,219.324。图上的十档色阶是按真实范围等距划分的**派生色阶**，不是 Depthmap 官方色标，也不是玩家经过频率。
- 本局有 28 条原生 Route 对象、22 个原生事件图标；Spawn 编 001，End 单独标注。累计顺序按静态几何推定，最大端点断接 313.14 AI 点；录像时间、重试归属和事件动作均未核实。
- 当前 CLI 的 shapegraph-connections-csv 只有表头，不能据此核实可通行门洞；拓扑边与 PCG 门洞约束保持待核实。物理比例仍未校准。
