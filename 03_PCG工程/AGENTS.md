# Rat King PCG repository instructions

## Start every task or new conversation here

1. Read this `AGENTS.md`, then the repository root `PLANS.md` and `PROGRESS.md` **before** choosing work. Read the latest stage report and relevant code after that. Do not restart Phase 1 if `PROGRESS.md` shows completed modules.
2. Inspect `git status --short`, recent commits, relevant source/config hashes, and any running experiment or test processes. Preserve user modifications and in-progress runs. Do not reset, clean, overwrite, kill, or interrupt them to prepare work.
3. Choose the next incomplete module from `PROGRESS.md`, following the dependency gates in `PLANS.md`. If code and the confirmed plan conflict, report the specific conflict first; inspect the evidence and resolve without silently rewriting existing functionality.
4. Treat the latest confirmed repository plan as authoritative. When a user explicitly changes the research plan, update `PLANS.md` and `PROGRESS.md` together, document what changed, and keep historical experiments distinguishable.

## Delivery discipline

- The five phases are separate tasks. Split each phase into modules with observable input, output, tests and an acceptance gate. Implement one module, run its tests and required runtime validation, **update `PROGRESS.md`, then commit only that module and its progress update**. Record the resulting commit hash in the next progress update or stage report. Do not start dependent formal work before its gate passes.
- At phase completion, write an acceptance report with actual commands/results, limitations, configuration/source hashes and module commits. Include the report and progress update in the phase commit. Never call unrun checks complete.
- Stage explicit paths; do not stage all files or mix in unrelated user changes. Never automatically push. Keep large experiment data out of Git; commit manifests/hashes and small evidence only.
- Preserve Legacy, `evolution/runs/search_v1`, source DXF and `shuwang.graph`. New combat score/protocol revisions get new experiment IDs; never merge old/new scores silently. Source files and legacy outputs are read-only unless the user explicitly requests their modification.
- The project lives at `F:\大学作业\游戏空间设计微专业\03_PCG工程` inside the course repository. Use the installed Python, Godot and Depthmap programs. Independent automated runs must work without an active Codex conversation.

## Research and computation boundaries

- Python Layout is the geometry source for Godot, Depthmap, and figures. Godot CombatLevel executes interactive, batch, and replay combat. Keep the archived Python proxy available for reproduction of earlier experiments.
- Reuse existing project modules first, then tested open-source components, then minimal new code. Record version, license, changes and compatibility evidence for any imported module.
- Python schedules candidate requests, validation, Godot batches, scoring, selection, caching, and resume. DepthmapX supplies spatial measurements. Godot executes navigation, collision, shooting, and state changes. **Codex does not score individual maps or select survivors.**
- Formal experiments must be pinned to Git commit, source/config/implementation hashes, tool versions and a frozen scoring protocol. A draft or synthetic fixture is not a real experimental result. ERROR is a system failure, not a low-scoring map; UNCERTAIN is not proof of impossibility.
- Keep S/F/P/D Pareto selection separate from display Q. Keep Gate Counts and Convex Choice out of formal S until calibrated. Do not infer player sight or valid shots from Depthmap potential visibility alone.
- Generation 0 and every subsequent generation must retain all evaluated offspring, the survivor population, lineage, repairs, constraint failures and current/cumulative Pareto. Do not display a composite winner built from different individuals.
- Report measured geometry, spatial analysis, simulated outcomes, Godot checks and untested experience hypotheses separately. Do not claim superiority to the official game from numeric similarity.

## Current handoff

Phase 2 passed for the current shell layouts in `0073787`. Phase 3 uses the Godot backend from `b9ce3e1` and follows the formal gate in [PLANS §5.2](PLANS.md#52-phase-4-准入与当前收口顺序). Phase 4 engineering now follows the single-parent archive plan in [PLANS §5.4](PLANS.md#54-phase-4-正式引擎与单种子验收). Each new child has one actual parent and uses a local edit or regional rewrite. The v2 crossover run and labels are historical records. Read [PROGRESS.md](PROGRESS.md) for the next unverified module.

Main uses `scripts/shell_main.gd` and `full_pcg/shell_layout.py`. Follow PLANS §§2.2, 3.2 and 3.3 for the agreed layout family, window rules, and multiple portals. The earlier anchor generator is a historical baseline; obsolete draft copies have been removed. Use RUNS.md for run outputs and tools/open_viewer.ps1 for the current B viewer. See the current Git status before editing.
