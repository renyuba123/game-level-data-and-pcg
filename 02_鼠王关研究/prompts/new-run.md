# 鼠王关新增局

使用 `$gameplay-route-analysis`。输入 `run_id` 和该局原始 AI；保留原件，仅生成该局一份修改版 AI。复用 001 已验证的 DXF 底图、`source/depthmap/shuwang.graph` 导出、房间 ID、坐标变换、指标图层与图例，不重复生成共享地图。**所有 graph 指标必须来自当前 `source/depthmap/shuwang.graph` 哈希对应的导出**；版本变化时先更新共享数据与全部五局图件。

从本局 AI 原生 Route、Spawn、`ori_events` 提取路线与事件；只把本局对象放进本局修改版。Spawn 编 001，其余按静态路线候选顺序编号，End 单独标注。没有录像时只标几何候选，不填时间、动作或重试事实。每类图以 `*-Labels` 为父层；保存并重新打开 AI 后导出路线、事件、Convex Choice、VGA Visibility、VGA Gate Counts、Metric Mean Shortest-Path Distance 六组 SVG/PNG。运行验证器，报告断接、房间归属和门洞未核实项。
