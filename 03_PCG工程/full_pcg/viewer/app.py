"""Streamlit entry point for inspecting an archived shell evolution run."""

import argparse
from pathlib import Path
import subprocess
import time

import streamlit as st

from full_pcg.common import ROOT, read
from full_pcg.viewer.archive import (
    Archive, OBJECTIVES, SINGLE_PARENT_SCHEMAS, display_q, representative, room_graph, shown_scores,
)
from full_pcg.viewer.depthmap import DEPTHMAP_METRICS, DEPTHMAP_STATES, DISTANCE
from full_pcg.viewer.figures import draw_layout, plot_pareto, plot_scores
from full_pcg.viewer.lineage import OP_NAMES, build_lineage, discard, initial_labels, q_history

GROUPS = {"genetic": "遗传组", "random": "随机组", "legacy": "Legacy 组"}
OUTCOMES = {"victory": "胜", "death": "死", "timeout": "超时"}
SCOPES = ("幸存种群", "本代全部请求", "当代 Pareto", "累计 Pareto")
ARCHIVES = {
    "shell_single_parent_v3": "单亲档案 · 新版两代试跑",
    "shell_breeding_v2": "双亲交叉 · 历史试跑",
    "shell_draft_pilot_v1": "局部变异与随机 · 历史对照",
}


def file_signature(root):
    files = [root / "config_snapshot.json", root / "registration.json",
             *sorted(root.glob("*/generation_*.json"))]
    return tuple((p.name, p.stat().st_mtime_ns, p.stat().st_size) for p in files)


def fit_lineage_view(figure, view_key):
    """Fit the complete drawing, including the outermost detours, in a full-width plot."""
    xs, ys = list(figure.layout.xaxis.range), list(figure.layout.yaxis.range)
    for shape in figure.layout.shapes:
        if shape.path:
            # Lineage paths consist of M/L commands and an optional closing Z.
            for vertex in shape.path.split():
                if "," in vertex:
                    x, y = map(float, vertex.split(","))
                    xs.append(x)
                    ys.append(y)
        else:
            xs.extend((shape.x0, shape.x1))
            ys.extend((shape.y0, shape.y1))
    figure.update_layout(uirevision=view_key)
    figure.update_xaxes(range=[min(xs)-.12, max(xs)+.12], domain=[0, 1], constrain="range")
    figure.update_yaxes(range=[min(ys)-.12, max(ys)+.12], domain=[0, 1], constrain="range",
                        scaleanchor="x", scaleratio=1)
    return figure


def lineage_view_key(graph_key, number, cutoff):
    scope = (graph_key, number, cutoff)
    if st.session_state.get("lineage_view_scope") != scope:
        st.session_state["lineage_view_scope"] = scope
        st.session_state["lineage_view_epoch"] = st.session_state.get("lineage_view_epoch", 0) + 1
    return f"{graph_key}_fit_full_{st.session_state['lineage_view_epoch']}"


@st.cache_resource(max_entries=3, show_spinner="载入归档布局")
def get_archive(root, signature):
    archive = Archive(root)
    archive.extent()
    return archive


def controls(generations):
    last = max(generations)
    st.session_state.setdefault("playing", False)
    st.session_state.setdefault("generation", min(1, last))
    st.session_state["generation"] = min(st.session_state["generation"], last)

    def move(offset):
        st.session_state["generation"] = min(last, max(0, st.session_state["generation"]+offset))

    def toggle():
        st.session_state["playing"] = not st.session_state["playing"]
        if st.session_state["playing"] and st.session_state["generation"] == last:
            st.session_state["generation"] = 0
        st.session_state["next_step"] = time.monotonic()+2

    @st.fragment(run_every=2.0 if st.session_state["playing"] else None)
    def ticker():
        if st.session_state["playing"] and time.monotonic() >= st.session_state["next_step"]:
            move(1)
            st.session_state["playing"] = st.session_state["generation"] < last
            st.session_state["next_step"] = time.monotonic()+2
            st.rerun()

    ticker()
    left, mid, right, track = st.columns([1, 1, 1, 5], vertical_alignment="center")
    current = st.session_state["generation"]
    left.button("上一代", on_click=move, args=(-1,), disabled=current == 0, width="stretch")
    mid.button("下一代", on_click=move, args=(1,), disabled=current == last, width="stretch")
    right.button("暂停" if st.session_state["playing"] else "自动播放", on_click=toggle,
                 disabled=last == 0, width="stretch")
    return track.slider("Generation", 0, last, key="generation") if last else 0


