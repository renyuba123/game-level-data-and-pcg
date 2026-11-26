# 关卡进化查看器

当前推荐入口是 `shell_sampling_focused_g20_v1`（B 组，G0–G20）。在项目根目录执行 `& .\tools\open_viewer.ps1`。其他 run 见根目录 `RUNS.md` 和 `RUN_OUTPUTS.html`；下方 v3/v2 检查条目是历史归档复查方法。

谱系顶端的三角形 Initial 展示原始 `鼠王关.dxf` 的墙线、特殊开口和障碍。蓝色点线标记 G0 初始种群的生成来源。实线连接归档中的真实亲代。所有轮廓使用同样大小的正方形外接框，正方形为初始种群、独立样本和区域重排，圆形为局部编辑，新单亲实验的加号形为成功的档案参考编辑，详情显示参考 ID，谱系线仍连接唯一实际亲代。历史双亲档案的加号形表示双亲交叉。已保存的 v3 试跑早于这项算子。× 表示验证无效，− 表示未入选，? 表示证据不足，≡ 表示布局重复，! 表示系统错误。候选轮廓按固定 0–100 的 Q 刻度着色。星标是截至所选代有效个体的最高完整 Q，粗线连接这个个体的实际祖先。

谱系图默认可拖动平移，滚轮缩放。右上角工具栏提供框选缩放、平移、放大、缩小、自动缩放和复位。双击画布也可复位。

谱系按实际亲代整理分叉，代次从上往下读。细斜线为真实亲代连接，遇到挡住连线的节点时作短绕行，S、F、P、D 用粗体字母标出各项最高分，彩线追溯祖先。★ 标出最高 Q，祖先线最粗。共用亲代线平行显示，只有完整评分的个体参与标记。缩略图按自身平面比例放大到轮廓内，尺寸比较使用下方的同尺度平面图。

点击谱系中的缩略图即可切换下方的当前个体、地图和指标。地图右侧集中显示个体范围、当前个体、对照方式和图层开关。点选到范围之外的节点时，当前个体仍可在右侧查看。

左右地图默认使用相同坐标范围和比例。每张图都有独立工具栏，可以分别滚轮缩放、平移和复位。切换对照对象或方式后，两张图回到同一默认比例。

在右侧「地图控制」打开「叠加 Depthmap 指标」，可切换视觉整合度（HH）、可视连接度及平均最短路径距离，并选择初始或可破坏通道全开状态。颜色来自归档点网格，无采样格留空；对照两张地图使用共同的数值范围。点位按地图倍率配准，距离值保留原分析模型米。早期继承的 G0 从配套 v1 归档读取原始点位，归档缺失时显示提示。

## 启动

在项目根目录执行。当前电脑的 Viewer 依赖装在 `%LOCALAPPDATA%\RatKingPCG\viewer`。其它电脑可另建 Python 环境，安装 `full_pcg/viewer_requirements.txt`，再在命令中指定对应的 Python、档案和 Godot 路径。

```powershell
$course = 'F:\大学作业\游戏空间设计微专业\04_PCG实验输出\runs'
$python = Join-Path $env:LOCALAPPDATA 'RatKingPCG\viewer\Scripts\python.exe'
$run = Join-Path $course 'shell_sampling_focused_g20_v1'
$godot = 'D:\steam\steamapps\common\Godot Engine\godot.windows.opt.tools.64.exe'
& $python -B -m streamlit run full_pcg/viewer/app.py --server.address 127.0.0.1 --server.port 8503 --browser.gatherUsageStats false --theme.base light -- --run $run --godot $godot
```

浏览器地址为 <http://127.0.0.1:8503>。

## 检查新版单亲谱系

