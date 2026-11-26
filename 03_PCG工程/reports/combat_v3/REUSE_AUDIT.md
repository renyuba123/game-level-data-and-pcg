# Phase 1.1 — 复用审查（2026-11-20）

本轮仅完成 Phase 1，不把旧逃生实验转换成新战斗成果。新 Python 包 combat_pcg 只负责协议与评分，后续通过适配层复用 full_pcg 的权威几何，不创建第三份地图生成器。

| 模块 | 当前能力与证据 | 决定／适配 | 风险与验证 |
|---|---|---|---|
| full_pcg/topology.py | 8–18 房间，平面锚点图、环路、形状旋转；当前仍按图直径分配玩家／出口，Boss 在别处 | 复用图与稳定 ID，Phase 2 改同场坐标和补给基因 | 锚点格点限制、核心区当前只是标签；100 seed + 精确同构 + 实际通路重建 |
| full_pcg/geometry.py | 权威多边形、走廊路由、显式入口交汇、墙、两障碍、角色净空三角形 | 复用几何，不在 Godot 重抽随机布局 | 基准面积取凸空间并集，真实可玩面积需校准；角色净空和几何/拓扑双检 |
| full_pcg/operators.py | 房间/边增删、几何/门型/出生变异；单接口分支交叉 | 复用；后续扩展 2–3 接口和战斗基因 | 不把单接口功能称完整交叉；父子事件、重建与不兼容回退测试 |
| full_pcg/validation.py, geometric_graph.py | 净空、封口重建拓扑、撞击面序列；逃到出口规则尚在 | 复用物理检查，新战斗规则独立适配 | 删除逃生胜利判定但保留旧模块原样；反例和穿门验证 |
| scripts/main.gd | CharacterBody、移动、挤身、Boss 撞门、导航和白模 | 提取必要交互并适配稳定 ID／Portal | 房间索引、共享墙、矩形导航、首个障碍等假设不能照搬；既有 squeeze/chase/nav 测试复用 |
| evolution/metrics.py | CLI 导入、网格、VGA、Metric、CSV、DXF 与指标 | 复用分析调用；新功能分类/尺度/区域阈值计算独立实现 | ROLE 固定 R01–R11；不能把旧 profile 作为新 S；真实 CSV 复算 |
| evolution/simulation.py | 路径、状态、追逐代理 | 复用算法思想；优先使用 full_pcg/navigation.py 的端点安全修正 | 旧代理会吸附导航点，出口成功、无射击/FOV；新事件一致性测试 |
| evolution/evaluator.py | 缓存、文件锁、并行批处理、来源校验 | 复用调度模式；新的 ERROR 与 INVALID 严格分离 | 当前 ValueError/RuntimeError 混记候选失败，不能照搬；异常注入测试 |
| pymoo 0.6.2 | 非支配与拥挤度等已装库 | 复用选择；结构化 Genome 专用算子 | Q 不作选择；不能将 variable graph 塞入固定字段交配 |
| full_pcg/visualize.py / evolution 图表 | 二维几何与静态实验图 | 复用绘图；增加每代全种群、血缘、战斗轨迹 | 现有审计不是 Generation 0–20；离线回放验收 |

## 外部候选：只审查，尚未导入／声称兼容

- https://github.com/mdtoupin/godot-fps ：第三人称控制/相机/射击。README 声明代码 MIT、素材 CC-BY 4.0；导入时逐文件核验并保留归属。
- https://github.com/KenneyNL/Starter-Kit-FPS ：射击逻辑备选，README 声明代码 MIT、素材 CC0，目标 Godot 4.6；本地 4.7.2 仍须实测。
- https://github.com/limbonaut/limboai ：MIT 行为树/状态机；GDExtension 二进制需要版本/平台验证，示例美术许可单独检查。现有状态机够用则不安装。

不为审查而迁移工程。候选远程提交及 README/LICENSE 内容哈希另存 external_review.json；Phase 2 才根据小型独立兼容测试确定实际引入版本。

## Git 边界

起点 8a06b2d；已有 scenes/Main.tscn、evolution/process.json 和 Word 锁文件修改，以及 configs/、full_pcg/、full_pcg_output/ 未跟踪内容。本轮不提交这些已有内容，只显式添加 combat_pcg 和 reports/combat_v3 下的新文件。大型新运行目录加入独立忽略规则。

## 阶段依赖

Phase 1：审查 → 合同 → 评分核 → 草案/反例/验收，各模块测试后提交。
Phase 2：生成/战斗适配；Phase 3：真实采集、校准并冻结；Phase 4：程序搜索和离线回放；Phase 5：6048 请求自动对照。草案评分核不是已校准评价器，禁止正式启动实验。
