# Phase 4：单亲抽样的等预算工程对照

## 协议

A 沿用当前档案抽样，权重为 `1 / [Pareto 层级 × (1 + 历史子代请求数)]`。B 每代随机排定 6 个重点位和 2 个探索位。重点池最多 8 张，按当代前沿与累计前沿各目标最优先入池，再用拥挤度填充，按 Layout 哈希去重。单项并列和拥挤度并列按个体 ID。探索池优先使用重点池之外的有效档案，池为空时回退至原档案权重，并记录回退。A、B 的参考编辑和其他算子沿用同一规则。C 每个请求由固定随机键独立抽取生成 seed，运行相同生成与几何验证，再使用同一评价和 Pareto 统计。几何失败占一次请求。

三组共享 G0 的 8 个布局，锁定 `near_1_-1`、地图 1.5 倍、400 图纸单位网格及 3 种策略 × 4 个固定情景。各跑 G0–G20，每组 168 次评价请求。S/F/P/D 越高越好，Q 供展示。主指标是把四个分数除以 100 后，以原始分的固定零向量为参考点计算累计非支配覆盖体积。每代新进前沿比例的分母是该代所有请求，汇总只计 G1–G20。拓扑类别按房间邻接无标签图精确判同构。

## A 组归档基线

- 路径 `F:/大学作业/游戏空间设计微专业/04_PCG实验输出/runs/shell_local_g20_pop8_20261125_143448_831`。
- Git `19ce0bf09839cc476c41e727aed31c43d9be4e11`。配置哈希 `f163fd7be210f73b59014a3fba52e0473b28fb22275fa4438a64b20812b08392`。
- 以登记的旧版本重新核验 G0–G20，`complete=true`。评价证据哈希与原始验证一致，为 `abace06fadaa6832b7769b8ce88622c4fc9f3a91af692f4a8b8f21c6df4e4a6b`。8 个 G0 的布局、分项、空间对照与逐局哈希均与 B 的试跑一致。
- G3 的 `single-3-07` 为历史最高 Q（66.21）。G2／G20 幸存者均值 58.74／58.72。160 次子代请求中有 119 次抽到上一代幸存种群之外的亲代。累计超体积 G0 为 0.146057，G20 为 0.176610。

## G0–G2 验收

`shell_sampling_focused_smoke_v1` 先用 4 个工作进程提交 G0 并退出，第二个进程续跑到 G2。G1、G2 各有 6 个重点位、2 个探索位、0 次抽样回退，16 个子代各记录一个亲代。24 次请求中，23 个得到完整评分，1 个几何无效。共新增 276 局 Godot、460 次 DepthmapX 调用，6 个子代实际改变拓扑。用 2 个工作进程从归档重新构建，三代哈希匹配，证据哈希为 `ae605a132ee47d22855c91e326c026240ee4fec126b76c497730fe1193459c70`。Viewer 的 Streamlit 集成测试在 G2 显示 24 个节点，同屏包括当代最高、历史最高和当代均值。10 项引擎回归和 8 项 Viewer 回归通过。B 的 G2 累计超体积为 0.158765，完整 G20 对照另行归档。

## 本地运行和验证

```powershell
Set-Location 'F:\大学作业\游戏空间设计微专业\03_PCG工程'
$pcgPython = '.\evolution\.venv\Scripts\python.exe'
$archiveRoot = 'F:\大学作业\游戏空间设计微专业\04_PCG实验输出\runs'
$baseline = Join-Path $archiveRoot 'shell_local_g20_pop8_20261125_143448_831'
$focused = Join-Path $archiveRoot 'shell_sampling_focused_g20_v1'
$random = Join-Path $archiveRoot 'shell_sampling_random_g20_v1'

# 验收试跑，首次提交 G0 后退出，再恢复到 G2
& $pcgPython -B -m full_pcg experiment --config configs/shell_sampling_focused_smoke.json --through 0
& $pcgPython -B -m full_pcg experiment --config configs/shell_sampling_focused_smoke.json --resume
& $pcgPython -B -m full_pcg verify --run (Join-Path $archiveRoot 'shell_sampling_focused_smoke_v1') --workers 2

# 首次启动 B、C，各用一个 PowerShell 窗口
& $pcgPython -B -m full_pcg experiment --config configs/shell_sampling_focused_g20.json
& $pcgPython -B -m full_pcg experiment --config configs/shell_sampling_random_g20.json

# 完成后核验并复算对照指标
& $pcgPython -B -m full_pcg verify --run $focused --workers 4
& $pcgPython -B -m full_pcg verify --run $random --workers 4
& $pcgPython -B -m full_pcg.viewer.sampling_report --baseline $baseline --focused $focused --random $random --output (Join-Path $archiveRoot 'shell_sampling_comparison_v1.json')
```

已登记的实验中断后，用同一 `--config` 加 `--resume`。若要重新做一组实验，复制配置并改用新的 `run_id`。A 组的历史核验使用登记的 19ce0bf 版本，避免当前版本的严格实现哈希检查拒绝旧归档。

试跑验收后也可以执行 `& './tools/run_phase4_sampling.ps1'`。它按登记状态启动或续跑 B/C，并在两组完整验证后输出 `shell_sampling_comparison_v1.json` 和 `shell_sampling_comparison_v1.md`。每组的启动日志与归档目录并列。

