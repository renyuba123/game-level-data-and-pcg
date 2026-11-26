# Phase 4 准入诊断 · Seed 1102 自动取弹与撤离

## 配置和变更

在 Seed 1102 固定白模上登记了四个策略版本，并给每组使用相同的 3 种策略和 110–113 四个场景扰动。固定 `near_1_-1`、Map Size 1.5、Godot 4.7.2／60 Hz 和原布局包。日常运行与正式评价继续使用各自原配置。本实验只有 48 局最终开发对照，另存开工前的 12 局基准及 8 局早期冒烟实验。二次验证使用固定输入回放。地图、战斗数值、S/F/P/D 和遗传预算均未调整。

- `paced_supply_v1`：低弹量时按导航路程、拾取耗时和最近观察到的 Boss 位置判断补给机会。只追已有视野记录的弹药，未发现可用弹药时可沿普通开口探查邻区。由 Godot 实际完成取弹。
- `paced_exit_v1`：取弹后若只有一个直接开放的出口、仍有近期威胁观察，从门洞另一侧选一段可用胶囊扫掠通过的横向退路，走完再交回常规移动和开火。开发冒烟中的首版只跑到出口，很快被转回原侧室并死亡，最终对照加入了过门后的净空距离。
- `paced_tactics_v1`：同时开启两条规则。自主决策写入独立 `policy_decisions`，战斗事件与固定输入重放维持现有口径。没有用场景种子、地图 ID、预录轨迹或隐藏补给的实际坐标决定动作。

## 48 局完整对照

单元格为胜／死／超时。只有进入第二阶段后合法击杀大型 Boss 才计胜。

| 决策版本 | 输出优先 | 遮挡转移 | 补给优先 | 总计 | 进入二阶段 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 原 `paced` | 0／4／0 | 0／4／0 | 0／4／0 | 0／12／0 | 6/12 |
| 只改取弹 | 2／2／0 | 2／2／0 | 0／4／0 | 4／8／0 | 6/12 |
| 只改提前撤离 | 1／3／0 | 1／3／0 | 1／3／0 | 3／9／0 | 9/12 |
| 同时启用 | 3／1／0 | 3／1／0 | 1／3／0 | **7／5／0** | 9/12 |

- **原 `output_110` 18.133 秒死亡。** 只改取弹和同时启用两组均在 10.667 秒取弹、14.517 秒触发分裂、20.433 秒第二次取弹，31.067 秒完整击杀。
- **原 `output_112` 11.217 秒死亡。** 只改撤离和同时启用两组均在 7.083 秒触发撤离，第 452 帧（约 7.533 秒）穿过 `gate_10` 实际开口，第 496 帧位于隔壁且沿横向离开门洞超过 3 m。9.500 秒后续命中，19.200 秒分裂，32.667 秒完整击杀。
- 扰动 111 的三种策略均未触发这两条新规则，在第一阶段 11.283–11.450 秒死亡，终局仍有 14–24 发。组合组另有两局在第二阶段死亡，Boss 分别剩 143／347 HP。没有证据能将这些失败归到同一个决策。

## 核验与准入

- 48 局均通过归档 SHA-256、资源守恒、合法补给与二阶段终局检查。新代码下原策略的 12 局与改动前各自输入、逐帧状态、事件和终局一致。
- 将两条关键胜局在单项和组合中分别固定输入复播。四次均与源对局的全部状态帧、事件及结果一致，涉及 1,864 和 1,960 帧。原 B `single-18-02` 的首帧差异属于另一个已记录问题，本轮没有复核或修复该问题。
- Python `unittest discover -s combat_pcg -t . -v` 共 66 项通过。没有重算四项分数或比较遗传排名。
- 7/12（58.3%）是单张**开发图**的结果。原独立复核仍为 6/24，`preflight` 未通过。两条新规则继续作为显式实验选项。后续调试须将 Seed 1102 归入开发集，并为新版本预登记独立地图及扰动。正式 672／6048 请求本轮均为 0。

## 证据和复跑

证据目录为 `F:\大学作业\游戏空间设计微专业\.phase14-work\seed1102_policy_v1`。四组完整对局有各自的输入、事件、轨迹、Godot 输出和工具／源码哈希。目录内 `smoke` 保留早期版本，`development_matrix` 是上表的最终对照，`replay_matrix` 是固定输入复播。

| 文件 | SHA-256 |
| --- | --- |
| `registration.json` | `57d389c3032b4dbcc9cc86cdd9a039d1cb013a0e77a9b34406ea10537a024c0e` |
| `development_matrix/summary.json` | `321a7d9036acc1797459e559a99b4bb16622731cf87673abd31c62219adc1d3e` |
| `verification.json` | `0e3438102cca9b015e12fa70406df9399b74d886d33d5f8535a138d20464109b` |

```powershell
Set-Location 'D:\GODOT Prams\boss-level-pcg'
$python = '.\evolution\.venv\Scripts\python.exe'
$godot = 'D:\steam\steamapps\common\Godot Engine\godot.windows.opt.tools.64.exe'
$archive = 'F:\大学作业\游戏空间设计微专业\.phase14-work\seed1102_policy_v1'
$invokeScript = "import runpy,sys; runpy.run_path(sys.argv.pop(1), run_name='__main__')"
& $python -X utf8 -B -c $invokeScript (Join-Path $archive 'run_registered.py') $godot
& $python -X utf8 -B -c $invokeScript (Join-Path $archive 'verify_registered.py') $godot
```

运行器发现同版本完整证据时会校验并复用。需要全新实测时，在新的目录内复制 `registration.json`、`run_registered.py`、`verify_registered.py` 和 `paced_before`，以新目录为 `$archive`。既有遗传档案的精确复算仍使用其登记的代码版本和工具。