def counts(requests, rows):
    records = [rows[key] for key in requests]
    total = len(records)
    valid = sum(row.get("layout_hash") is not None and row["status"] != "INVALID"
                for row in records)
    wins = sum(row.get("outcomes", {}).get("victory", 0) for row in records)
    outcomes = sum(sum(row.get("outcomes", {}).values()) for row in records)
    return total, valid, wins, outcomes


def scope_ids(generation):
    return dict(zip(SCOPES, (generation.survivors, generation.requests,
                            generation.current_pareto, generation.cumulative_pareto)))


def display_stats(rows, ids):
    table = []
    for key in ids:
        row = rows[key]
        s = shown_scores(row)
        q = display_q(row)
        outcomes = row.get("outcomes", {})
        table.append({"个体": key, "出生代": row["born"], "状态": row["status"],
                      "Seed": row["seed"], "胜／死／超时": " / ".join(
                          str(outcomes.get(result, 0)) for result in OUTCOMES) if outcomes else "—",
                      **{axis: round(val, 2) if val is not None else None for axis, val in s.items()},
                      "Q（展示）": round(q, 2) if q is not None else None,
                      "父代": " / ".join(row["parents"]) or "—"})
    st.dataframe(table, hide_index=True, width="stretch")


def evidence(archive, row, generation, reference):
    fields = shown_scores(row)
    cols = st.columns(5)
    for col, (label, value) in zip(cols, (*fields.items(), ("Q · 展示", display_q(row)))):
        col.metric(label, f"{value:.2f}" if value is not None else "—")

    flags = []
    identity = row["id"]
    if identity in generation.survivors:
        flags.append("当代幸存种群")
    if identity in generation.current_pareto:
        flags.append("当代 Pareto")
    if identity in generation.cumulative_pareto:
        flags.append("累计 Pareto")
    if not flags:
        flags.append("保留在评价档案中")
    st.caption(" · ".join(flags))
    outcomes = row.get("outcomes", {})
    if outcomes:
        total = sum(outcomes.values())
        st.write(" · ".join(f"{label} {outcomes.get(k, 0)}" for k, label in OUTCOMES.items())
                 + f" · 进入第二阶段 {row.get('phase2', 0)}/{total} 局")
    operation = row.get("operation") or []
    st.text(f"实际父代 {' × '.join(row['parents']) or '无'}    算子 {' / '.join(map(str, operation)) or '无'}")
    if row.get("crossover") == "fallback":
        st.caption("交叉未通过校验，回退单亲变异。尝试配对 · " + " × ".join(row["attempted_parents"]))
    if exemplar := row.get("archive_reference"):
        st.caption(f"档案参考 {exemplar['id']} · 修改区域 {exemplar['region']} · 谱系线连接实际父代")
    elif row.get("archive_reference_attempted"):
        st.caption("档案参考未通过，已回到常规单亲编辑。")
    if row.get("parent_sample"):
        sample = row["parent_sample"]
        st.caption(f"亲代抽样 · Pareto 第 {sample['rank']} 层 · 此前派生请求 {sample['prior_requests']} 次 · "
                   f"权重 {sample['weight']:.3g}")
    events = row.get("operations") or []
    if events:
        steps = []
        for index, event in enumerate(events, 1):
            name, *parts = event["operation"]
            kind = {"crossover": "交叉", "rewrite_region": "区域重排", "archive_reference": "档案参考编辑"}.get(
                event["kind"], "局部编辑")
            steps.append({"步骤": index, "操作": OP_NAMES.get(name, name),
                          "作用对象": " / ".join(parts), "类型": kind})
        st.dataframe(steps, hide_index=True, width="stretch")
        with st.expander("编辑与继承记录"):
            st.json(events, expanded=1)
    if row.get("topology_changed") is not None:
        st.caption("相对父代的无标签邻接图" + ("发生变化" if row["topology_changed"] else "保持同构"))
    if row.get("missing"):
        st.warning("缺失测量 · " + "、".join(row["missing"]))
    if row.get("failures") or row.get("violations"):
        st.json({"失败与回退": row.get("failures", []), "违规": row.get("violations", {})}, expanded=False)
    if reference:
        before = shown_scores(reference)
        st.dataframe([
            {"目标": key, "对照": round(before[key], 2) if before[key] is not None else None,
             "当前": round(value, 2) if value is not None else None,
             "变化": round(value-before[key], 2) if value is not None and before[key] is not None else None}
            for key, value in fields.items()
        ], hide_index=True, width="stretch")
    with st.expander("Genome 与修复记录"):
        if row.get("genome") is not None:
            st.json(row["genome"], expanded=1)
        else:
            st.write("这次请求没有生成 Genome。")
    score_file = archive.score_path(row)
    if score_file and score_file.is_file():
        with st.expander("评分依据与原始测量"):
            report = read(score_file)
            sections = ("raw", "subscores", "phase_details", "sample_summary", "missing_measurements")
            st.json({key: report.get(key) for key in sections}, expanded=1)
            st.download_button("下载原始评分 JSON", score_file.read_bytes(), "score.json",
                               mime="application/json")


