# 鼠王关首局整理

使用 `$gameplay-route-analysis` 的首局修订模式。读取 `鼠王关玩家路线图001.ai`、`shuwangguan.graph` 和 `2026-11-14 20-03-35.mp4`；不要复制原始 AI。项目最终只保留原件与 `outputs/ratking_run-001/ratking_run-001_edited.ai` 两份 AI。

已确认：绿色 Spawn 是起点，沿已画路线前进，在左侧靠近 Transform 的线段末端结束。总体方向是用户确认；局部接缝、交叉、事件时间和重试仍需录像核对。正式 `sequence_index` 仅写核实段，候选顺序另列。

按 Skill 的 Illustrator 和 DepthmapX 工作流执行：导出原生对象与真实 Convex/VGA 数值；至少三点配准后核准房间 ID、可通行连接及指标归属。不能把填色当成 Choice 或 Visibility。

从**最终修改版 AI**导出四组 SVG/PNG：单局路线、战斗事件、Convex Choice、VGA Visual Integration [HH]。各图有图例、数值范围、证据状态、来源和 `run_id`；适合 16:9 PPT，SVG 可用于论文。若数值/配准不合格，图名与 QA 如实降级，禁止伪造热力图。

更新 `maps/ratking/`、`runs/ratking_run-001/`、QA 与导出清单。交付前验证原件哈希、AI 重新打开、图件来源、数据合同、PPT 缩小图和 SVG 放大图。不要开发完整 PCG 生成器。
