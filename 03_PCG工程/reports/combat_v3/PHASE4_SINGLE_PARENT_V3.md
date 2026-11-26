# Phase 4 单亲档案进化工程试跑

运行 ID 为 `shell_single_parent_v3`。固定战斗配置为 `near_1_-1`，地图倍率为 1.5，空间分析网格为 400 图纸单位。每张布局用三种策略各跑四个固定场景，共 12 局。首代沿用原试跑的八个布局和校验证据。本轮使用独立工程预算，正式请求数为 0。

## 谱系与选择

每代锁定历史亲代抽样池。通过硬约束且 S/F/P/D 完整的布局按 Layout 哈希去重，权重为 `1 / [r × (1 + n)]`。其中 `r` 是在历史抽样池的 Pareto 层级，`n` 是此前派生的请求数。每个子代有一个亲代，由代号和请求序号派生随机流。

局部编辑目标为 1–3 步。区域重排在左翼或右翼一个母区换角布置小间，或在原先没有小间的母区新增角部划分。重建实体墙和 Portal 后核对外围邻接、区域入口、净尺寸及角色通路。每个请求最多检查八个提案。本轮区域重排的抽中概率为 0.5，属于试跑配置。

幸存种群按 S/F/P/D 和拥挤度选择。Q 只用于展示。每代提交全部请求、亲代抽样快照、操作、拒绝原因、幸存种群、当代及累计 Pareto、代表和各目标历史最优。

## 实测结果

| 出生代 | 布局数 | 局部／重排 | 相对亲代拓扑变化 | 当代请求非同构类别 | 胜／死／超时 | 当代／累计 Pareto |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| G0 | 8 | — | — | 7 | 55／38／3 | 5／5 |
| G1 | 8 | 4／4 | 5 | 5 | 64／31／1 | 8／8 |
| G2 | 8 | 2／6 | 5 | 6 | 56／40／0 | 8／12 |

24 次请求产生 24 张不同布局。16 张子代运行新的 DepthmapX 分析和 192 局 Godot 战斗，8 张初始图复用 96 局战斗证据。21 个请求评分完整，3 个为 `UNCERTAIN`，其中 `single-2-06` 的 12 局全部死亡。6 个算子提案被拒绝并换用后续提案，包括无安全窗口、面积范围、布局无变化、角位没换、玩家导航连线穿墙和 Boss 撞击面不可达。

G2 有两次亲代抽取来自上一代幸存种群以外。例：第二代 `single-2-02` 以 `single-1-03` 为唯一亲代，区域重排改变了邻接，Godot 以 1.5 倍加载了 9 房、17 Portal 的同一个 Layout。Godot 加载检查仍记录了导航边合并警告，本次验收只确认布局、尺度、战斗配置与出生位置。批测胜负沿用归档的真实对局。

当前最高展示 Q 为 G1 的 `single-1-05`（67.46），亲代为 `initial-07`。G2 新出生个体的最高 Q 为 65.92。此轮验证了工程流程和真实拓扑变化，效果比较仍留给统一协议下的正式实验。

## 复现与校验

归档目录为 `F:\大学作业\游戏空间设计微专业\04_PCG实验输出\runs\shell_single_parent_v3`。登记和汇总的 SHA-256 分别为 `8648dfb3c5bf942a2bc9057f4271b75258c13c735fa3427a3b0601d3e4c0c7da` 与 `09aa1c3e12bf0c6fcd85df0e1db51d78ea4baa4bf8de27fa64b3f0b9f1399632`。

```text
python -B -m full_pcg.single_parent.run configs/shell_single_parent_v3.json <v1 归档> <v3 归档> <Godot.exe> <DepthmapX.exe> --workers 4 --through 0
python -B -m full_pcg.single_parent.run configs/shell_single_parent_v3.json <v1 归档> <v3 归档> <Godot.exe> <DepthmapX.exe> --workers 4
python -B -m full_pcg.single_parent.run configs/shell_single_parent_v3.json <v1 归档> <v3 归档> <Godot.exe> <DepthmapX.exe> --workers 2 --verify
python -B -m unittest full_pcg.test_single_parent full_pcg.test_shell_genome full_pcg.test_shell_pilot -v
```

以第 0 代为检查点继续运行到第 2 代。改为两工作进程验证时重新计算候选、评价证据哈希与生存选择，三代记录均一致。该验证复用已存的 Godot/Depthmap 证据。设置 `RATKING_SINGLE_PARENT_TEST_ARCHIVE` 指向 v3 后，六项测试覆盖档案抽样、真实父代链、编辑次数、可复现哈希和拓扑变化。
