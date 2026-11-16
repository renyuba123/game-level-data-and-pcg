# 鼠王关首局核验记录

- 原件 `鼠王关玩家路线图001.ai` 维持原字节；项目仅另有 `outputs/ratking_run-001/ratking_run-001_edited.ai` 一份修改版 AI。
- 用户确认绿色 Spawn 起点、整体沿路线至左侧靠近 Transform 的末端。44 条原生 Route 对象已识别；局部候选连接顺序未逐帧核实，`sequence_index` 留空。第 16→17 段有 8.64 AI 点接缝；终点对应哪一个 Transform 标记待查。
- `shuwangguan.graph` 由本机 Depthmap+ Beta 1.0 成功打开，GUI 的 `Map > Export` 取得 Convex TXT/MIF/MID/Pajek 和 VGA TXT。Ref 0 是无效折线；9 个 REGION 才是有效凸空间。原来的 10 个临时房间标签中，下方 L 形块合并为一个房间。
- 8 个图层颜色质心控制点配准 graph→AI，最大残差 2.327 AI 点，小于半个 VGA 网格的 6.692 点。MIF 声明 NonEarth metres，但游戏世界物理比例没有核准。
- 9 条凸空间图边已导出，门洞中心和真实可通行性仍需录像/底图核验。路线端点 88/88 唯一归入房间；事件 23/24，现编号 E012（原 E005、原件 UUID 736）在分块外。
- 原件 24 个图标按候选路线重编号：Spawn 为 E001，终点旁 Hunting Pistol 为 E024；End 独立标注。图层移动可能重分配编辑版 UUID，`icon_audit.tsv` 记录原件→修改版的逐一对应。
- Choice、Visual Integration [HH] 由真实导出值绘图。Gate Counts 恢复白底矢量格点图；3,462 个点、4–7,230 count 来自 VGA TXT。用户提供的 Depthmap+ 截图用来校准 10 档颜色和阈值，记录在 `gate_counts_palette.json`；这些阈值为图像匹配派生值，不是软件官方色标。单局路线不称使用频率热图。
