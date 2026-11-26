> 状态索引（2026-11-20 整理）：本文件正文按时间保留历史过程。首轮 `search_v1` 已于 2026-11-19 完成 3840 次旧协议评价，最终结果以 [FINAL_REPORT.md](runs/search_v1/FINAL_REPORT.md) 为准。下文“正在运行”“尚未结束”及早期单一预设描述均指当时状态，不是当前状态。新版战斗协议开发见 [PROGRESS.md](../PROGRESS.md)，不沿用本实验分数。

# 实施与核验记录（2026-11-18）

## 当前状态

Godot 参数生成、真实 Depthmap VGA/Metric、追逐代理、多目标进化、随机对照、缓存/断点、精网格复核和 Main 编辑器载入已经接通。正式作业 `search_v1` 正在运行：32 个体 × 20 代 × 3 个随机种子，并配相同评价预算的随机对照，共 3840 个评价名额。

**整个作业尚未结束，不能报告最终收敛或相对随机对照的胜出结论。** 实时状态见 `status.json`、日志见 `search_console.log`。后台流程结束后自动生成报告、精网格复核、真实门洞测试；失败会写入状态。

## 已取得的证据

- `pilot/summary.json`：16 个候选中 13 个通过几何、净空和 Depthmap 检查，3 个出生距离过近。四进程耗时 84.35 秒，Depthmap 缓存命中为 0。公平性是后续独立约束，13 个不等于 13 个推荐关卡。实测外推完整作业约 5.6 小时，仅为估计。
- `runs/smoke_evolution/`：早期评分器完成三代进化和等预算随机对照，各 48 次评价，验证迭代及断点。其净空采样和路线评分后来修订，不能与正式版混排。
- 当前三个预设实际指向同一个早期候选，尚不是三种风格。该候选已用最终评分器完成 200 单位复核：结构距离约 0.237813、公平性损失 0、压力损失 0.5、路线多样性 0.136364。独立扰动的六次代理模拟全部逃脱、无过早捕获和卡住，但近距离可见追逐占比为 0，因此它只是低压力流程样例。
- `acceptance.json`：该候选 9 个特殊门洞全部通过初始阻挡、Boss 撞开、双方开放状态和 Boss 实际穿越检查。测试使用真实 Godot 碰撞与 Boss 更新，关闭战斗结束条件以单独检查穿门。
- `squeeze_test.json`：玩家交互可穿过 intact through，一次挤身不会永久打开通道，返回仍需再次交互。只有 Boss 撞开才永久开放。
- `runtime_checks.json`：现有追逐测试和 Main 编辑器预览刷新通过。编辑器 MCP 已确认候选、代数、评分和正式任务状态可读，原有手动 seed 保留。
- `test_pipeline.py`：五项回归通过，包括窄走廊、转角运动轨迹、障碍外填充点、同参数可复现、原始 DXF/graph 哈希不变。

## 基准差异

在原 `shuwang.graph` 内直接重算：Connectivity 最大差异 0；Visual Integration [HH] 最大差异 0.0273132；Metric Mean Shortest-Path Distance 最大差异 0.21 图纸单位。

从 DXF 重建 200 单位点图时，初始和全开状态均为 3468 个点，与历史 CSV 点坐标集合完全一致，但指标不完全相同：

| DXF 重算条件 | Visual Integration 最大差异 | Connectivity 最大差异 | Metric 最大差异 |
|---|---:|---:|---:|
| 初始，break 封闭 | 8.5250083 | 635 | 4262.0663 |
| 全部撞开 | 0.732504 | 22 | 3.1465 |

历史 graph 的开口状态没有独立记录。全开条件更接近历史数据，但不能据此宣称状态已确认或几何已完全复现。**优化使用新初始/全开条件下重算的 DXF 基准**；每种网格有独立基准，历史 graph 值保留用于校准审计。详见 `baseline/calibration_200.json`。

填充点修复了左侧圆障碍和右端墙线方柱内部被分析的问题；现在只从历史 VGA 确认的空地点选取，并优先远离墙和障碍。没有删掉无效值来伪装分析通过。

## 结论边界

- Gate Counts 生成参数未核实，Convex Choice 尚未验证重算一致性；两项均不计分，也不拿房间连接度替代 Convex。
- 追逐是二维净空网格代理，不是人类体验或完整战斗。没有“优于官方”的证据。
- 图纸单位 / 1000 是暂定 Godot 尺度，真实物理尺度未核实。
- 尚未进行玩家交叉试玩；压力、公平性和体验仍需玩家实测。
- 原始 DXF、graph 和 AI 未修改。新增 Godot 实现、依赖和结果都在本工程；原代码实施前快照在 `source_snapshot/`。

## 2026-11-19 续算与编辑器修复

原作业在 seed 29 的第 8 代遇到 BrokenProcessPool，已完成 seed 11 的进化/随机各 20 代和 seed 29 的前 7 代。保留原失败日志为 search_console_20261118_failure.log；现以两个工作进程从断点恢复，评分、随机种子和评价预算不变。异常退出的根因未确认，降并发是运行缓解措施。

第一组同预算结果见 runs/search_v1/first_seed_comparison.json：各 640 次评价；进化有 198 个满足约束的候选，随机有 60 个。可行候选最佳结构距离分别为 0.130998 / 0.157140；最佳压力损失分别为 0.073611 / 0.004762；最大路线多样性分别为 0.460606 / 0.547475。这些极值来自不同候选，且仅一组随机种子完成，不能宣称进化全面胜出。

Main 的旧 ScriptEditor 文本缓冲曾在保存场景时覆盖磁盘新脚本。已关闭旧编辑器、恢复实现、重新启动并重新保存，验证保存前后 main.gd SHA-256 均为 EB27D1B9FFFECF7FAD2E35E695D93AB111AD4F365C6D6F8EEE87FD0761209018。用户手动 seed 94、候选选择与实时预览保留。重新运行追逐和编辑器预览测试均通过；恢复用源码与脚本保存在 source_snapshot/。

### 第一组中期候选行为复核

已生成 first_seed_comparison.png/SVG，均只包含 seed 11 各 640 次评价。均衡候选 3b15c030… 的 200 单位结构距离为 0.176267，压力损失 0.251852，路线多样性 0.330303；实际 9 个特殊门洞全部通过。

但独立测试只有 2/6 次逃脱（直奔出口约 2.2 秒），其余 4 次约 3.6 秒被抓，无卡住。它虽然避开旧的 3 秒过早捕获门槛，却未满足独立测试的公平性目标，因此只保留为诊断候选 reviewed_seed11.json，没有升级 Main。详细结果在 runs/search_v1/seed11_review/result.json。

最终 report.py 增加导出验收：在三类候选各前五名组成的有限候选集中，要求 heldout fairness_loss <= 0，即至少半数逃脱且无过早捕获、卡住或超时；不通过时不发布新推荐预设，并写出 heldout_export_review.json。这是看到中期问题后新增的事后验收，不是预注册结论，也没有改变当前搜索的适应度和预算。完整导出流程尚待搜索结束实际执行。3 秒边界和过短的逃脱路线仍需在后续评价版本中校准，不能把通过数值门槛当作体验已经优良。


## Final delivery 2026-11-19
120 batches / 3840 evaluations completed. Final fine-grid, heldout, 18 gate crossings, all-room Godot navigation and 5 regression checks passed. Two unique presets; pressure aliases balanced. See runs/search_v1/FINAL_REPORT.md for mixed results versus random control and metric exclusions. Main reopened from disk; script hash stable after saving.
