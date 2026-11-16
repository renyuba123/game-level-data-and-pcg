# 玩家路线、Depthmap 与 PCG 分析工作区

当前首局案例是《最后生还者 2》鼠王关。项目 Skill 在 `.agents/skills/gameplay-route-analysis/SKILL.md`；复用提示词在 `prompts/`。鼠王关的 AI **恰有两份**：原件 `鼠王关玩家路线图001.ai` 和 `outputs/ratking_run-001/ratking_run-001_edited.ai`。原件不改写。

## 当前交付

- `outputs/ratking_run-001/`：唯一修改版 AI、直接由它导出的五组 16:9 SVG/PNG、原件图标对象映射 `icon_audit.tsv`、`FINDINGS.md` 和 `QA_REPORT.md`。Gate Counts 图以原始 Depthmap 截图校准 10 档色阶，再用真实 VGA 点值绘制白底矢量格点；派生阈值见 `maps/ratking/gate_counts_palette.json`。
- `maps/ratking/`：Depthmap+ 导出的 Convex 属性/几何/网络、VGA 点数据、graph→AI 配准、9 个房间和 9 条图边。
- `runs/ratking_run-001/`：44 段路线的 88 个端点、24 个事件标记、候选顺序、来源哈希、逐项 QA 和房间统计。

这里的路线箭头代表基于用户确认的整体方向和静态端点连续性得到的**候选局部顺序**。未逐帧核实的时间戳和正式 `sequence_index` 为空。单局图不能称作玩家频率热图。`FINDINGS.md` 分开写观察、计算与空间设计假设。

## 重做流程

1. 读 `prompts/first-run.md` 或新增局提示词，并按 Skill 选择工作流。原生 Illustrator 对象由 `tools/inspect_native_ai.jsx` 读取；`tools/revise_first_run.py` 从原 AI PDF 兼容视图和原生 UUID 生成候选路线与事件。
2. 使用用户提供的 `C:\Users\人于八\Downloads\空间句法软件及练习文件\Depthmap+ Beta 1.0.exe` 打开 `shuwangguan.graph`。在 GUI 里激活 Convex/VGA 图层，使用 `Map > Export` 导出。具体格式见 Skill 的 `references/depthmapx-workflow.md`。
3. `py -3.11 tools/register_depthmap.py` 校准坐标、验证误差并生成稳定房间 ID、拓扑和标准化指标。`py -3.11 tools/summarize_first_run.py` 计算有来源的单局描述量。
4. `py -3.11 tools/order_events_along_route.py` 根据候选路线空间顺序给原始事件重新编号；保留原件 UUID 和未核实时间状态。`py -3.11 tools/build_illustrator_script.py` 生成 JSX；用 Illustrator 2026 执行 `tools/render_ratking.jsx`，复用原件图标、按 label 收纳图层，并保存到**现有唯一修改版 AI**。`tools/export_figure_views.jsx` 重新打开保存的 AI，导出五组 SVG/PNG。`tools/run_illustrator.vbs` 是 Windows COM 入口。
5. `py -3.11 tools/finalize_first_run.py` 更新文件哈希及图层视图清单，再运行 `py -3.11 .agents/skills/gameplay-route-analysis/scripts/validate_run.py runs/ratking_run-001`，并检查 PNG 整页与 SVG 放大效果。

`Depthmap+` 的 MIF 虽声明 `NonEarth Units "m"`，游戏内物理尺度没有校准。Convex 图边和实际可通行门洞分字段存放；后续 PCG 只应使用已核实的门洞。环境、导出错误和仍待录像确认的项目以 `QA_REPORT.md` 为准。
