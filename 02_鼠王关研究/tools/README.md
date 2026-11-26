# 分析工具

所有命令从上一级“02_鼠王关研究”目录运行。

| 用途 | 脚本 |
|---|---|
| 当前流程 | `prepare_shuwang_runs.py` → `build_shuwang_jsx.py` → Illustrator 执行 `render_shuwang.jsx` → `finalize_shuwang.py` |
| 检查已有成果 | `validate_run.py runs/<run_id>`，只读校验，不重新生成 |
| 原生对象清单 | `check_source_001.jsx`、`inventory_new_runs.jsx`、`extract_run_items.jsx` |
| CAD 细节修补 | `build_repair_cad_ai.py`、`repair_cad_ai_template.jsx`、生成的 `repair_cad_ai.jsx` |
| 历史首局流程 | `build_ratking.py`、`inspect_route_pdf.py`、`*first_run.py`、`render_ratking.jsx`、`ratking_figure_template.jsx` 等；不能与当前流程混用 |

`validate_run.py` 从既有项目校验器适配，改用整理后的 source 路径。共享代理配置仍保留原位。
JSX 通过模板及构建脚本维护。不要直接编辑生成脚本中的嵌入数据。

PCG 已直接读取本项目的 `source/` 与 `maps/ratking/shuwang/`，不再生成上级目录兼容快照。
