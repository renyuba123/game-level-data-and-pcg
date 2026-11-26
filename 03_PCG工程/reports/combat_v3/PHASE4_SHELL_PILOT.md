# Phase 4.0 鼠王关外壳布局两代工程试跑

**状态：工程闭环通过，正式进化未准入。** 本报告对应 [PLANS §5.3](../../PLANS.md)。遗传组与随机组共用 Generation 0 的 8 张地图，分别产生 Generation 1、2 各 8 次新请求。试跑采用 `near_1_-1`、Map Size 1.5、三种 paced 代理 × 四个场景扰动，共 12 局／有效布局；出生、补给规则和战斗机制保持锁定。评分协议与物理尺度仍为草案，结果不用于正式 6048 次请求预算。

## 执行、归档与复现

| 项目 | 实测 |
| --- | ---: |
| 请求预算 | 遗传 24＋随机 24＝48；其中初始 8 张为共同样本 |
| 唯一 Layout、空间分析结果、评价证书 | 各 39 |
| Godot 实际战斗局数 | 468；另有 1 次无效布局未运行战斗 |
| 同一评价复用 | 随机组 Generation 0 的 8 张共用初始评价 |
| 遗传组完整草案分／证据不足／几何无效 | 20／4／0 |
| 随机组完整草案分／证据不足／几何无效 | 13／10／1 |
| 无标签房间邻接拓扑类别 | 遗传 15；随机 17 |
| 遗传组合法子代中实际拓扑变化 | Generation 1 为 6，Generation 2 为 4 |

