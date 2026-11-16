# 鼠王关首局图件 QA（2026-11-16）

## 交付检查

- 原始 `鼠王关玩家路线图001.ai` SHA-256：`66238BC3F75C78F018A90749B2130A3CF0ED021977BBFBAD4F8BFF1D86CA2542`，与开始时一致。
- 唯一修改版 `ratking_run-001_edited.ai` SHA-256：`EC35839A64FE7674984B57C6D5145FCE331DCF4B7A325575CF776BED108A1279`。项目扫描恰有两份 `.ai`。修改版由 Illustrator 重新打开并导出，PDF 兼容页为 1800 × 1012.5（16:9），有 8 个顶层图层；各类图形收纳在对应的 `*-Labels` 父层。
- 五组 PNG/SVG 均由重新打开的最终 AI 的命名图层视图导出，见 `run_manifest.json` 的图层清单和每个文件哈希。Gate Counts SVG 的 `F-Gate-Counts` 层有 3,462 个矢量矩形，无嵌入截图；墙体、标题和图例也是矢量。所有 SVG 均无外部本机图片引用。导出记录见 `figure_export.log`。
- `ori_events` 保留 23 个原件事件图标；绿色 Spawn 由原件路径复制。Illustrator 移动图层时重分配编辑版 UUID，`icon_audit.tsv` 将 24 个原件 UUID 与编辑版对象逐一按图层和几何中心对应，最大中心差 4.682 AI 点（容差 40 点）；脚本在保存并重新打开 AI 后再次核查。
- `validate_run.py`：PASS。仍有预期的 8.64 AI 点候选路线接缝和 1 个事件未落入凸空间警告。

## Depthmap+ 导出与配准

- 用户指定的 Depthmap+ Beta 1.0 已打开 `shuwangguan.graph`。未保存或改写原 `.graph`；其 SHA-256 见 `map_transform.json`。
- Convex Map 导出属性 TXT、MIF/MID 多边形和 Pajek 网络；Ref 0 为没有有效指标的 PLINE，不作为房间。9 个有效 REGION 对应 R01–R09。原先临时分成两块的下方 L 形区域在图中只有一个凸空间，现为 R05。
- 8 个非共线分块质心控制点从原 AI 嵌入的 Depthmap 图像与 MIF `CENTER` 配对，拟合 graph→AI 仿射。最大残差 2.327 AI 点，低于半个 VGA 网格的 6.692 点阈值。路线端点 88/88 唯一归属房间；事件 23/24 唯一归属。
- VGA Map 导出 3,462 个点，`Visual Integration [HH]` 范围 4.0597–14.8545，`VGA Connectivity` 范围 159–1667，`Gate Counts` 范围 4–7,230 count，网格间距 200 graph units。Gate Counts 使用白底矢量格点，真实点值来自 VGA TXT。用户提供的 664 × 454 px Depthmap+ 截图仅作校准参照，原文件 SHA-256 为 `22E8201E1A47DEE84CCB99911D71235EAA246CD96435F2B9F9B591AD93B349AB`。对齐后 3,454/3,462 个格点中心可读取原图颜色，10 档阈值匹配其中 3,065 个（88.7%）；阈值及原生 RGB 见 `gate_counts_palette.json`。这是图像匹配所得的派生色阶，不是 Depthmap 官方阈值。Choice 是凸空间图指标，范围 0–42。
- MIF 文件虽然声明 `NonEarth Units "m"`，但游戏内物理尺度没有校准；图中按“比例未核准”处理，没有把 graph 单位称作可信游戏米。

## 证据边界与待核实项

- 用户确认整体方向为绿色 Spawn 到左侧靠近 Transform 的末端。44 条原生 Route 对象已与 PDF 绘图段匹配。局部顺序是基于端点连续性的**候选**，尚未逐帧与录像核对；正式 `sequence_index` 和时间戳留空。图中的箭头也按候选方向解读。
- 第 16→17 候选段有 8.64 AI 点空隙；实际是否为绘图断点、停顿或重试待录像确认。末端关联 E008 还是 E023 Transform 仍待确认；End 本身是独立路线标注。
- 24 个原生事件标记按候选路线位置重编 E001–E024；Spawn 是 E001，末端附近 Hunting Pistol 是 E024。编号不代表录像核实的事件时间；动作语义、时间和重试归属仍未核实。E012（原 E005、原件 UUID 736）位于所有导出凸多边形之外，需检查门洞或原 AI 偏移。
- Pajek 导出 9 条凸空间图边且与 Connectivity 度数一致，但未逐一确认实际门洞位置及玩家可通行性。PCG 接口保留 `passable_door_verified=false`。
- VGA 3,462 点中有 100 点不唯一落入导出的凸多边形（主要为边界/外缘），房间均值只对唯一归属点计算。

## 图面复核

- 路线图：蓝线/箭头、绿色 Spawn、紫色终点和未核实说明在整页可辨。中央交叉处的时间连接仍不能仅凭静态图判断。
- 事件图：保留用户原始图标，图上号码显示 001–024 并用细引线关联；PPT 整页可辨，密集区仍可用 SVG 放大查读。侧栏明确候选顺序、End 与事件编号的区别。
- Convex Choice：9 个房间边界、ID、原始 Choice 值和 0–42 色标可辨。
- VGA Visibility：显示真实点值，不是单局路线热图；指标全称、4.06–14.85 色标、网格间距及配准误差可辨。
- VGA Gate Counts：已恢复与其他分析图一致的白底矢量版式；右侧通道才出现主要红色高值区。10 档实际图例覆盖 4–7,230，SVG 放大时格点仍是矢量。原图与矢量配色约有 11.3% 可匹配点的色档不一致，因此图例注明“图像匹配所得、原生阈值未核实”；该指标不当作玩家实际经过次数。
