# 鼠王关：玩家路线与空间句法分析

本目录是分析项目根。PowerShell 中先切换到本目录，再执行下方命令。

| 目录 | 内容 |
|---|---|
| `source/cad/` | 当前 DWG、DXF；BAK 放在 `backups/` |
| `source/illustrator/` | 001–005 五份原始 AI，保留原名与原始字节 |
| `source/depthmap/` | 当前 `shuwang.graph`；旧版在 `history/` |
| `source/video/001/` | 001 对应录像 |
| `maps/ratking/shuwang/` | 当前 graph 导出、房间几何、配准、指标摘要 |
| `maps/ratking/` 根部 | 旧版分析与配准依据，不能冒充当前 graph 输出 |
| `runs/ratking_run-00N/` | 每局路线、事件、来源清单与候选顺序 |
| [outputs](outputs/README.md) | 五局修改版 AI、六组图件与 QA |
| [tools](tools/README.md) | 当前流程、检查工具与保留的历史脚本 |
| `prompts/` | 首局、新局、多局比较提示词 |
| `docs/history/` | 早期任务书、旧目录说明 |
| `archive/` | 既有开发暂存归档，内容保持不变 |

## 当前数据与限制

当前 graph 是 `source/depthmap/shuwang.graph`；底图是 `source/cad/鼠王关.dxf`。当前 graph 有 11 个 Convex REGION 与 3,468 个 VGA 点。新旧版本不能混用。

每局交付修改版 AI 与路线、事件、Convex Choice、VGA Visibility、Gate Counts、Metric Distance 六组 SVG/PNG。颜色是按真实数值范围等距派生的色阶；Gate Counts 不是玩家通过次数。

002–005 没有对应录像；静态几何候选顺序不能代替实际时间顺序。门洞可通行性与物理尺度仍未在本分析中核实。

## 检查已有成果

```powershell
1..5 | ForEach-Object {
    $runId = 'ratking_run-{0:D3}' -f $_
    py -3.13 -B tools/validate_run.py "runs/$runId"
}
```

## 再生成流程

1. 只读打开 `source/depthmap/shuwang.graph`，将 VGA 与 Convex 导出到 `maps/ratking/shuwang/`。
2. 用 Illustrator 核实原始对象清单，再依次执行：

```powershell
py -3.13 -B tools/prepare_shuwang_runs.py
py -3.13 -B tools/build_shuwang_jsx.py
```

3. Illustrator 运行 `tools/render_shuwang.jsx`；保存、重新打开修改版 AI 后导图。
4. 执行 `py -3.13 -B tools/finalize_shuwang.py` 并逐局检查。

整理目录本身不需要重新渲染或覆盖已有图件。共享工具依赖保留在上级目录原位置。

Godot / PCG 主工程位于 `../03_PCG工程/`。以该工程 `PLANS.md`、`PROGRESS.md` 为准，不从历史任务书重复开发。

## PCG 输入

`../03_PCG工程/` 直接读取本目录的 `source/` 与 `maps/ratking/shuwang/`。不再向上级根目录复制兼容快照，也不要在其他位置维护第二份当前 graph、DXF 或地图导出。

## 已有 QA 差异

整理前五份修改版 AI 以及当前 DXF 的哈希已与历史 manifest 不一致。本次保留现文件与历史 QA，不重新签认。详情见 `../00_课程说明/整理记录/2026-11-26/校验报告.json`。
