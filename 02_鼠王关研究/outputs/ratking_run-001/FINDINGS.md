# 鼠王关 001：新版地图与空间句法

**观察：**当前 `source/depthmap/shuwang.graph` 导出 11 个 Convex REGION 和 3,468 个 VGA 点；建筑线来自 `source/cad/鼠王关.dxf`。001 原始路线有 44 段、24 个事件图标。图中的局部先后顺序由静态几何推定，未经录像逐段核实。

**计算：**Convex Choice 范围 0–62，中央长厅 R05=62，向右连接的 R07=48，右侧狭通道 R09=30。VGA Visual Integration [HH] 范围 4.5676–17.1735；Gate Counts 范围 83–82,594 count；Metric Mean Shortest-Path Distance 范围 6,209.8452–13,219.324。图中十档颜色按各指标真实范围等距划分，不是 Depthmap 官方色阶。房间 ID 已按新版 11 区重新分配，旧版 R03 等房间统计不能直接比较。

**设计解释：**中央 R05 与连接段 R07 的 Choice 较高，可优先检查多方向进入时的视线、掩护和目标提示；右侧通道的 Gate Counts 高值区应结合门洞与视线复查。以上只是空间结构指标与一局绘图的关联，不能推断多数玩家的经过频率或战斗强度。

**待核实：**逐段时间、重试归属、事件动作、房间之间的实际可通行门洞，以及游戏世界物理尺度。当前 CLI 的形状图连接导出只有表头，PCG 不应把未核实的凸空间邻接当作通行边。详见 `QA_REPORT.md` 与 `maps/ratking/shuwang/summary.json`。