Viewer 从既有的独立 Python 环境启动。示例查看 B 组，端口 8503 须空闲。查看 C 时把 `$focused` 换为 `$random` 并另选端口。只显示已提交的代次。

```powershell
$env:PYTHONPATH = (Get-Location).Path
$pcgViewer = Join-Path $env:LOCALAPPDATA 'RatKingPCG\viewer\Scripts\python.exe'
& $pcgViewer -B -m streamlit run full_pcg/viewer/app.py --server.address 127.0.0.1 --server.port 8503 --server.headless true --browser.gatherUsageStats false -- --run $focused
```

## 判读

同一优化种子的三组差异属于工程证据。B 若对 A 增加新子代进入累计前沿的比例，并超过 C 的最终累计超体积，再用独立预算对照单步局部编辑。如未达到，按子代证据缺失、失败类型、父子分项变化与算子分别检查。正式 Phase 5 预算保持独立。

## G20 实测结果

| 组别 | G20 累计超体积 | G1–G20 入前沿 | 完整评分 | 无标签拓扑 | 历史最高 Q | G20 幸存 Q 均值 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A 档案抽样 | 0.176610 | 74/160 | 146/168 | 19 | 66.21 | 58.72 |
| B 重点抽样 | 0.205961 | 75/160 | 157/168 | 20 | 67.81 | 60.38 |
| C 独立随机 | 0.183708 | 33/160 | 118/168 | 31 | 67.02 | 56.94 |

B 的最终超体积比 A 高约 16.6%，比 C 高约 12.1%。B 的历史最高 Q 在 G18（`single-18-02`），提高的分项极值主要是 F、P、D。C 保留了更多不同拓扑，也取得略高于 B 的 P 极值。B 比 A 多一个新布局进入当代累计前沿，这项差异很小。按本轮预登记门槛继续做单步局部变异对照，正式 Phase 5 仍按项目准入条件推进。

A/B/C 分别执行 1908／1944／1728 局 Godot 实战，3180／3240／2880 次 DepthmapX 调用，登记运行时间 77.5／55.4／55.2 分钟。A 使用 1 工作进程，B/C 各用 4 工作进程并行，墙钟时间不宜直接用作效率排名。B 使用 120 个重点位、40 个探索位。

B/C 使用登记提交 `0222e5b` 重建验证 G0–G20。B 的评价证据哈希为 `138d756f79eee86ee127ba3157742f01848c78c7638bf37b76363e9888820179`。C 为 `e001c6c4ee547998fb4340acde5fbba9f0fb97bf3473e84d61b0959171d3b4c7`。逐代与算子统计见归档根目录下的 `shell_sampling_comparison_v1.json`，同目录有 Markdown 初报。

## 单步局部编辑小试验

使用已核验 B 组 G0–G2 作为 24 请求对照。新组沿用同一批 G0、同一重点抽样、区域重排、参考编辑和评分。仅对 `diff` 将 1–3 次编辑替换为最多一次 `shift_opening` 或 `move_partition`。移动分隔时，依赖几何仍按原生成器重建。G1 对同一真实亲代和固定随机键下的局部编辑做配对比较。G2 的亲代池可能已经分叉，报告整组累计超体积和完整率。

```powershell
& $pcgPython -B -m full_pcg experiment --config configs/shell_sampling_single_step_smoke.json
& $pcgPython -B -m full_pcg verify --run (Join-Path $archiveRoot 'shell_sampling_single_step_smoke_v1') --workers 2
```

单步组已登记时，用同一配置加 `--resume`。旧 G20 归档的完整重建使用登记版本：A 为 `19ce0bf`，B/C 为 `0222e5b`。单步编辑上线后仍可从现行代码重新汇总旧记录的对照指标，归档重建继续严格匹配登记的实现。

| 同预算 G0–G2 | 原局部变异 B | 单步局部变异 |
| --- | ---: | ---: |
| G2 累计超体积 | 0.158765 | 0.153619 |
| 历史最高 Q | 65.98 | 65.98 |
| 完整评分 | 23/24 | 22/24 |
| 实际拓扑变化 | 6 | 5 |

G1 八个请求的亲代全匹配。四个局部编辑位置中，有两个移动后 Q 变高，一个提交同一布局，有一个证据不足。最大单项案例 `single-1-04` 移动分隔后 Q 由 45.90 到 60.36。原局部变异的 G2 前沿覆盖更高，本轮保留原 B 的策略作为后续候选口径。单步保留为可选的局部诊断算子。

单步组 276 局 Godot、460 次 DepthmapX，六次实际 `diff` 均仅包含一个允许编辑。G0–G2 使用两工作进程重建核验通过，评价证据哈希 `f5ac0b9ecb8d204cf937f638a0414f91437bea48839ee7929fd7be82c99697df`。11 项引擎回归通过。

## G20 Viewer 验收

初次全谱系回放超出测试的 60 秒限时。批量构建 Plotly 图层并为长跨度血缘线提供无穿卡的外侧绕行后，用真实 B/C 归档执行 Streamlit 集成测试，从启动到 G20 分别用时 6.90／2.05 秒，两组各读取 168 个节点。9 项 Viewer 回归通过。B 在 [8503](http://127.0.0.1:8503/)，C 在 [8504](http://127.0.0.1:8504/)。
