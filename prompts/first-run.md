# 鼠王关首局整理

使用 `$gameplay-route-analysis` 的首局修订模式。读取 `鼠王关玩家路线图001.ai`、`shuwangguan.graph` 和 `2026-11-14 20-03-35.mp4`；不要复制原始 AI。项目最终只保留原件与 `outputs/ratking_run-001/ratking_run-001_edited.ai` 两份 AI。

已确认：绿色 Spawn 是起点，沿已画路线前进，在左侧靠近 Transform 的线段末端结束。总体方向是用户确认；局部接缝、交叉、事件时间和重试仍需录像核对。正式 `sequence_index` 仅写核实段，候选顺序另列。

按 Skill 的 Illustrator 和 DepthmapX 工作流执行。Depthmap 使用本机 `C:\Users\人于八\Downloads\空间句法软件及练习文件\Depthmap+ Beta 1.0.exe` 打开原 `.graph`；导出原生 AI 对象与真实 Convex/VGA 数值。至少三点配准后核准房间 ID、凸空间图边和指标归属；实际可通行门洞另外核实。不能把填色当成 Choice 或 Visibility。

事件图复用 AI 的 `ori_events` 原生图标，Spawn 从原件路径复制；不要生成替代符号。沿候选路线投影累计距离编号 `001–024`，Spawn 为 `001`，终点旁 Hunting Pistol 为 `024`，End 独立标注。保留原件 UUID，并核对编辑版对象映射；候选编号不表示事件时间。

AI 图层以每图的 `*-Labels` 为父层，收纳该类别图形、图标、编号和图例，共用底图/墙体独立。从**最终修改版 AI**导出五组 SVG/PNG：单局路线、事件、Convex Choice、VGA Visual Integration [HH]、VGA Gate Counts。本局 Gate Counts 恢复白底矢量格点图：3,462 个点及 4–7,230 count 来自 VGA TXT，使用 `maps/ratking/gate_counts_depthmap_original.png` **优先校准原生颜色与空间分布**，以 `gate_counts_palette.json` 中记录的 10 档数值阈值重绘；不得用等频分位数造成大面积红色。原图截图只作配色核对，不嵌入最终图；阈值标为图像匹配所得，不能冒称 Depthmap 官方阈值。墙体、格点、图例均保持矢量；在 PPT 尺寸及放大 SVG 中对照原图检查红色是否只集中于右侧。数值/配准不合格时如实降级并写 QA。

更新 `maps/ratking/`、`runs/ratking_run-001/`、QA 与导出清单。交付前验证原件哈希、AI 重新打开、图件来源、数据合同、PPT 缩小图和 SVG 放大图。不要开发完整 PCG 生成器。
