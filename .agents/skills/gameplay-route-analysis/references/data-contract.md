# 玩家路线数据合同 v1.1

当前鼠王关共享图数据位于 `maps/ratking/shuwang/`：`vga.csv`、`convex.csv`、`convex_geom.mif/.mid` 是 `shuwang.graph` 导出的原始数据；`rooms.json`、`connections.json`、`summary.json` 和 `render_data.json` 是派生数据。`runs/<run_id>/` 放本局 `route_points.csv`、`events.csv`、`run_manifest.json`；`outputs/<run_id>/` 放该局单个修改版 AI、六组 AI 导出图和 QA。旧 `maps/ratking/` 根目录数据属于 `shuwangguan.graph` 历史版本，不是当前默认输入。

## 路线与事件

`route_points.csv` 保留 v1 字段，增加 `candidate_order`、`sequence_evidence`、`x_ai`、`y_ai`。`sequence_index` 只记录逐段经录像或同等证据核实的正式顺序；未核实时留空，候选连接写 `candidate_order`。`order_status` 为 `verified/unverified`，`confidence` 为 `high/medium/low`。端点来自 PDF 绘制操作时，`source_object_id` 必须注明 `PDF-paint`，不可冒充 Illustrator 原生对象 UUID。

`events.csv` 保留原始图层名、原件对象 ID、AI 页面坐标和地图坐标。沿已画候选路线计算累计弧长，按最近线段投影排序；同一位置优先 Spawn，再按投影距离和原件对象 ID 稳定排序。`event_id` 显示为 `001…N`，数据中可存 `E001…EN`；保留 `original_event_id`、`route_distance_ai_pt`、`route_offset_ai_pt`、`candidate_route_segment` 与 `event_order_status`。重复经过同一点时取首次最近投影并标候选，不能据此推断事件时间。End 单独标注。事件含义未核实时 `event_type=unknown`；`timestamp_s`、`attempt_id` 未核实则留空。`room_id` 只在唯一落入已配准凸多边形时写入。

`run_manifest.json` 记录原件和 graph 哈希、修改版 AI 哈希、总体方向证据、局部顺序状态、视频来源、坐标系、比例状态、图件导出清单。`rooms.json` 中临时 ID 标 `provisional`，没有核准轮廓时 `polygon=null`。`connections.json` 可记录 Depthmap 凸空间图边，但必须用 `passable_door_verified` 单独标记真实可通行门洞是否核实；PCG 不能把未核实边直接当作门洞。

## DepthmapX

`convex_metrics.csv` 至少含 `room_id,depthmap_ref,Choice,Integration_HH,Convex_Connectivity,source_graph_sha256,metric_status`；`vga_points.csv` 至少含 `point_ref,x_graph,y_graph,x_ai,y_ai,Visual_Integration_HH,VGA_Connectivity,Gate_Counts,source_graph_sha256`。`Gate_Counts` 映射原始导出列 `Gate Counts`，是 VGA 点指标，单位记 count，不是玩家通过次数。`vga_summary.json` 记录真实数值范围；原始指标图像另存原字节和 SHA-256，清单标明截图/软件导出来源、尺寸、是否嵌入 AI、是否有可读色标。派生矢量色阶另存颜色、数值阈值、图像配准和匹配率；可计算的分位点只作数据摘要，不能自动作为原图颜色阈值。缺失值留空；`map_transform.json` 记录 graph→AI 变换、控制点、残差、容差和单位状态。路线/事件的 `x_map,y_map` 使用 graph 坐标，`x_ai,y_ai` 使用 PDF 兼容的 AI 页面坐标。未通过配准的数据不得与路线做空间统计。

每个导出值标注 `observed/derived/hypothesis` 或 `needs_review/unavailable`。PCG 仅消费核准的空间拓扑与有来源、样本数的候选目标。
