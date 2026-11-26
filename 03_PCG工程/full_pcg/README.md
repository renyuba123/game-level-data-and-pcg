# Full-PCG 开发入口

阶段状态见 [PROGRESS](../PROGRESS.md)。当前外壳布局已通过 Phase 2 校准准入，生成约束见 [PLANS](../PLANS.md) 的 2.2、3.2 与 3.3 节。Phase 3 使用统一 Godot 战斗进行校准，复算和重放命令见 [运行报告](../reports/combat_v3/PHASE3_GODOT_SYNC.md)。

| 入口 | 当前职责 |
|---|---|
| `shell_layout.py`、`room_limits.py` | 当前Main的Python外壳分区与内净尺寸规则，生成同一份权威Layout |
| `godot_export.py`、`godot/layout_decoder.gd` | 当前布局导出及 Godot 解码，支持 window 和同一对空间的独立 Portal |
| `godot/combat_level.gd`、`../scenes/CombatFullPCG.tscn` | 交互、自动批战和输入重放共用的战斗白模 |
| [关卡进化查看器](viewer/README.md) | 查看遗传与随机试跑的逐代档案、Pareto、父子布局和 Godot 轨迹 |
| `topology.py`、`geometry.py`、`operators.py` | 保留的可变锚点图生成基线及可复用算子 |

当前shell可按已有命令从项目根目录生成单图：

```powershell
& evolution/.venv/Scripts/python.exe -B full_pcg/shell_layout.py 159 full_pcg_output/shell_preview_159.json
```

该命令生成并导出单张开发布局。`python -m full_pcg generate --seeds 1:100` 继续运行原锚点图审计。

## 本地单亲遗传工程实验

在 PowerShell 执行以下命令。示例配置每代 2 个请求，G0–G2 共 6 个。它使用已锁定的 `near_1_-1`、`Map Size = 1.5` 和每张有效布局 12 局的既有评分口径。每次新开实验使用独立运行 ID。

~~~powershell
Set-Location 'F:\大学作业\游戏空间设计微专业\03_PCG工程'
$python = Join-Path (Get-Location) 'evolution/.venv/Scripts/python.exe'
$settings = Get-Content -Raw -Encoding utf8 'configs/shell_single_parent_local.json' | ConvertFrom-Json
$settings.run_id = 'shell_local_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff')
$config = Join-Path $settings.output_root ($settings.run_id + '.json')
$settings | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $config -Encoding utf8
$run = Join-Path $settings.output_root $settings.run_id
& $python -B -m full_pcg experiment --config $config
~~~

本地 CLI 不需要 Viewer 或 Codex。要让运行脱离当前 PowerShell 窗口，用以下命令替换上一段最后一行。输出根目录下会保留启动日志，归档中的 `runtime/summary.json` 记录实际 Godot 局数、DepthmapX 调用与耗时。

~~~powershell
Start-Process -FilePath $python -WorkingDirectory (Get-Location).Path -WindowStyle Hidden -PassThru -ArgumentList ('-B -m full_pcg experiment --config "{0}"' -f $config) -RedirectStandardOutput "$run.stdout.log" -RedirectStandardError "$run.stderr.log"
~~~

原进程退出后，用同一配置恢复。首次启动时可添加 `--through 0`，只提交 G0，再用续跑命令完成余下代次。若重开 PowerShell，可按保存的 JSON 文件重新设置 `$config` 和 `$run`。

~~~powershell
& $python -B -m full_pcg experiment --config $config --resume
& $python -B -m full_pcg verify --run $run
~~~

`verify` 重建已提交的各代布局、抽样、编辑和 Pareto 选择，并校验归档证据。另有一份相同输入的运行时，可用 `--compare <另一归档目录>` 比较逐代内容和证据哈希。运行时日志的时钟和耗时各自记录。

查看结果时用 Viewer 环境启动只读回放。已运行的 Viewer 可以保留在原端口。

~~~powershell
$viewer = Join-Path $env:LOCALAPPDATA 'RatKingPCG/viewer/Scripts/python.exe'
& $viewer -B -m streamlit run full_pcg/viewer/app.py --server.address 127.0.0.1 --server.port 8502 -- --run $run
~~~

## 原锚点图模块说明（保留基线）

# Full-PCG v2 development

Independent subsystem. Legacy scripts and search_v1 remain unchanged.

Current implementation: variable planar anchor graphs, room count and shape/rotation, graph edge deletion, explicit portals, deterministic corridor routing and polygon union. Python layout is the single geometry source. Stable room/edge IDs and versioned JSON are used throughout.

Initial anchor sampling uses a grown planar lattice as a packing aid, not a fixed room graph. It is still a geometric prior: the development report must retain this limitation. Existing operators include topology mutation and bounded one-interface crossover; the general multi-interface crossover, shell-Genome adaptation, optimization, replay and complete validation remain pending. Do not describe the initial geometry audit as final Phase 2 acceptance.

Run with the existing evolution virtual environment: `python -m full_pcg generate --seeds 1:100`.
