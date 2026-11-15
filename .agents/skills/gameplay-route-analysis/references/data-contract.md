# 玩家路线数据合同 v1.1

`maps/<map_id>/` 放 `rooms.json`、`connections.json`、`map_transform.json`、`convex_metrics.csv`、`vga_points.csv` 和配准报告；`runs/<run_id>/` 放 `route_points.csv`、`events.csv`、`run_manifest.json`、`review_needed.csv`；`outputs/<run_id>/` 放单个修改版 AI、从中导出的图与 QA。

## 路线与事件

`route_points.csv` 保留 v1 字段，增加 `candidate_order`、`sequence_evidence`、`x_ai`、`y_ai`。`sequence_index` 只记录逐段经录像或同等证据核实的正式顺序；未核实时留空，候选连接写 `candidate_order`。`order_status` 为 `verified/unverified`，`confidence` 为 `high/medium/low`。端点来自 PDF 绘制操作时，`source_object_id` 必须注明 `PDF-paint`，不可冒充 Illustrator 原生对象 UUID。

`events.csv` 保留原始图层名、对象 ID、原始和地图坐标。事件含义未核实时 `event_type=unknown`；Spawn/Transform 的图层语义与路线起终点确认分别记证据。`timestamp_s`、`attempt_id`、`room_id` 未核实则留空，不写 0。

`run_manifest.json` 记录原件哈希、修改版哈希、总体方向证据、局部顺序状态、视频来源、坐标系、比例状态、图件导出清单。`rooms.json` 中临时 ID 标 `provisional`，没有核准轮廓时 `polygon=null`；`connections.json` 只容纳确认可通行的门洞。

## DepthmapX

`convex_metrics.csv` 至少含 `room_id,depthmap_ref,Choice,Integration_HH,source_graph_sha256,metric_status`；`vga_points.csv` 至少含 `point_ref,x_graph,y_graph,Visual_Integration_HH,VGA_Connectivity,source_graph_sha256`。缺失值留空；列名保留指标全称的映射。`map_transform.json` 分开记录 AI→统一地图坐标和 graph→统一地图坐标的变换、控制点、残差、单位。未通过配准的数据不得与路线做空间统计。

每个导出值标注 `observed/derived/hypothesis` 或 `needs_review/unavailable`。PCG 仅消费核准的空间拓扑与有来源、样本数的候选目标。
