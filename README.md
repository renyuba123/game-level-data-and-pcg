# Gameplay Route Analysis — Codex Skill 安装包

用于《最后生还者2》鼠王关及其他关卡：统一整理 Illustrator 玩家移动轨迹图、保留多局路线及战斗事件、对接 DepthmapX 数据与后续 PCG 验证。

## 安装（Windows）

**项目级（推荐）：** 将压缩包中的 `.agents/skills/gameplay-route-analysis/` 整个文件夹复制到你的项目根目录：

```text
<你的项目目录>/
  AGENTS.md                 # 可选：追加 AGENTS_SNIPPET.md 内容
  .agents/
    skills/
      gameplay-route-analysis/
        SKILL.md
        references/
        assets/
        scripts/
```

**全局级（所有 Codex 项目可调用）：** 把同一个 `gameplay-route-analysis` 文件夹复制到 `C:\Users\<你的用户名>\.agents\skills\`。全局级不要与项目级无意识重复安装同名 Skill。

项目级适合当前鼠王项目，功能稳定后再考虑迁移到全局级。打开此项目的 Codex 后用 `$gameplay-route-analysis` 显式调用，也可尝试 `/skills` 查看是否被发现。若未出现，重启 Codex。

**不需要安装 MCP 才能使用 Skill。** MCP 只影响 Codex 能否直接操作 Illustrator；没有 Illustrator MCP 时，可以让 Codex生成 Illustrator 2026 可执行的 `.jsx` 脚本，用户在本机副本中运行。

## 快速开始
1. 将你的原始 `.ai`、参考的 CAD/DepthmapX 资料置于项目 `source/`（原件保留）。
2. 复制 `prompts/first-run.md` 给 Codex，启动首轮审核与样式优化。
3. 每次新增一局，使用 `prompts/new-run.md`，填入新的 `run_id`、源文件与录像等。
4. 不足以恢复时间/顺序时，先得到 `movement_clean` 图和 `review_needed.csv`，根据录像补录后才能做频率与路径顺序分析。
5. 生成的数据可运行 `python .agents/skills/gameplay-route-analysis/scripts/validate_run.py runs/<run_id>/` 做基础检查。

## 包内内容
- `SKILL.md`：触发条件与分阶段工作流。
- `references/rat-king-first-pass.md`：针对现有鼠王图的修改重点。
- `references/visual-style.md`：多图输出的视觉标准。
- `references/data-contract.md`：共用地图+逐局数据格式。
- `assets/`：空白数据模板，不包含真实观测。
- `scripts/validate_run.py`：不依赖第三方包的基础 CSV/manifest 校验。
- `prompts/first-run.md`：针对当前图的首次提示词。
- `prompts/new-run.md`：以后每次重用的提示词。
- `AGENTS_SNIPPET.md`：可选项目约定，不会自动写入你的现有 AGENTS.md。

## 重要说明
这个包是**可安装的 Codex Skill + 提示词和校验模板**，不是已经连上 Illustrator 的 MCP，也不是能够自动读取你本地 AI 文件的服务。它指导 Codex 检查、制作脚本和交付文件，具体自动修改的范围以你本机的权限和文件格式为准。
