# Phase 2.3 — Godot 白模解码与通路状态

复用 `drafts/full_pcg_godot/` 的 Python 导出器和 GDScript 解码器；Python Layout仍是唯一几何来源。修复NumPy 2.5对二维叉积的限制，导出地板、墙、障碍、两角色净空导航和特殊门实体。NavigationLink必须跨过对应Portal且整段位于开启后的角色净空多边形内；无法满足时明确拒绝，不以穿墙链接兜底。

从Phase 2.2保存的合法布局中按不同房数优先选取并导出12张。尝试21张，其中9张因无法找到无穿墙的直线Godot导航链接而被拒绝，失败seed与Portal ID写入 `full_pcg_output/combat_godot/manifest.json`；12张通过导出，覆盖房数8–17。该结果说明几何合法与Godot单段链接可实现性是不同门槛，不能把98张全部称为已可在Godot游玩。后续需用弯曲廊道的多段真实导航连接或调整生成几何修复9张失败地图。

本机 `D:\steam\steamapps\common\Godot Engine\godot.windows.opt.tools.64.exe` 为Godot 4.7.2。无界面运行 `res://full_pcg/godot/verify_layouts.gd`，进程退出码0：12/12张包可加载，Layout哈希匹配，through初始仅玩家交互导航可用、break初始双方不可用，Boss撞开后双方链接可用；全开状态玩家和Boss均可到达全部房间。逐图状态在 `full_pcg_output/combat_godot/godot_navigation.json`。测试等待导航同步的物理帧；Godot仍报告少量导航网格边合并警告，尚须在实际移动与碰撞测试中检查影响。

这里尚未验证角色实际挤身、Boss撞后穿越、射线命中、两阶段战斗或潜行者。旧Main用户改动未覆盖；新白模解码在独立文件中。
