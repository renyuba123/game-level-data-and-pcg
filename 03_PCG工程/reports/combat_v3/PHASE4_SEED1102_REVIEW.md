# Phase 4 · Seed 1102 失败回放与 B 组对照

## 范围和来源

在 Godot 4.7.2 stable Steam `ed1daf0bf`、60 Hz 下实测。锁定 `near_1_-1`、Map Size 1.5 与既有 S/F/P/D 协议，启用原生 Boss 和角色碰撞。地图、策略、战斗配置和评分均未改动。正式评价请求为 0。坐标为缩放后的 Godot 世界 X/Z，时间从首次物理步起算。

Seed 1102 来自 `phase3_inspector_177_v1` 独立复核。B 来自 `shell_sampling_focused_g20_v1` 的 `single-18-02`（布局种子 6）。对照固定 `output` 策略、`paced` 决策、场景种子 110／112、能力设置和战斗配置。两图各用自身出生点和几何，单个空间构件的作用仍待隔离验证。

| 验证对象 | 版本或 SHA-256 |
| --- | --- |
| 代码基线 | `4927180` |
| Godot 二进制 | `12310c74bdda7dcd43f28e971f33047dcecadd436b68169d61ce41009006df38` |
| 实测战斗配置哈希 | `b3088e498ab848463dfaba62e85d7eda40c3c6309528fb6432da18b01ca73d6e` |
| Seed 1102 Layout 哈希 | `a1732212066ab279ef5766c23acf5d91d46bbcfe61346201890aa07453b4de2e` |
| B Layout 哈希 | `f7a60bade449efd096a9c6810340066ba3ddfeff57911c7b360140373a51c406` |

原始输入、轨迹、事件和 `review_manifest.json` 位于 `F:\大学作业\游戏空间设计微专业\04_PCG实验输出\diagnostics\seed1102_phase4_review_01`。清单记录布局包、引擎脚本、回放文件和匹配场景的首个偏差。

## Seed 1102 最早可复验的两个转折

| 对局 | 转折、位置与资源 | 当时的退路与策略选择 | 后果 |
| --- | --- | --- | --- |
| `output_110` | **9.900 秒，第 594 步。** 在主廊 (24.52, 12.74) 换弹完成。Boss 相距 10.03 m，592 HP。弹匣 4 发，备弹 0。 | 普通门 `gate_6` 通往 `east_high` 的弹药，旁边也有挤身门 `gate_0`，后者的补给收益未实测。代理沿主廊走后折回，朝 Boss 的来向接近。 | 13.050 秒进入第二阶段，全局耗完 12 发、未取弹。18.133 秒在 (23.24, 16.60) 被大型 Boss 抓死，Boss 剩 398 HP。 |
| `output_112` | **7.083 秒，第 425 步。** 在左侧间 `left_low` (11.15, 17.98) 完成第二次取弹。Boss 相距 6.04 m，898 HP。弹匣 6 发，备弹 20。 | 普通门 `gate_10` 可退回 `left_inner`，另一口 `gate_9` 是仍关闭的 break。代理留在侧间继续射击。 | Boss 约 9.133 秒抵达 `gate_10`，双方距离约 2.19 m。10.383 秒触发抓取预警，11.217 秒在 (12.39, 16.69) 死亡，剩 24 发，Boss 仍处第一阶段、796 HP。 |

这里的转折指本轮找到并实测替代路线的第一个决策点。更早的动作是否已经增加风险，证据不足。

### 保留原输入前缀的替代动作

- **`output_110`** 保留前 594 步。经普通门 `gate_6` 转入 `east_high`，11.250 秒取到 `supply_1`，备弹增至 8 发。沿门洞射线在 11.600 秒合法命中，Boss 由 592 降至 541 HP。12.500 秒结束输入时玩家满血、相距 6.00 m。另一次退到室内更深的位置，枪口射线被遮挡，未命中。取弹路线和可用射位应分别检查。
- **`output_112`** 保留前 425 步。取弹后即经 `gate_10` 回到 `left_inner`，约 7.767 秒完成过门，8.850 秒合法再命中，Boss 由 898 降至 847 HP。9.317 秒结束输入时玩家满血、相距约 3.58 m。
- 两个片段均到 `INPUT_ENDED` 为止。它们证明当时有可完成的取弹／撤离动作，随后可恢复射击。两条替代路线的最终胜负及第二阶段击杀仍待验证。
- 两条原始对局的逐帧状态、事件和终局均与归档一致。原路线和替代片段都另行重复，回放文件 SHA-256 一致。

