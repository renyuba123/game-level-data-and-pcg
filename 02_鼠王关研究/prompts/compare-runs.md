# 鼠王关 001–005 比较

使用 `$gameplay-route-analysis`。只比较使用同一 `source/depthmap/shuwang.graph` 哈希、同一 DXF 和稳定 R01–R11 ID 的局次。保留每局真实路线；静态候选顺序与录像核实顺序分开，不能用跨局事件编号匹配动作。按原生对象 ID、事件类型、房间和明确的分母计算统计；没有录像时间时不估算停留时长。

Convex Choice、VGA Visual Integration [HH]、Gate Counts、Metric Mean Shortest-Path Distance 用相同真实数值范围与明确标注的派生色阶。Gate Counts 不是玩家经过次数；单局图也不是访问热图。当前 shapegraph connection 导出没有边数据，真实可通行门洞仍待核实，不能直接生成 PCG 通行约束。输出观察、计算结果和设计假设，注明样本数、来源哈希及不确定性。
