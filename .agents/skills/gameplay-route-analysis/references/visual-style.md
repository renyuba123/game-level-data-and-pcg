# 玩家路线分析图规范

参考：[Pathways 的箭头、事件与时间切片](https://www.sfu.ca/~shaw/papers/Gagne-Pathways-ICEC11.pdf)；[多局轨迹聚合研究](https://research.jku.at/en/publications/visualization-of-player-movement-patterns-with-line-integral-conv/)。借鉴信息编码，不复制原图。优先保证 16:9 PPT 缩放后可读，并以 SVG 供论文排版。

## 单局图

1. `movement`：中性灰墙体、淡色空间边界、蓝色真实路线、绿色 Spawn、明确终点、少量经核准的箭头与段号。路线交叉处用断开/桥接符号或局部放大，不暗示未知的连通关系。若仅总体方向已确认，图例写明“逐段顺序待核验”。
2. `combat_events`：同底图、淡路线、事件以形状和颜色双编码，图例与事件 ID 对应；无法确认的事件标 `?`，不把武器图层名当作已确认的射击动作。
3. `convex_choice`：真实凸空间边界、ID、DepthmapX Choice 数值及分级色标；若数值未导出则只可称 `convex_regions`，不称 Choice。
4. `vga_visibility`：从真实 VGA 点数据绘制 `Visual Integration [HH]`，注明点网格间距、数值范围和无数据区域；与 Choice 使用不同标题、图例和来源说明。

单局不得输出无分母的“使用频率热图”。有已校对的顺序时可另作房间进入次数图，标题注明 `N=1` 和计数定义。多局图使用小倍图、每局独立色或汇总密度图，写明局数、采样率和归一化方法，不把平均轨迹当成真实路径。

## 图面与导出

- 灰白底图；主路线高对比蓝，约 2–3 pt（按画板实测）；墙体较细，门洞保持可见；数值色标不得复用仅表示房间类别的颜色。
- 每张图有标题、`map_id/run_id`、证据等级、比例/单位状态、指标全称和范围、数据源、图例。事件标签与房间 ID 避开门洞和路线交叉。
- 从同一修改版 AI 的命名视图导出 SVG 和 PNG，使用 16:9 汇报版面；SVG 放大检查路径和文字，PNG 在实际投影大小检查辨识度。导出清单记录 AI 哈希、视图名、画板、尺寸和文件哈希。
