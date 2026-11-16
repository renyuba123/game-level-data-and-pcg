# DepthmapX Convex 与 VGA

以 `.graph` 为权威输入，不从颜色反推数值。先记录 graph SHA-256 和所用版本。当前鼠王关使用用户指定的 `C:\Users\人于八\Downloads\空间句法软件及练习文件\Depthmap+ Beta 1.0.exe`：打开 `shuwangguan.graph`，双击左侧 `Convex Map` 或 `VGA Map` 激活，再从 `Map > Export...` 导出。Convex 分别导出制表符属性 TXT、MapInfo MIF/MID 几何与属性、Pajek NET 邻接；VGA 导出制表符 TXT，包含点坐标及全部指标。不要覆盖原 `.graph`。其他版本可参考[官方 CLI 文档](https://github.com/varoudis/depthmapX/blob/master/docs/commandline.md)的 `EXPORT -em pointmap-data-csv`。

分别保存 Convex `Choice`、`Integration [HH]` 与 VGA `Visual Integration [HH]`、`Connectivity`、`Gate Counts`；VGA Connectivity 不得改称房间连接度，Gate Counts 不得改称玩家经过次数。记录网格间距、范围、导出列名、缺失值、分析半径（能读取时）。优先取得同指标 Depthmap 原图，原字节保留并记录哈希、像素尺寸、指标名；用它核对格点空间位置、颜色顺序和高值分布。要做白底矢量格点时，以真实 VGA 点值配色；如截图没有可读色标，可对齐格点中心、采样原生颜色、拟合单调数值阈值并报告匹配率。此类阈值标为派生校准，不能冒称 Depthmap 官方阈值。不要用等频分位数制造不符合原图的红色区域。

从 AI 底图与 graph 几何选至少三个不共线同名控制点，估计仿射变换并报告每点残差与最大残差。鼠王关可用原 AI 嵌入的 Depthmap 分块纯色区域质心，与 MIF 同一分块的 `CENTER` 配对。先核对门角和外轮廓，再将凸多边形及 VGA 点叠加。误差超过半个 VGA 网格或一个图面线宽时停止分析图导出，核查尺度、Y 轴、旋转和地图版本；不得以肉眼挪动点来“对齐”。

Pajek NET 是凸空间图边，不自动等于已核实的可通行门洞；门洞位置和通行状态单列。只有成功配准后的真实数值才能生成 `convex_choice` 和 `vga_visibility` 图。不能获取数值时保留 `convex_regions` 与 QA 状态，不制作假热力图。
