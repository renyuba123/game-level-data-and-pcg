# ratking_run-001 QA（shuwang.graph）

- 原件 `鼠王关玩家路线图001.ai` 保持原哈希 `97797773f7d4b45d799396be8078b4d936498017de367889bd9cf3e8ce0f0aaa`；修改版 AI 由 Illustrator 保存、重新打开，再导出六组 SVG/PNG。
- 共用底图完整读取 `鼠王关.dxf` 的 129 条 LINE、2 个 CIRCLE 和 1 个封闭 LWPOLYLINE；后两类对应图中左侧与上方圆、最右小方框，六组 SVG 均含三个 CAD 细节对象。Graph 与 DXF 共享世界 XY，使用已核查的 graph→AI 仿射。新版 Convex 为 11 个 REGION，VGA 为 3,468 点。
- 六组空间指标和图件仅来自 `shuwang.graph`（SHA-256 `103c65634720498ec2f71e42b5b4c21091d0c4a5e27ee728418733794790c049`）。Gate Counts 83–82,594 count；Visual Integration [HH] 4.5676–17.1735；Metric Mean Shortest-Path Distance 6,209.8452–13,219.324。图上的十档色阶是按真实范围等距划分的**派生色阶**，不是 Depthmap 官方色标，也不是玩家经过频率。
- 本局有 44 条原生 Route 对象、24 个原生事件图标；Spawn 编 001，End 单独标注。累计顺序按静态几何推定，最大端点断接 15.71 AI 点；录像时间、重试归属和事件动作均未核实。
- 当前 CLI 的 shapegraph-connections-csv 只有表头，不能据此核实可通行门洞；拓扑边与 PCG 门洞约束保持待核实。物理比例仍未校准。
