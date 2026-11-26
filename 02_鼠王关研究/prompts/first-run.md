# 鼠王关 001 修订

使用 `$gameplay-route-analysis`。原件为 `source/illustrator/鼠王关玩家路线图001.ai`，权威建筑底图为 `source/cad/鼠王关.dxf`，**唯一 graph 数据源为 `source/depthmap/shuwang.graph`**。保留原件字节，更新 `outputs/ratking_run-001/ratking_run-001_edited.ai`。

从当前 graph 重新导出 11 个 Convex REGION 的 Choice 及几何、3,468 个 VGA 点的 `Visual Integration [HH]`、`Gate Counts` 和 `Metric Mean Shortest-Path Distance`。使用 DXF/graph 共同世界 XY 和已核查的 graph→AI 仿射；配准不合格则停止叠加。旧 `source/depthmap/history/shuwangguan.graph` 导出、旧 Gate Counts 色阶、旧 9 房间 ID 均不得用于当前图。数值色阶若由导出值等距计算，明确标为派生色阶，不称软件原生色标。

在修改版 AI 中按 `*-Labels` 父层组织路线、原始事件图标、Convex、Visibility、Gate Counts、Metric；Spawn 为事件 001，End 不占事件编号。用户确认的整体方向与局部候选顺序分开，未核实时间戳留空。保存后重新打开 AI，导出六组 SVG/PNG；核对 16:9 缩图、放大 SVG、原件/graph/DXF 哈希、3,468 个格点、11 个凸空间、图层与导出视图。Gate Counts 不称玩家经过次数。