def godot_command(godot, archive, row):
    package = archive.packet_path(row["layout_hash"])
    return [str(godot), "--path", str(ROOT), "--script", "res://full_pcg/viewer/open_candidate.gd",
            "--", str(package), str(archive.root / "config_snapshot.json")]


def candidate_actions(godot, archive, row):
    if row["status"] == "INVALID" or not row.get("layout_hash"):
        return
    file = archive.packet_path(row["layout_hash"])
    a, b = st.columns(2)
    a.download_button("下载原始 Layout 包", file.read_bytes(), f"{row['id']}.json",
                      mime="application/json")
    if b.button("在 Godot 中试玩", disabled=godot is None or not godot.is_file(),
                help="通过启动命令的 --godot 指定本机 Godot 可执行文件。"):
        try:
            subprocess.Popen(godot_command(godot, archive, row), cwd=ROOT)
        except OSError as exc:
            st.error(f"Godot 启动失败：{exc}")
        else:
            st.success(f"已启动 {row['id']} 的战斗白模。")


def choose_reference(generations, rows, row, name_for):
    number = row["born"]
    options = ["无对照", "其他个体"]
    if row["parents"]:
        options.insert(0, "直接父代")
    if number > 0:
        options.insert(-1, "上一代代表")
    mode = st.radio("对照", options)
    if mode == "直接父代":
        ids = row["parents"]
        key = ids[0] if len(ids) == 1 else st.selectbox("父代", ids, format_func=name_for)
        return rows[key], mode
    if mode == "上一代代表":
        key = representative(generations[number-1].current_pareto, rows)
        return (rows[key] if key else None), mode
    if mode == "其他个体":
        choices = [key for key in rows if key != row["id"]]
        key = st.selectbox("对照个体", choices, index=None, placeholder="选择任意已出现的个体",
                           format_func=name_for)
        return (rows[key] if key else None), mode
    return None, mode


