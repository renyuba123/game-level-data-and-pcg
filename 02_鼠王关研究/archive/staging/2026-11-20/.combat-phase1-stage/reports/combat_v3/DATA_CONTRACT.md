# Phase 1.2 — 数据合同

协议 `combat-pcg/3` 独立于 Legacy 与 full_pcg 的 schema_version=3，必须显式适配，不能自动改标签。

所有二维坐标为模型米 [x,z]，朝向为弧度，房间旋转 rotation_deg 为度。实际物理尺度未校准。Depthmap 按锁定转换倍率另行导出。

Genome 房间采用局部 outline_local+位置+旋转，connections 使用稳定 ID。spawn.player 与 spawn.boss 同 room_id 不同坐标。障碍带几何/碰撞/视觉高度，supplies 仅保存位置和包 ID，数量来自固定协议。合同检查引用与基本类型；多边形有效性、净空、核心区分位和预算检查由 Phase 2 负责，合同通过不等于合法地图。

Layout 必须含 schema_version、genome_hash、generation_config_hash、units、实际房间/走廊多边形、floor/walls、Portal 的 segment/normal/width/kind、障碍及遮挡高度、spawn、supplies、拓扑实现映射与 layout_hash。内容哈希排除其自身字段；绝对路径和运行时间不纳入几何哈希。Phase 2 再实现通用 Layout 验证器，不能把已有 Legacy 输出直接称为这个合同的产物。

EpisodeLog 的外层合同已实现：episode_id、individual_id、policy、scenario_seed、layout_hash、combat_config_hash、duration_s、outcome、phase2_reached、events。事件 ID 唯一，t 为单调秒，data 为载荷；成功/死亡/超时只能有一个末尾终止事件。ERROR 不计作死亡或地图失败。事件载荷的物理语义验证待 Phase 2 的引擎适配。必须记录位置、朝向、可见目标、弹药、生命、感知来源、瞄准、枪口射线、伤害、补给、攻击警告、抓取、分裂和通道状态；仅一份终止事件不能算完整战斗证据。

Individual 出现 ID 与 Genome 哈希分离；Generation 0 允许没有父代。重复地图也保留新出现 ID、父代和算子。全谱系环检查、代数关系、原子提交和恢复在 Phase 4 实现。Generation 必须分别保存 evaluated_offspring 与 survivor_ids，不将评价批次冒充幸存种群。

状态 VALID/INVALID/UNCERTAIN/ERROR 对外统一，附 geometry/topology/combat 子状态及 reasons。没有获胜证据不是几何 INVALID。任何缺失必需测量保留 null，不填零伪装实测。

ScoreReport 保存协议版本、输入/配置哈希、原始指标及单位/分母/证据引用、缺失项、各子分、S/F/P/D、展示 Q、最小化 objectives 和正式选择许可。草案即使结构有效也不得正式搜索。

证明边界：test_contracts 中例子都是手工合成合同样例，不是游戏日志、地图合法性或实验结果。
