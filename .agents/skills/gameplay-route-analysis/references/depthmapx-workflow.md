# DepthmapX Convex 与 VGA

以 `.graph` 为权威输入，不从颜色反推数值。先记录 graph SHA-256 和 DepthmapX 版本。官方 [CLI 文档](https://github.com/varoudis/depthmapX/blob/master/docs/commandline.md)支持 `EXPORT -em pointmap-data-csv`，用于导出 VGA 点数据；Convex Map 的几何和属性需从 DepthmapX 地图导出核对。CLI 不可用时使用官方图形界面的 CSV/几何导出，仍保留原 `.graph`。

分别保存 Convex `Choice`、`Integration [HH]` 与 VGA `Visual Integration [HH]`、`Connectivity`；后者不得改称房间连接度。记录网格间距、范围、导出列名、缺失值、分析半径（能读取时）。

从 AI 底图与 graph 几何选至少三个不共线同名控制点，估计仿射变换并报告每点残差与最大残差。先核对门角和外轮廓，再将凸多边形及 VGA 点叠加。误差超过半个 VGA 网格或一个图面线宽时停止分析图导出，核查尺度、Y 轴、旋转和地图版本；不得以肉眼挪动点来“对齐”。

只有成功配准后的真实数值才能生成 `convex_choice` 和 `vga_visibility` 图。不能获取数值时保留 `convex_regions` 与 QA 状态，不制作假热力图。
