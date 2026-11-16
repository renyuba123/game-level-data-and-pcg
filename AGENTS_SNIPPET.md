# 可添加到项目根目录 AGENTS.md 的片段

## 玩家轨迹与空间分析
当任务涉及玩家路线图、Illustrator Route 图层、多局游玩、事件分布、DepthmapX 指标叠加或轨迹数据进入 PCG 时，优先使用项目中的 `$gameplay-route-analysis` skill（`.agents/skills/gameplay-route-analysis/SKILL.md`）。

- 所有原始 `.ai/.dwg/.dxf`、录屏和 `.graph` 保留原件；每次生成使用独立 `run_id`，不得覆盖已有路线。
- 不能凭一条 Illustrator 折线推断完整时间顺序、事件意义或玩家速度；缺失数据必须明确标记。
- 路线、美化、行为统计、空间句法和 PCG 规则分别留痕；仅在完成数据验真后推导更高级统计。
- 导图保留统一底图、空间 ID、完整图例、版本编号与 QA 报告。
- 当前鼠王关只保留原件与一份修改版 AI；原件只读，直接在唯一修改版上迭代并记录哈希与导出图层。
