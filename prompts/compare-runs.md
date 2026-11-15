# 多局路线比较

使用 `$gameplay-route-analysis` 的多局对比模式。输入 `map_id=<...>` 与 run 列表；先核对地图版本、空间 ID、坐标、玩家/难度/重试和每局质量状态。

单局图保持真实路线；多局按小倍图或可核实的通道/空间频次表达，写清样本数、分母和归一化。事件比较需要每次进入或停留时间等合理分母；没有分母只报原始计数。不要把平均路径说成真实路线。

DepthmapX Choice、Integration 和 VGA Visual Integration 分别使用原始数值与独立图例；只有已配准、已验证的局次才进行行为与句法关联。结论标 `observed/derived/hypothesis`。PCG 只输出有数据来源、样本数和验证限制的候选结构目标，不开发生成器。