def map_panel(archive, current, reference, mode, sidebar, name_for):
    current_layout = archive.layout(current)
    ref_layout = archive.layout(reference) if reference else None
    case = None
    metric = None
    case_index = archive.episode_index(current) if current_layout else {}
    ref_case_index = archive.episode_index(reference) if ref_layout else {}
    with sidebar:
        show_graph = st.toggle("显示 Portal 邻接")
        highlight = st.toggle("高亮父子分区变化", disabled=mode != "直接父代")
        show_trace = st.toggle("叠加单局轨迹")
        if show_trace:
            if case_index:
                case = st.selectbox("已归档对局", list(case_index), format_func=lambda name:
                                    f"{name} · {OUTCOMES.get(case_index[name]['result'], '未知')}")
            else:
                st.caption("该个体没有归档的战斗对局。")
        if st.toggle("叠加 Depthmap 指标"):
            metric = st.selectbox("空间指标", tuple(DEPTHMAP_METRICS), format_func=DEPTHMAP_METRICS.get)
            state = st.selectbox("开口状态", tuple(DEPTHMAP_STATES), format_func=DEPTHMAP_STATES.get)
            if reference:
                st.caption("两图共用同一色标。")
            if metric == DISTANCE:
                st.caption("距离保留原分析模型米。")
    panels = [(current, current_layout, "当前个体", case_index)]
    if reference:
        label = "直接父代" if mode == "直接父代" else "对照个体"
        panels.insert(0, (reference, ref_layout, label, ref_case_index))
    headings = st.columns(2) if reference else (st.container(),)
    for col, (row, layout, label, _) in zip(headings, panels):
        with col:
            st.markdown(f"**{label} {name_for(row['id'])}** · 出生于 G{row['born']} · {row['status']}")
            if layout is None:
                st.info("这次请求没有可显示的布局。详细原因见个体证据。")
            else:
                graph = room_graph(layout)
                st.caption(f"Seed {row['seed']} · {graph.number_of_nodes()} 房 · {graph.number_of_edges()} 对邻接 · "
                           f"{len(layout['portals'])} 个 Portal · {len(layout['obstacles'])} 个障碍")
    grids, notes, limits = {}, {}, None
    if metric:
        for row, layout, _, _ in panels:
            if layout is None:
                continue
            try:
                grid = archive.depthmap(row, state)
            except (OSError, ValueError, KeyError, TypeError):
                notes[row["id"]] = "Depthmap 点位数据与归档不一致或无法读取。"
            else:
                if grid is None:
                    notes[row["id"]] = "该个体没有可读取的归档 Depthmap 点位。"
                else:
                    grids[row["id"]] = grid
        if grids:
            low = min(min(grid.values[metric]) for grid in grids.values())
            high = max(max(grid.values[metric]) for grid in grids.values())
            limits = (low, high) if low < high else (max(0, low-.5), high+.5)
    maps = st.columns(2) if reference else (st.container(),)
    extent = archive.extent()
    comparison_id = reference["id"] if reference else "single"
    view_key = f"maps_{archive.config['run_id']}_{mode}_{comparison_id}_{current['id']}"
    for col, (row, layout, label, episodes) in zip(maps, panels):
        if layout is None:
            continue
        episode = archive.episode(row, case) if case in episodes else None
        grid = grids.get(row["id"])
        fig = draw_layout(layout, archive.scale, extent, topology=show_graph,
                          reference=ref_layout if row is current else None,
                          highlight=highlight and mode == "直接父代", episode=episode,
                          spatial_grid=grid, spatial_metric=metric, spatial_limits=limits)
        with col:
            st.plotly_chart(fig, width="stretch", config={"scrollZoom": True, "doubleClick": "reset"},
                            key=f"{view_key}_{label}")
            if grid:
                st.caption(f"{DEPTHMAP_METRICS[metric]} · {DEPTHMAP_STATES[state]} · "
                           f"{len(grid.positions_m):,} 点 · 原分析网格 {grid.spacing_m:g} 模型米")
                if grid.source_run != archive.root.name:
                    st.caption(f"点位来自继承归档 {grid.source_run}。")
            elif note := notes.get(row["id"]):
                st.caption(note)
            if episode:
                st.caption(f"{case} · {OUTCOMES[episode['result']]} · {episode['duration_s']:.2f} 秒 · "
                           f"终局阶段 {episode['phase']}")
            elif case:
                st.caption(f"该个体没有同场景 {case} 的归档轨迹。")
    if show_trace and case and reference:
        st.caption("两张图使用相同的场景名与扰动，代理动作根据各自布局决定。")
    if highlight and reference and ref_layout and current_layout:
        before = {tuple(sorted((g["a"], g["b"]))) for g in ref_layout["portals"]}
        after = {tuple(sorted((g["a"], g["b"]))) for g in current_layout["portals"]}
        for label, pairs in (("新增邻接", after-before), ("移除邻接", before-after)):
            st.caption(f"{label} · " + ("、".join(" ↔ ".join(p) for p in sorted(pairs)) or "无"))