## B 组成功对照与时序异常

| 场景种子 | 首次命中 | 首次取弹 | 进入第二阶段 | 首批击杀大型 Boss | 同配置再次击杀 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 110 | 0.500 秒 | 5.383 秒 | 10.450 秒 | 45.650 秒 | 34.767 秒 |
| 112 | 0.500 秒 | 5.233 秒 | 10.550 秒 | 35.950 秒 | 70.100 秒 |

首批两局都完成两次取弹，约 5 秒已把补给接入交战。用首批保存的输入做固定回放，两局胜负均一致，**逐帧确定性未通过**。首个差异出现在第 1–2 个物理步，只有 Boss 坐标和双方间距变化，偏差约 0.033 m。首个事件时序差异在种子 110 为第 1137 对 1136 步，种子 112 为第 1207 对 1203 步。固定输入重跑的文件哈希仍有变化。重新执行自动对局也均获胜，但击杀时间明显变化。B 的成功节奏可做观察对照，单帧和时间差须按各自批次解读。

批测与固定回放都强制同步导航图、等待两次 `physics_frame`。下一步记录首个控制输入前及最初三帧的 Boss 出生变换、导航图迭代、首个导航路点、移动与碰撞调用顺序。具体触发条件仍待验证。

## 修正顺序和正式准入

1. 先定位并修复 B 组固定输入的时序偏差，重跑两组场景并核对关键事件、终局及位置偏差。
2. 如需修改策略，优先分开测试两条最小调整。换弹后根据已发现弹药的通行和拾取耗时评估绕行。取弹后估算 Boss 到达门洞的时间，提前从当前可用出口撤离。本轮普通门能实际通过，现有证据优先指向动作时机。是否需要改局部几何仍待后续长程测试。
3. 修改策略、配置或评分前先确认并登记新版本。把参与调试的地图归为开发用途，用预登记的新地图和扰动独立复核，按地图和策略报告胜、死、超时。原独立复核仍为 **6/24（25%）**，准入目标 **70%**。B 对照和替代片段均未计入独立复核。
4. 实测 `preflight` 返回 `allowed=false`，理由为战斗、评分协议未冻结，物理尺度未校准，正式自动实验引擎准入项未置位。两项准入均通过后，再验证 B 组每代 24 个重点名额＋8 个探索名额并启动 G0–G20、672 次正式请求。

## 本机复现

以下四次固定输入检查已实跑，分别复现 1088／673／750／559 帧，档案保持原样。

```powershell
Set-Location 'F:\大学作业\游戏空间设计微专业\03_PCG工程'
$archive = 'F:\大学作业\游戏空间设计微专业\04_PCG实验输出\diagnostics\seed1102_phase4_review_01'
$godot = 'D:\steam\steamapps\common\Godot Engine\godot.windows.opt.tools.64.exe'
$code = @'
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from combat_pcg.godot_batch import file_hash
from combat_pcg.paired_replay import run_godot
from full_pcg.common import read, write

archive, godot = map(Path, sys.argv[1:])
for name in ("output_110", "output_112", "alt_110_hold_cover", "alt_112_reengage"):
    with TemporaryDirectory(prefix="ratking-replay-") as directory:
        target = Path(directory)
        case = read(archive / name / "case.json")
        case["output"] = str(target / "replay.json")
        write(target / "case.json", case)
        run_godot(godot, target / "case.json", target / "godot.log")
        actual = read(target / "replay.json")
        expected = read(archive / name / "replay.json")
        assert actual == expected, name
        print(name, actual["result"], len(actual["frames"]), file_hash(target / "replay.json"))
'@
$code | & '.\evolution\.venv\Scripts\python.exe' -X utf8 -B - $archive $godot
& '.\evolution\.venv\Scripts\python.exe' -B -m combat_pcg preflight
```

B 组可从 `matched_B/request.json` 取战斗协议和布局包，调用 `combat_pcg.godot_batch.batch` 跑 `output`、种子 110／112并开启输入捕获，写入独立目录。两批自动对局在 `matched_B`、`matched_B_repeat`，固定输入与差异在 `matched_B_replay_110_recheck`、`matched_B_replay_112_recheck` 及两份对应的 `_fresh` 目录。
