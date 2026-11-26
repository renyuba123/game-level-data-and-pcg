# PCG 主工程并仓记录

日期：2026-11-26。

- 原主工程：`D:\GODOT Prams\boss-level-pcg`
- 新主工程：`F:\大学作业\游戏空间设计微专业\03_PCG工程`
- 工作树校验：排除缓存后源、目标均为 2077 个文件、501.45 MiB；11 个关键入口 SHA-256 一致。
- 保留内容：源码、配置、场景、报告、版本化 `search_v1`、`full_pcg_output`、未提交修改和运行索引。
- 未迁移内容：`.git/`、`.godot/`、`evolution/.venv/`、`evolution/analysis_cache/`、`evolution/cache/`、`__pycache__/`。
- 历史恢复：`boss-level-pcg-history.bundle` 保存原仓库完整提交历史；`boss-level-pcg-working-tree.patch` 保存原仓库已跟踪的未提交修改。
- 复制日志：`boss-level-pcg-robocopy-trimmed.log`。

PCG 默认输入已改为直接读取 `02_鼠王关研究/source/` 和 `02_鼠王关研究/maps/ratking/shuwang/`。根兼容快照只用于本次删除前 GitHub 检查点，上传成功后再删除。

## 校验边界

- 新路径解析、关键文件哈希和 Viewer 测试通过。
- 旧版 `test_pipeline.py` 有 4 项通过、1 项失败；失败原因是当前 DXF SHA-256 与旧 `data/source_profile.json` / summary 记录不同。该差异在整理前已存在，本次不重签历史实验。
- 当前源文件与历史 QA 的哈希差异继续以既有校验报告为准。