def choose_from_tree(graph_key, candidate_key, visible_ids):
    event = st.session_state.get(graph_key, {})
    for point in reversed(event.get("selection", {}).get("points", [])):
        if point.get("curve_number", 0) != 0:
            continue
        identity = point.get("customdata")
        if not isinstance(identity, str):
            index = point.get("point_index", point.get("point_number"))
            identity = visible_ids[index] if type(index) is int and 0 <= index < len(visible_ids) else None
        if identity in visible_ids:
            st.session_state[candidate_key] = identity
            st.session_state[f"{candidate_key}_from_tree"] = identity
            return


def inspect_candidate(generation, rows, candidate_key, default, name_for):
    origin_key = f"{candidate_key}_from_tree"

    def clear_selection():
        st.session_state.pop(candidate_key, None)
        st.session_state.pop(origin_key, None)

    st.markdown("**地图控制**")
    source = st.radio("个体范围", SCOPES, key="viewer_candidate_scope", on_change=clear_selection)
    ids = list(scope_ids(generation)[source])
    only_failed = st.toggle("仅看无效或证据不足", key="viewer_candidate_failed", on_change=clear_selection)
    if only_failed:
        ids = [key for key in ids if rows[key]["status"] in {"INVALID", "UNCERTAIN", "ERROR"}]
    selected = st.session_state.get(candidate_key)
    from_tree = st.session_state.get(origin_key)
    if selected is not None and selected == from_tree and selected not in ids:
        ids.insert(0, selected)
        st.caption("已加入从谱系点选的个体。")
    if not ids:
        return None
    if selected not in ids:
        st.session_state[candidate_key] = default if default in ids else ids[0]
    return st.selectbox("当前个体", ids, index=None, key=candidate_key, format_func=name_for)


