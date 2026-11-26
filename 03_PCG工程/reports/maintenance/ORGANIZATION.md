# 项目整理与复用边界（2026-11-20）

本次任务只整理文件和文档，不推进研究阶段，不改实验协议，不提交用户原有修改。

## 文件整理

- 逐文件比较两个开发暂存目录与 Godot 主工程：32 份 SHA-256 相同的文件移入课程目录 `archive/staging/2026-11-20/`，保持原相对路径。
- 9 份独有草案移入本工程 `drafts/`：战斗模块1.4的7份草案、Godot导出与解码的2份草案。新增 `drafts/README.md` 说明接续路径及未验收状态；`.gdignore` 防止草案被 Godot 扫描。
- 没有删除源码或输出。个别原暂存目录的空目录壳清理遇到“拒绝访问”；保留这些目录，不影响已迁移文件，后续不要在原路径继续开发。
- `.godot-mcp-stage/` 的 probe.py 硬编码自身绝对路径，工具依赖保持原位；安装缓存与 node_modules 加入忽略规则。
- 原 CAD、AI、graph、运行输出、Legacy、search_v1、用户场景及进程文件均保持整理前内容。旧输出和缓存不按相同文件名去重，避免损坏版本与实验血缘。
- Godot 忽略 Python 字节码和本地 full_pcg_output；数据仍在本地。后续必要的小型实验清单/哈希显式存入 reports，不能依赖被忽略的大型输出入库。

迁移明细：`organization_moves.json`，含原路径、目标路径、SHA-256。整理前保护快照：`organization_before.json`；整理后结果：`organization_verification.json`。

## 避免重复开发

| 工作 | 复用入口 | 尚需完成／不可混用 |
|---|---|---|
| 新地图几何、导航、图重建、算子 | full_pcg 的 topology/geometry/navigation/geometric_graph/operators | 不另写地图生成器；仍需同场出生、补给和战斗适配 |
| 新评分及空间归一化 | combat_pcg 的 contracts/scoring/spatial | 已有30项合同/评分测试；真实事件采集和校准仍待完成 |
| 战斗配置与命令草稿 | drafts/combat_phase1_4 | 先完成Phase 1.4，不直接宣称接口可用 |
| Godot导出/解码草稿 | drafts/full_pcg_godot | Phase 2审查并测试后迁入正式包，避免重写 |
| 真实空间分析、缓存及选择 | evolution 现有模块，详细决定见 reports/combat_v3/REUSE_AUDIT.md | 复用工具能力，旧逃生语义和分数不能当新版战斗评分 |
| 当前路线图再生成 | 课程目录 tools 下 shuwang 构建／渲染链 | 旧 first_run、旧渲染器保留追溯，不与当前数据源混排 |

## 文档归属与修正

- 根目录 PLANS 是长期规范，PROGRESS 是唯一阶段状态，README 是目录与入口导航。
- PROGRESS、AGENTS 的接续位置改到 drafts；草稿 IMPLEMENTATION_PLAN 保留原文作历史摘要，不另维护一份权威计划。
- Full-PCG STATUS 不再引导跳过Phase 1.4；明确已有局部几何重建证据不等于完整验收，复用已有空间归一化。
- evolution/QA 顶部标明2026-11-19已完成旧实验；正文保留当时运行状态，最终结果以 search_v1/FINAL_REPORT 为准。
- 课程目录 README 标明 PCG 主工程位置、当前分析脚本链和旧脚本边界；早期研究任务书加历史提示，其中 Houdini 方案不再误作当前开发入口。
- 去掉课程目录 .gitignore 重复的 *.mp4 行，增加本地安装缓存忽略。

## 实际核验

- `evolution/.venv/Scripts/python.exe -B -m unittest combat_pcg.test_contracts combat_pcg.test_scoring combat_pcg.test_spatial full_pcg.test_core -v`：37项通过。
- `evolution/.venv/Scripts/python.exe -B -m combat_pcg.audit --verify reports/combat_v3/baseline_inventory.json`：`changed: []`。
- 41份移动文件在目标路径逐个核对SHA-256，全部一致；整理前726个文件的快照比较，仅文档与忽略规则改变，已有源码与数据未改。
- Godot `git diff --check` 通过；本次新增/修改文档的本地Markdown链接检查见 verification JSON。
- 存在可见Godot/Python/Depthmap进程；进程命令行查询被拒绝，未停止任务。没有运行新草案测试、没有重新执行大型实验、没有进行新的Godot物理验收。
