# 玩家路线分析图规范

参考：[Pathways 的箭头、事件与时间切片](https://www.sfu.ca/~shaw/papers/Gagne-Pathways-ICEC11.pdf)；[多局轨迹聚合研究](https://research.jku.at/en/publications/visualization-of-player-movement-patterns-with-line-integral-conv/)。借鉴信息编码，不复制原图。优先保证 16:9 PPT 缩放后可读，并以 SVG 供论文排版。

## 单局图

1. `movement`：中性灰墙体、淡色空间边界、蓝色原始路线、绿色 Spawn、明确终点、少量方向箭头与段号。仅有总体方向证据时，箭头代表候选段序且图例写明“逐段顺序待核验”；不能把交叉处的静态叠线当作已验证的时间连接。
2. `combat_events`：同底图、淡路线、复用原始 AI 图标；`001` 为 Spawn，其余按路线方向的空间候选顺序递增，End 是独立路线标签。编号与图标以细引线对应；图例说明原始图层和未核实的动作语义，不把武器图层名当作已确认的射击动作。
3. `convex_choice`：真实凸空间边界、ID、DepthmapX Choice 数值及分级色标；若数值未导出则只可称 `convex_regions`，不称 Choice。
4. `vga_visibility`：从真实 VGA 点数据绘制 `Visual Integration [HH]`，注明点网格间距、数值范围和无数据区域；与 Choice 使用不同标题、图例和来源说明。
5. `gate_counts`：白底矢量格点图，使用当前 `shuwang.graph` 的真实 3,468 个 `Gate Counts` 点值；当前范围 83–82,594 count。十档等距数值色阶是派生编码，不能称软件官方色阶，也不能称玩家经过频率。旧 graph 的原图和阈值不能用于新图。
6. `metric_distance`：`Metric Mean Shortest-Path Distance` 独立图，使用相同坐标与 VGA 点，指标名、导出范围、图例和物理尺度状态单列。

单局不得输出无分母的“使用频率热图”。有已校对的顺序时可另作房间进入次数图，标题注明 `N=1` 和计数定义。多局图使用小倍图、每局独立色或汇总密度图，写明局数、采样率和归一化方法，不把平均轨迹当成真实路径。

## 图面与导出

- 灰白底图；主路线高对比蓝，约 2–3 pt（按画板实测）；墙体较细，门洞保持可见；数值色标不得复用仅表示房间类别的颜色。
- 每张图有标题、`map_id/run_id`、证据等级、比例/单位状态、指标全称和范围、数据源、图例。事件标签与房间 ID 避开门洞和路线交叉。
- 从同一修改版 AI 的命名视图导出 SVG 和 PNG，使用 16:9 汇报版面；SVG 放大检查路径和文字，PNG 在实际投影大小检查辨识度。导出清单记录 AI 哈希、视图名、画板、尺寸和文件哈希。