完整记录在 `F:\大学作业\游戏空间设计微专业\04_PCG实验输出\runs\shell_draft_pilot_v1\`。每组的 `generation_00.json`–`generation_02.json` 保存全部请求、父代、算子、修复失败、Genome、Layout 哈希、完整幸存种群和当前／累计 Pareto。每张评价的原始战斗局、空间分析结果和评分报告在同一目录的 `evaluation/`、`space/` 下。`registration.json` 登记了 Godot、Depthmap、配置和实现哈希；`overview.json` 的正式请求数为 0。随机组独立采样，`topology_changed` 没有父代可比较，因而 `overview.json` 的随机拓扑变化数为 0；17 类拓扑是对其实际布局做图同构检验的结果。

### 逐代结果

下表的胜／死／超时仅是固定自动玩家的模拟结果。几何无效的候选不产生战斗局；`UNCERTAIN` 表示缺少完整评分证据，不能解释为关卡必然不可胜。每一列的目标最优可能属于不同个体，表中不拼出虚构冠军。

| 组别与代 | 完整／UNCERTAIN／INVALID | 胜／死／超时 | 进入二阶段局数 | 当代拓扑类别／累计类别 |
| --- | --- | --- | ---: | --- |
| 两组共同 Generation 0 | 6／2／0 | 55／38／3 | 77 | 7／7 |
| 遗传 Generation 1 | 7／1／0 | 59／36／1 | 82 | 8／13 |
| 随机 Generation 1 | 3／4／1 | 21／59／4（实际 84 局） | 48 | 6／12 |
| 遗传 Generation 2 | 7／1／0 | 71／23／2 | 80 | 6／15 |
| 随机 Generation 2 | 4／4／0 | 24／63／9 | 46 | 7／17 |

Generation 1 的遗传组 8 张子代中，6 张改变了无标签房间邻接，7 张有可用的 S/F/P/D 草案评分，4 张进入幸存种群。随机组 8 张新样本有 3 张完整评分，2 张进入幸存种群。小规模试跑观察到遗传组较高的完整评分产出与更多自动玩家胜局；随机组累计获得更多拓扑类别。两轮结果不能估计总体优势，也没有通过独立图 70% 胜率门槛。

## 父子布局与战斗复盘

Seed 6 的 `initial-01` 经 `merge(left_inner, left_low)` 成为 `genetic-1-00`，实际房间数 9→8，邻接图非同构。固定 12 局由 8 胜→12 胜，但 F 由 70.7→49.0，P 由 51.0→65.6，D 由 2.8→10.1；胜率上升不能代替公平性判断。相同合并操作作用于 Seed 177 时，`initial-00` 的 12 胜变为 `genetic-1-04` 的 2 胜，说明局部操作的效果依赖原有空间关系。

![同种子父子路线与战斗事件](<F:/大学作业/游戏空间设计微专业/04_PCG实验输出/runs/shell_draft_pilot_v1/parent_child_replay.png>)

图中左右为 Seed 6 的父代与子代，同一世界比例，绿色为开局前 5 秒路线，蓝／橙为两阶段玩家路线，虚线为 Boss 路线。窗口、through、break 与补给位置都来自对应 Layout。图选取两张地图相同的 `occlusion_0` 场景种子，**两张图的代理动作会随地图重新决策，不是强制相同输入的因果实验**。两局均在 0.5 秒首击、约 9.7 秒分裂；父代在第二阶段取弹 2 次、32.2 秒胜利，子代取弹 1 次、24.8 秒胜利。真实逐帧重放分别为 1934／1488 帧，父子各自的状态帧、事件和终局与原记录完全一致。独立矢量图及事件摘要同目录有 `parent_child_replay.svg`、`parent_child_replay.json`。

### 预留 Seed 1102 诊断

`output_110` 的 1088 帧合法输入重放进入第二阶段，12 次命中，结束时 Boss 尚有 398 HP；没有拾取弹药，剩余 0 发，18.13 秒遭大型 Boss 抓取死亡。`output_112` 的 673 帧重放在第一阶段拾取 2 次，仍有 24 发，4 次命中后 Boss 为 796 HP，11.22 秒被抓取。两条轨迹的每帧、事件、终局均与原记录一致，保存在课程工作区 `04_PCG实验输出/diagnostics/shell_pilot_diagnostic_1102/`。这证明失败点不同，尚不能把 Seed 1102 的失利单独归因于布局或代理，亦不能据此声称它不可胜。

## 验证命令与限制

```powershell
& '.\evolution\.venv\Scripts\python.exe' -B -m unittest full_pcg.test_shell_pilot full_pcg.test_shell_genome -v
& '.\evolution\.venv\Scripts\python.exe' -B -m full_pcg.shell_pilot configs/shell_pilot_v1.json 'F:\大学作业\游戏空间设计微专业\04_PCG实验输出\runs\shell_draft_pilot_v1' 'D:\steam\steamapps\common\Godot Engine\godot.windows.opt.tools.64.exe' 'F:\大学作业\游戏空间设计微专业\.tools\depthmapXcli_win64.exe' --workers 2 --verify
& '.\evolution\.venv\Scripts\python.exe' -B -m combat_pcg preflight
```

前三项结果分别为 **3／3 测试通过**、Generation 0–2 重建和归档逐项哈希一致、正式 `allowed=false`。试跑原先以 4 个工作进程执行，验证以 2 个工作进程运行。`registration.json` SHA-256 为 `1ce49c8248d91e35ad47cc55080d6f33a46230acecff02fb5e83ddb1352afc68`，`overview.json` 为 `62b0e92ca11741a5da980f923cb4d03a6c6f1c0cba3c5ed6e50445f9990d78b6`，`reproducibility.json` 为 `70129b7de337cad6b4f04cd976a6d206f78b2851ff8f6bb5d868b9ae3c4d48d6`。主运行记录全部留在实验目录，仓库只保存代码、配置与报告。

本试跑仅采用局部 shell 分区／开口变异，未实现完整可变长度 Genome 交叉、Generation 0–20 查看器或正式评价调度。当前独立校准集 `near_1_-1` 仅 6／24 胜，低于预登记的 70% 门槛；战斗与评分协议以及物理尺度仍待冻结。下一步应按 [PLANS §5.2](../../PLANS.md) 收口 Phase 3，再按 Phase 4 正式门槛扩展结构化算子、完整逐代 Viewer 与独立实验。