1. 将 Generation 切至 2，查看原始 DXF 和 G0–G2 的全部 24 个请求。星标应落在 G1 的 `single-1-05`，粗线连接其亲代 G0 · 08（归档 ID 为 `initial-07`）。
2. 选择 `single-2-02`。其唯一亲代是 G1 的 `single-1-03`。后者在 G1 未进入幸存种群，G2 仍可从历史档案抽到它。个体详情显示亲代层级、历次派生数、抽样权重及区域重排记录。
3. 查看 `single-2-06` 的证据不足标记。该候选的 12 局均死亡，保留布局与事件记录。通过 Pareto 页可切换当代与累计解集。

## 回看历史 v2 双亲试跑

1. 在谱系图第三行点击 **`genetic-2-02`** 的缩略图。实线指向主要父代 `initial-02`，虚线指向提供右翼角部房组的 `genetic-1-03`。下方地图和评分随选中节点切换。
2. 悬停带红叉的节点，确认在哪一代弃用及原因。外框以固定的 0–100 标尺显示 Q，越深代表 Q 越高，灰框表示缺少完整 Q。弃用来自实际生存选择记录。
3. 切换父代，打开 **高亮父子分区变化**、**显示 Portal 邻接**或**叠加单局轨迹**。下方「进化分析」给出幸存种群 Q 的最高值、均值和中位数，以及当代 Pareto 的 S／F 投影。**Pareto** 页可切换目标轴及当代／累计档案，**代记录**可查完整请求。
4. 点击**在 Godot 中试玩**会从当前选中个体的原始 Layout、战斗配置和地图尺度启动战斗白模。副本下载可检查原始 Layout。没有布局的个体会显示失败诊断。

当代代表从当代 Pareto 中选取，使用四个 0–100 目标到理想点的欧氏距离，平手取个体 ID。Q 用于展示。拓扑类别比较去掉 ID 和门型后的基础邻接图。单局轨迹来自归档 Godot 帧，标记包括命中时玩家位置、拾取、分裂、通道破坏和结局。

批量热力图、逐代视频和正式 Generation 0–20 归档验收属于后续 Phase 4 工作。

## 验收证据

- 使用 CPython 3.13.2、Streamlit 1.67.0（Apache-2.0）、Plotly 7.1.0（MIT）和 NetworkX 3.7（BSD-3-Clause）。Viewer 独立安装，原实验的 Python 环境、实现哈希和归档继续可复现。
- 分别将 `RATKING_VIEWER_TEST_ARCHIVE` 与 `RATKING_SINGLE_PARENT_TEST_ARCHIVE` 指向 `shell_draft_pilot_v1` 和 `shell_single_parent_v3`。运行 `& $python -B -m unittest full_pcg.test_evolution_viewer -v`，五项通过。覆盖新旧谱系读档、实际祖先高亮、状态符号、跨代选择、轨迹、Pareto 与无效布局筛选。
- 在 Edge 刷新现有 Viewer 后确认新档案为默认项，切换 G2 后显示 56/96 胜。Godot 加载 `single-2-02` 的结果见[试跑报告](../../reports/combat_v3/PHASE4_SINGLE_PARENT_V3.md)。
- 用本机 Chrome 检查控件和自动播放。第 1 代按归档显示 59/96 胜，播放到第 2 代显示 71/96 胜并停止。Seed 6 父子图的 `occlusion_0` 分别为 32.23、24.80 秒，均在第二阶段取胜；图中高亮实际消失的左翼邻接。
- 在 Godot 4.7.2 使用 Viewer 的加载脚本无界面启动两份同一 Seed 的不同 Layout。两次均退出成功，分别输出 9 房 16 Portal 与 8 房 14 Portal，实际玩家出生和战斗协议与归档的 1.5 倍率及参数吻合。
- 新版谱系图以 Chrome 验证三代 24 个缩略图、双亲线、弃用标记、0–100 Q 色标及节点交互。点击 `genetic-2-02` 的缩略图后，检查器显示原始 **initial-02 × genetic-1-03** 和交叉／变异记录。 [视图实测截图](<F:/大学作业/游戏空间设计微专业/04_PCG实验输出/runs/output/playwright/ratking-lineage-v2.png>)