def render(archive, godot):
    is_pilot = archive.config.get("purpose") == "development_only"
    single_parent = archive.config.get("schema") in SINGLE_PARENT_SCHEMAS
    st.caption(f"{archive.config['run_id']} · {'工程试跑 · 草案评分' if is_pilot else '归档实验'} · "
               f"Map Size {archive.scale:g} · 读取现有归档")
    if archive.config.get("sampling") == "independent":
        st.caption("独立随机采样 · G1 起的候选均无亲代关系")
    arms = list(archive.arms)
    arm = arms[0] if len(arms) == 1 else st.radio(
        "实验组", arms, format_func=lambda k: GROUPS.get(k, k), horizontal=True)
    generations, rows = archive.arms[arm]
    number = controls(generations)
    generation = generations[number]
    representatives = {n: representative(g.current_pareto, rows) for n, g in generations.items()}
    total, valid, wins, episodes = counts(generation.requests, rows)
    tiles = st.columns(4)
    tiles[0].metric("本代可行布局", f"{valid}/{total}")
    tiles[1].metric("本代非同构拓扑", archive.topology_count(arm, number))
    tiles[2].metric("本代模拟胜局", f"{wins}/{episodes}" if episodes else "—")
    tiles[3].metric("当代／累计 Pareto", f"{len(generation.current_pareto)}/{len(generation.cumulative_pareto)}")
    if generation.selection_fallback:
        st.caption("本代归档记录了选择回退。证据不足的个体可查看其原始状态。")

    map_tab, pareto_tab, list_tab, trend_tab = st.tabs(("遗传谱系", "Pareto", "代记录", "评分曲线"))
    with map_tab:
        if single_parent:
            st.caption("△ 原始鼠王关 DXF　□ G0 初始种群／区域重排　○ 局部编辑　＋ 档案参考编辑　× 无效　− 未入选　? 证据不足　≡ 重复　! 错误")
        else:
            st.caption("□ 初始或独立样本　○ 单亲变异　＋ 双亲交叉　× 弃用分支　灰框 缺少完整 Q")
        cutoff = number if single_parent else max(generations)
        graph_key = f"lineage_{archive.config['run_id']}_{arm}"
        if single_parent:
            graph_key += f"_{cutoff}"
        tree_panel = st.container(key="lineage_viewport_short" if cutoff < 2 else "lineage_viewport")
        st.caption("默认适配窗口显示全树。拖拽平移，滚轮放大，双击还原全树。悬停或点选可查看个体详情。"
                   "边框按固定 0–100 的 Q 标尺着色，灰框表示 Q 缺失。"
                   + ("蓝色点线标记 G0 的生成来源。" if single_parent else
                      "实线连接主要父代，虚线连接提供房组的第二父代。"))
        st.caption("S、F、P、D 标出显示范围内各分项最高的完整评分个体，彩线连接其祖先。"
                   "★ 标出最高 Q，最粗的深色线连接其祖先。")
        st.caption("粗实线标出当前个体，粗虚线标出对照个体。缩略图各自适配外框，尺寸对照见下方的同尺度平面图。")
        st.subheader("个体地图与指标")
        inspector = st.container(key="map_inspector")
        maps, sidebar = inspector.columns([3.5, 1.2], gap="medium", vertical_alignment="top")
        sidebar = sidebar.container(key="map_controls", border=True)
        candidate_key = f"{graph_key}_candidate_{number}"
        g0_labels = initial_labels(generations[0]) if single_parent else {}

        def name_for(key):
            label = g0_labels.get(key)
            return f"{label}（{key}）" if label else key

        reference = None
        with sidebar:
            identity = inspect_candidate(generation, rows, candidate_key, representatives[number], name_for)
            row = rows[identity] if identity else None
            if row:
                reference, mode = choose_reference(generations, rows, row, name_for)
        if row:
            cutoff = max(cutoff, row["born"])
        if reference:
            cutoff = max(cutoff, reference["born"])
        highlighted = (identity, reference["id"] if reference else None)
        visible_ids = tuple(key for n in range(cutoff+1) for key in generations[n].requests)
        view_key = lineage_view_key(graph_key, number, cutoff)
        tree = fit_lineage_view(build_lineage(archive, generations, rows, cutoff, highlighted), view_key)
        tree_panel.plotly_chart(tree, theme=None, width="stretch", height="stretch", key=view_key,
                                on_select=lambda: choose_from_tree(view_key, candidate_key, visible_ids),
                                selection_mode="points",
                                config={"displayModeBar": True, "responsive": True, "scrollZoom": True,
                                        "doubleClick": "reset", "modeBarButtonsToRemove": ["autoScale2d"]})
        if row:
            with maps:
                map_panel(archive, row, reference, mode, sidebar, name_for)
            inspected = generations[max(number, row["born"])]
            st.subheader("个体评分与证据")
            removed = discard(generations, row, cutoff)
            if removed:
                st.caption(f"在 G{removed[0]} 弃用 · {removed[1]}")
            evidence(archive, row, inspected, reference)
            candidate_actions(godot, archive, row)
        else:
            maps.info("该范围没有符合条件的个体。")
        st.subheader("进化分析")
        history_col, pareto_col = st.columns(2)
        with history_col:
            st.caption("当代曲线统计幸存种群。历史最高统计截至当代的完整评分请求。")
            st.plotly_chart(q_history(generations, rows), width="stretch")
        with pareto_col:
            st.caption(f"G{number} 四目标 Pareto · S / F 投影")
            st.plotly_chart(plot_pareto(generation.survivors, rows, generation.current_pareto,
                                       "S", "F", identity), width="stretch",
                            key="lineage_pareto_preview")
    with pareto_tab:
        scope = st.radio("解集", ("当代 Pareto", "累计 Pareto"), horizontal=True)
        front = scope_ids(generation)[scope]
        available = generation.survivors if scope == "当代 Pareto" else tuple(
            key for key, row in rows.items() if row["born"] <= number)
        axis_a, axis_b = st.columns(2)
        axis_x = axis_a.selectbox("横轴", OBJECTIVES, index=1)
        axis_y = axis_b.selectbox("纵轴", [a for a in OBJECTIVES if a != axis_x], index=1)
        st.plotly_chart(plot_pareto(available, rows, front, axis_x, axis_y, identity), width="stretch")
        st.caption("高亮点来自归档的四目标 Pareto 解集。图中只投影所选两个轴。")
        if front:
            display_stats(rows, front)
    with list_tab:
        source = st.radio("记录范围", SCOPES, index=1, horizontal=True)
        display_stats(rows, scope_ids(generation)[source])
        requests = [rows[key] for key in generation.requests]
        hashes = [row["layout_hash"] for row in requests if row.get("layout_hash")]
        previous_hashes = {row.get("layout_hash") for row in rows.values() if row["born"] < number}
        repeats = len(hashes) - len(set(hashes) - previous_hashes)
        repaired = sum(bool((row.get("genome") or {}).get("repair_reasons")) for row in requests)
        failures = sum(bool(row.get("failures")) for row in requests)
        st.caption(f"在本代请求中，{len(hashes)} 个保存了布局，{repeats} 个重复出现，"
                   f"{repaired} 个有布局修复记录，{failures} 个有算子失败或回退记录。")
    with trend_tab:
        mode = st.radio("曲线口径", ("当代代表", "当代各目标最优", "累计各目标最优"), horizontal=True)
        st.plotly_chart(plot_scores(generations, rows, representatives, mode), width="stretch")
        st.caption("当代代表为当代 Pareto 中离固定理想点 (100, 100, 100, 100) 最近的个体。"
                   "各目标最优曲线保留各自个体 ID，悬停可查。")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--godot", type=Path)
    args = parser.parse_args()
    st.set_page_config(page_title="关卡进化查看器", layout="wide")
    st.html("""
        <style>
          .stMainBlockContainer { padding-top: 4rem; }
          .st-key-lineage_viewport.stVerticalBlock {
            --lineage-height: clamp(250px, 72dvh, 900px);
          }
          .st-key-lineage_viewport_short.stVerticalBlock {
            --lineage-height: clamp(210px, 42dvh, 450px);
          }
          :is(.st-key-lineage_viewport, .st-key-lineage_viewport_short).stVerticalBlock {
            flex: 0 0 auto;
            height: var(--lineage-height) !important;
            min-height: var(--lineage-height);
            min-width: 0;
          }
          :is(.st-key-lineage_viewport, .st-key-lineage_viewport_short) > [data-testid="stElementContainer"] {
            flex: 1 1 0;
            min-height: 0;
            height: 100%;
          }
          @media (min-width: 1024px) {
            .st-key-map_inspector [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .st-key-map_controls) {
              display: grid;
              grid-template-columns: minmax(0, 1fr) clamp(10rem, 15vw, 12rem);
              width: calc(100% + 3rem);
              max-width: none;
            }
            .st-key-map_inspector [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .st-key-map_controls) > [data-testid="stColumn"] {
              width: auto;
              min-width: 0;
            }
          }
        </style>
    """)
    st.title("关卡进化查看器")
    try:
        root = args.run.resolve()
        if root.name in ARCHIVES:
            choices = [root.with_name(name) for name in ARCHIVES
                       if (root.with_name(name)/"genetic"/"generation_00.json").is_file()]
            archive_key = "known_archive"
            if st.session_state.get(archive_key) not in choices:
                st.session_state[archive_key] = choices[0] if choices else root
            if len(choices) > 1:
                root = st.radio("运行档案", choices, horizontal=True,
                                format_func=lambda p: ARCHIVES[p.name], key=archive_key)
        render(get_archive(root, file_signature(root)), args.godot)
    except (OSError, ValueError, KeyError) as exc:
        st.error(f"归档读取失败：{exc}")


if __name__ == "__main__":
    main()
