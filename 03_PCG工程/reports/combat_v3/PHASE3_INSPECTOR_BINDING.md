# Phase 3 Inspector 战斗参数绑定

当前 `Main` 使用 `shell_main.gd` 直接声明试玩参数。它在创建
`CombatFullPCG` 前读取 `combat_config.json`，复制配置并应用 Inspector
覆盖值。运行时 `CombatLevel`、HUD、碰撞、追击、伤害、门状态和人工试玩
日志共同使用这份覆盖后的配置。

Inspector 现在分为 Layout、Player、Boss、Weapon 和 Portals。有效字段包括
地图 seed、DXF 对照、分区着色、玩家普通／瞄准移速、Boss 移速／血量／
抓取范围／抓取前摇、武器伤害／射击间隔／瞄准／换弹时间，以及玩家挤门、
Boss 撞开 through 和 break 的时间。旧固定拓扑生成器的候选文件和 Evolution
字段不再由当前 Main 脚本暴露。旧脚本和历史实验文件仍保留。

Godot 4.7.2 的 `verify_inspector_combat.gd` 在真实 Layout v5 包上检查了字段
映射。Boss Speed 设为 0 时最终速度为 0，运行时改为 4.2 后速度和位移均恢复。
测试输出为
`PASS Inspector values reach CombatLevel and Boss Speed controls movement`。
Python 战斗与评分回归共 62 项通过。

人工试玩保存的 `combat_episode.json` 现在对实际运行时配置做哈希。因而
Inspector 覆盖产生的记录不会继续错误标记为原始 JSON 配置。
