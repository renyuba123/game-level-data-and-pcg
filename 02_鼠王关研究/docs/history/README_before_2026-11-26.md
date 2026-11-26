## 项目目录导航（2026-11-20）

- 本目录负责 CAD／AI／graph 原始资料、路线与空间句法分析；下方说明是当前分析流程。
- Godot 与 PCG 主工程：`D:\GODOT Prams\boss-level-pcg`。开发顺序、阶段进度分别以该工程 `PLANS.md`、`PROGRESS.md` 为准，避免从早期任务书重做生成器或旧实验。
- `RatKing_Space_Syntax_PCG_Codex_Brief.md` 是早期研究任务书；其中 Houdini 路线是历史设想，当前 PCG 实施采用 Python + Godot + Depthmap。
- 重复开发暂存副本已移至 [archive/staging/2026-11-20/](archive/staging/2026-11-20/README.md)，独有草案集中在 Godot 的 `drafts/`，不在两处继续开发。
- `.godot-mcp-stage/` 包含工具依赖及绝对路径调用，保持位置；`.npm-cache-godot-mcp/` 是安装缓存。它们不属于关卡源码。
- 当前再生成入口为 `tools/prepare_shuwang_runs.py` → `tools/build_shuwang_jsx.py` → `tools/render_shuwang.jsx` → `tools/finalize_shuwang.py`。旧 `build_ratking.py`、`tools/*first_run*` 和旧渲染器保留用于历史追溯，不能与当前 shuwang 流程混用。生成的 JSX 由对应模板与构建脚本维护。

---

# 鼠王关玩家路线与空间句法

当前权威地图是 `鼠王关.dxf`，当前唯一空间句法数据源是 **`shuwang.graph`**。五份原始 AI（001–005）保持不变；每局的修改版 AI、六组 SVG/PNG 和 QA 位于 `outputs/ratking_run-00N/`。旧 `shuwangguan.graph` 及 `maps/ratking/` 根目录下的旧导出仅供历史追溯，不能用于当前图件或后续 PCG。

新版 `shuwang.graph` 有 11 个 Convex REGION 和 3,468 个 VGA 点。共享建筑底图完整读取 DXF 的 129 条 LINE、2 个 CIRCLE 和 1 个封闭 LWPOLYLINE；两个圆与最右小方框均保留。当前标准数据位于 `maps/ratking/shuwang/`：VGA/Convex 原始导出、房间几何、配准后的渲染数据与指标摘要。`runs/ratking_run-00N/` 分别记录各局原生路线、事件、候选顺序和来源哈希。

每份 AI 包含路线、事件、Convex Choice、VGA Visual Integration [HH]、VGA Gate Counts、Metric Mean Shortest-Path Distance 六类图层。所有格点数值来自新版 graph；图上的十档颜色为真实数值范围的**等距派生色阶**，并非 Depthmap 软件原生阈值。Gate Counts 不是玩家通过次数。002–005 没有对应录像，局部路线顺序和事件编号仅是静态几何候选；001 的静态顺序也不能代替逐帧核实。

## 再生成

1. 从 `shuwang.graph` 导出 `pointmap-data-csv`、`shapegraph-map-csv`、`shapegraph-map-mif` 到 `maps/ratking/shuwang/`。目前使用 Depthmap 官方 CLI v0.9.1；原始 graph 不改写。
2. 用 Illustrator 原生对象检查并导出 001–005 路线/事件清单。执行 `py -B tools/prepare_shuwang_runs.py` 生成共享地图及各局数据；执行 `py -B tools/build_shuwang_jsx.py` 生成 JSX。
3. 由 Illustrator 运行 `tools/render_shuwang.jsx`，保存并重新打开每份修改版 AI，再导出六组图。执行 `py -B tools/finalize_shuwang.py` 记录哈希和 QA，逐局运行 `.agents/skills/gameplay-route-analysis/scripts/validate_run.py`。

`maps/ratking/shuwang/connections.json` 当前不含已核实可通行门洞；CLI 导出的 shapegraph connections 只有表头。游戏物理尺度也未校准。PCG 不应把凸空间接触或图上颜色直接当成已核实的通行边、行为频率或米制距离。
