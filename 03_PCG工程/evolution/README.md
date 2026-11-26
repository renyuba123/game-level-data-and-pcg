# Depthmap 反馈进化

本目录是现有 Godot 房型生成器的搜索层。Godot 输出唯一的多边形/门洞/障碍数据，DepthmapX 0.9.1 计算真实 VGA 与 Metric；pymoo 混合变量 GA 使用 NSGA-II 的非支配排序与拥挤度生存选择。不是官方关卡源码，也不声称找到全局最优。

## 编辑器

打开 `scenes/Main.tscn`，选择根节点。在 **Evolution** 区域可以运行 16 候选试跑、运行/恢复完整搜索、选择 Balanced / Exploration / Pressure、刷新候选。`Candidate File` 也可载入任意已导出的候选 JSON。生成布局直接出现在 Main 的编辑器视口；候选有代数、网格和目标分数标签。

任务在独立 Python 进程运行，默认四个评分工作进程。状态在 `evolution/status.json`，详细日志在 `search_console.log`。候选生成完成前选择预设会提示文件尚未生成。修改代码/基准后须使用新的运行名称，不能混入旧结果；运行期间来源或评分实现变化会停止当前搜索。具体证据与未完成项见 [QA.md](QA.md)。

## 命令（项目根目录 PowerShell）

```powershell
$python = '.\evolution\.venv\Scripts\python.exe'
& $python .\evolution\calibrate.py --grid 400
& $python .\evolution\pilot.py
& $python .\evolution\search.py --name search_v1
& $python .\evolution\report.py search_v1
& $python .\evolution\calibrate.py --grid 200
& $python .\evolution\refine.py search_v1
& $python .\evolution\check_runtime.py
& $python .\evolution\test_pipeline.py
```

默认种群 32、20 代、种子 11/29/47；每组配相同候选评价预算的随机对照，共 3840 次候选评价（缓存命中和廉价淘汰也占评价预算）。先粗网格 400，最终候选单独以 200 网格复核；两种网格的分数不能混排。小规模调试可加 `--population 16 --generations 3 --seeds 11 --name smoke_v2`。

每代保存 `checkpoint.pkl` 和 `history.json`，重跑相同命令会恢复。只加载本项目自己生成的 pickle。要停止，创建对应运行目录中的空文件 `STOP`；当前代完成后退出。删除 STOP 后可继续。运行完成后用 report 导出预设和比较图；没有通过公平性约束的候选时，报告明确失败，不发布合格预设。

## 数据与评价合同

- 唯一来源：`鼠王关.dxf`、`shuwang.graph`；运行验证来源 SHA-256，原件不修改。称为“鼠王关重建模型基准”。图纸坐标除以 1000 进入 Godot，真实物理尺度尚未核实。
- 11 个空间、6 个 through、3 个 break、2 个 block；显式进化长宽、斜边、削角、支路次序、开口宽度/位置、连接类型、一个可选普通通路、障碍位置和出生房间。角色尺寸、速度、交互时间固定。
- through 在初始状态保留 0.9 m 窄缝供视觉分析，玩家交互耗时 0.65 s，Boss 撞开耗时 2 s；break 初始完全封闭，玩家不能破坏，Boss 耗时 3 s；撞开后双方可通行。block 参与碰撞、绕行、遮挡。
- 评分使用真实 `Visual Integration [HH]`、`Connectivity`、`Metric Mean Shortest-Path Distance`，分别评价初始/全开状态。比较固定分位数和大厅/廊道/支房/终端的空间分布，归一化尺度固定来自同网格基准。
- Gate Counts 生成参数未核实、Convex Choice 尚未建立重算一致性，**都不进入适应度**，也不以房间连接度冒充 Convex。原 graph 重算存在小幅数值差异，见 calibration 文件。
- 体验评价目前是明确标注的二维净空网格追逐代理：直奔出口、远离 Boss、寻找视线遮挡三种策略；独立训练/复核扰动种子。并非真实玩家体验或完整 Godot 战斗。近距离可见压力、逃脱/过早被抓/卡住、房间覆盖和路线差异形成多目标。
- 无几何通路、出生过近、无效 Depthmap 数值的候选淘汰；训练中 3 s 内被抓、卡住、六次模拟均不能逃脱的候选违反公平性约束。高压力不能越过这些约束。
- 深度分析以语义几何与 CLI/网格/实现哈希缓存；改变模拟不会强制重复相同几何的 Depthmap 分析。每个结果保留原始 CSV、命令日志和来源。

## 结果边界

`comparison.png` 比较相同评价预算下的结构距离和有效比例；不能仅凭曲线声称游戏体验优于原版。`pareto.json` 保留多目标候选；预设可能指向同一候选，报告会保留真实 key。200 网格复核、独立扰动追逐及实际 Godot 穿门测试是不同检查，须分别报告。最终仍需基准/候选交叉顺序玩家试玩。

参考：[pymoo 混合变量](https://pymoo.org/customization/mixed.html)、[Depthmap CLI](https://github.com/varoudis/depthmapX/blob/master/docs/commandline.md)、[多目标地图进化](https://doi.org/10.1145/1814256.1814259)。

## 已完成的首轮实验（2026-11-19）
完整结果与最终验收见 [FINAL_REPORT.md](runs/search_v1/FINAL_REPORT.md)。3840 次评价已完成；两个不同候选通过最终验收，Pressure 与 Balanced 共用一个候选。Main 已载入最终 Balanced。最终图表为 final_comparison、candidate_metrics、candidate_layouts（PNG/SVG）。
复核完成结果可运行 finish_validation.py；重建实验图表运行 final_report.py，再运行 candidate_report.py。不要将新的评价规则混入 search_v1。

