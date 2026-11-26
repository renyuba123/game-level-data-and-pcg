# Phase 3 缩放地图的 Boss 撞门修复

## 原因

当前人工试玩使用 Seed 177、`Map Size=1.5`。门洞净宽约 2.19–2.26 米，
Boss 胶囊直径约 1.16 米，因此不是门宽不足。逐门物理诊断发现 `gate_7`
和 `gate_12` 的 Boss 都停在距离门中心 1.125 米的导航入口端点；旧代码只在
距离门中心不超过固定 1.0 米时开始撞门。Boss 无法再向关闭门体内移动，因而
永远差 0.125 米，既不触发撞门，也不能穿越。

## 修复

关闭的 `through`／`break` 现在使用 Boss 对应 `NavigationLink3D` 的两个入口
端点作为撞门交互锚点。端点与墙体、门洞和导航一起按 `Map Size` 转换；触发
容差由 Boss 半径加 0.15 米构成，不缩放角色本身。旧包若缺少 Boss 导航连接，
仍保留原门中心判定作为兼容回退。

该改动不改变门宽、撞门耗时、Boss 速度或正式评分参数。

## 验证

- Godot 4.7.2，Seed 177、`Map Size=1.5`：全部 `through`／`break` 的缩放后
  Boss 入口端点均能被识别。
- 从 `gate_7` 的真实入口端点开始，Boss 成功进入撞门状态，经过配置的
  `through_boss_smash_s` 后门体和导航连接正确打开。`gate_12` 使用同一入口
  合同并通过端点检查。
- 完整 Godot 机制回归通过：`issues=[]`，事件包含 `smash_start`、
  `portal_open`、补给、换弹、分裂及第二阶段胜利。
- `python -B -m unittest discover -s combat_pcg -t .`：63 项通过。

测试只验证机制和坐标合同；人工试玩中的路线选择和难度仍属于 Phase 3 校准。
