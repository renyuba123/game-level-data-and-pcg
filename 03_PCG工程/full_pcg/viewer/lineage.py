"""An archived genealogy arranged by parent branches and birth generation."""

from base64 import b64encode
from html import escape
from itertools import combinations
from math import hypot, sqrt
from statistics import mean, median

import networkx as nx
import plotly.graph_objects as go

from full_pcg.common import ROOT, read
from full_pcg.viewer.archive import OBJECTIVES, SINGLE_PARENT_SCHEMAS, display_q, shown_scores
from full_pcg.viewer.figures import GATE_COLORS, SCORE_COLORS, styled

NODE_SIZE, ROW = 1.04, 1.83
THUMB_HALF, THUMB_MARGIN, CROSS_ARM = 60, 5, .53
CROSS_POINTS = ((-1, -CROSS_ARM), (-CROSS_ARM, -CROSS_ARM), (-CROSS_ARM, -1), (CROSS_ARM, -1),
                (CROSS_ARM, -CROSS_ARM), (1, -CROSS_ARM), (1, CROSS_ARM), (CROSS_ARM, CROSS_ARM),
                (CROSS_ARM, 1), (-CROSS_ARM, 1), (-CROSS_ARM, CROSS_ARM), (-1, CROSS_ARM))
RED_SCALE = [(0, "#f6cccc"), (0.5, "#e2766d"), (1, "#831721")]
LINEAGE_COLORS = {**SCORE_COLORS, "Q": "#252a30"}
LINEAGE_WIDTHS = {**dict.fromkeys(OBJECTIVES, 2.5), "Q": 5}
OP_NAMES = {
    "initial": "初始布局", "random_sample": "随机样本", "graft_corner": "角部房组交叉",
    "merge": "合并房间", "split": "拆分房间", "move_partition": "移动隔墙",
    "shift_opening": "移动门洞", "seal_connection": "封闭连边", "restore_connection": "恢复连边",
    "rewrite_region": "区域重排", "archive_reference": "档案参考编辑",
}
REASONS = {
    "invalid": "无效布局或违反约束", "insufficient_evidence": "评分证据不足",
    "duplicate_layout": "布局重复", "pareto_rank_or_crowding": "未通过 Pareto 排序或拥挤度选择",
}


class LineageLayers:
    """Collect layout elements and validate them once when creating the Plotly figure."""

    def __init__(self):
        self.shapes = []
        self.annotations = []
        self.images = []

    def add_shape(self, **shape):
        self.shapes.append(shape)

    def add_annotation(self, **annotation):
        self.annotations.append(annotation)

    def add_layout_image(self, **layout_image):
        self.images.append(layout_image)


def q_color(q):
    if q is None:
        return "#9eabb4"
    value = min(100, max(0, q))/100
    index = 0 if value <= .5 else 1
    segment = value*2-index
    colors = [color for _, color in RED_SCALE]
    first, second = colors[index], colors[index+1]
    channels = (round(int(first[i:i+2], 16)*(1-segment)+int(second[i:i+2], 16)*segment)
                for i in (1, 3, 5))
    return "#" + "".join(f"{v:02x}" for v in channels)


def discard(generations, row, cutoff):
    identity = row["id"]
    for n in range(row["born"], cutoff+1):
        generation = generations[n]
        if identity in generation.survivors:
            continue
        reason = generation.decisions.get(identity, {}).get("reason")
        if not reason:
            reason = {"INVALID": "invalid", "UNCERTAIN": "insufficient_evidence"}.get(row["status"],
                                                                                   "pareto_rank_or_crowding")
        return n, REASONS.get(reason, reason)
    return None


def plan_coordinates(points, outline):
    xs, zs = zip(*points)
    xmin, xmax, zmin, zmax = min(xs), max(xs), min(zs), max(zs)
    width, depth = xmax-xmin, zmax-zmin
    cx, cz = (xmin+xmax)/2, (zmin+zmax)/2
    span = 2*(THUMB_HALF-THUMB_MARGIN)
    if outline == "triangle":
        # At height z above the base, each side closes in by z/2.
        extent = max(abs(x-cx)+(z-zmin)/2 for x, z in points)
        factor = (THUMB_HALF-1.65*THUMB_MARGIN)/extent
        cz = zmin+(THUMB_HALF-THUMB_MARGIN)/factor
    elif outline == "circle":
        factor = (THUMB_HALF-THUMB_MARGIN)/max(hypot(x-cx, z-cz) for x, z in points)
    elif outline == "cross":
        arm = 2*(THUMB_HALF*CROSS_ARM-THUMB_MARGIN)
        factor = max(min(span/width, arm/depth), min(arm/width, span/depth))
    else:
        factor = min(span/width, span/depth)

    def point(p):
        return THUMB_HALF+(p[0]-cx)*factor, THUMB_HALF-(p[1]-cz)*factor

    return point, factor


def svg_thumbnail(elements):
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="120" height="120" viewBox="0 0 120 120">'
    return "data:image/svg+xml;base64," + b64encode((svg+"".join(elements)+"</svg>").encode()).decode()


def thumbnail(layout, outline):
    rooms, portals = layout["rooms"], layout["portals"]
    if not rooms:
        return None
    points = [point for room in rooms for point in room["polygon"]]
    points.extend(point for gate in portals for point in gate["segment"])
    transform, _ = plan_coordinates(points, outline)

    def point(p):
        x, y = transform(p)
        return f"{x:.2f},{y:.2f}"

    svg = []
    for room in rooms:
        polygon = " ".join(point(p) for p in room["polygon"])
        tint = "#f3ecd6" if room["role"] in ("hall", "foyer") else "#edf0f2"
        svg.append(f'<polygon points="{polygon}" fill="{tint}" stroke="#253440" stroke-width="1.25" />')
    for gate in portals:
        segment = " ".join(point(p) for p in gate["segment"])
        svg.append(f'<polyline points="{segment}" fill="none" stroke="{GATE_COLORS[gate["kind"]]}" stroke-width="1.3" />')
    return svg_thumbnail(svg)


def coordinates_path(points, *, closed=False):
    path = "M " + " L ".join(f"{x:.4f},{y:.4f}" for x, y in points)
    return path + " Z" if closed else path


def add_dxf_root(fig, profile, starters, center):
    y = ROW + .12
    half = NODE_SIZE/2
    bottom = y - half
    triangle = ((center, y+half), (center+half, bottom), (center-half, bottom))
    fig.add_shape(type="path", layer="below", path=coordinates_path(triangle, closed=True), fillcolor="#f5fafb",
                  line={"color": "#507686", "width": 2})
    segments = profile["wall_segments"] + profile["connections"]
    points = [segment[key] for segment in segments for key in ("start_m", "end_m")]
    for block in profile["blocks"]:
        x, z = block["center_m"]
        r = block["radius_m"]
        points.extend(((x-r, z-r), (x+r, z+r)))
    transform, units = plan_coordinates(points, "triangle")
    elements = []
    for segment in segments:
        x0, y0 = transform(segment["start_m"])
        x1, y1 = transform(segment["end_m"])
        color = GATE_COLORS.get(segment.get("kind"), "#253440")
        elements.append(f'<line x1="{x0:.2f}" y1="{y0:.2f}" x2="{x1:.2f}" y2="{y1:.2f}" '
                        f'stroke="{color}" stroke-width="1" />')
    for block in profile["blocks"]:
        x, block_y = transform(block["center_m"])
        elements.append(f'<circle cx="{x:.2f}" cy="{block_y:.2f}" r="{block["radius_m"]*units:.2f}" '
                        'fill="none" stroke="#253440" stroke-width="1" />')
    fig.add_layout_image(source=svg_thumbnail(elements), xref="x", yref="y", x=center, y=y,
                         xanchor="center", yanchor="middle", sizex=NODE_SIZE, sizey=NODE_SIZE,
                         layer="above")
    fig.add_annotation(x=center, y=bottom-.13, text=f"<b>Initial</b> · {escape(profile['source_dxf'])}",
                       showarrow=False, bgcolor="white", borderpad=1, font={"size": 11, "color": "#253440"})
    for x, z in starters:
        fig.add_shape(type="line", layer="below", x0=center, y0=bottom, x1=x, y1=z+half,
                      line={"color": "#507686", "width": 1.2, "dash": "dot"})
    fig.add_annotation(x=center, y=(bottom+half)/2, text="基于 DXF 生成",
                       showarrow=False, bgcolor="white", borderpad=3,
                       font={"size": 11, "color": "#507686"})


def best_lineage(rows, cutoff, metric="Q"):
    candidates = ((-value, identity) for identity, row in rows.items()
                  if row["born"] <= cutoff and row["status"] == "COMPLETE_DRAFT"
                  and (value := (display_q(row) if metric == "Q" else shown_scores(row)[metric])) is not None)
    _, best = min(candidates, default=(0, None))
    edges = set()
    pending = [best] if best is not None else []
    while pending:
        child = pending.pop()
        for parent in rows[child]["parents"]:
            if (parent, child) not in edges:
                edges.add((parent, child))
                pending.append(parent)
    return best, edges


def branch_marker(row, removed, single_parent):
    if not single_parent:
        return ("×", "#c73833", "弃用") if removed else None
    if row["status"] == "INVALID":
        return "×", "#c73833", "验证无效"
    if row["status"] == "ERROR":
        return "!", "#8c5b32", "系统错误"
    if row.get("duplicate_layout"):
        return "≡", "#667681", "重复布局"
    if row["status"] == "UNCERTAIN":
        return "?", "#677786", "证据不足"
    if removed:
        return "−", "#798792", "未入选"
    return None


def node_outline(row):
    if len(row["parents"]) == 2 or row.get("edit") == "archive_reference":
        return "cross"
    return "rect" if not row["parents"] or row.get("edit") == "full" else "circle"


def initial_labels(generation):
    return {key: f"G0 · {i:02d}" for i, key in enumerate(generation.requests, 1)}


def branch_positions(generations, rows, cutoff):
    ids = [key for n in range(cutoff+1) for key in generations[n].requests]
    children = {key: [] for key in ids}
    roots = []
    for key in ids:
        parents = rows[key]["parents"]
        if parents:
            children[parents[0]].append(key)
        else:
            roots.append(key)
    born = {key: rows[key]["born"] for key in ids}

    def pack(group, gap, share_parent=False):
        packed, right_edge = {}, {}
        previous = None
        for key in group:
            siblings = children[key]
            branch = pack(siblings, 1.40, share_parent=True)
            branch[key] = (branch[siblings[0]]+branch[siblings[-1]])/2 if siblings else 0
            # Compare subtree contours at actual birth generations. This leaves room for
            # a real direct edge from a parent reused after an intervening generation.
            limits = [right_edge[born[member]]+gap-x for member, x in branch.items()
                      if born[member] in right_edge]
            if share_parent and previous is not None:
                limits.append(packed[previous]+1.10-branch[key])
            offset = max(0, max(limits, default=0))
            for member, x in branch.items():
                packed[member] = x+offset
                row = born[member]
                right_edge[row] = max(right_edge.get(row, 0), packed[member])
            previous = key
        return packed

    x_coordinates = pack(roots, 1.55)
    # Compress long gaps on busy rows while retaining family order and clearance.
    max_span = (max(len(generations[n].requests) for n in range(cutoff+1))-1)*1.60
    for n in range(cutoff+1):
        cohort = sorted(generations[n].requests, key=x_coordinates.__getitem__)
        left, right = (x_coordinates[cohort[i]] for i in (0, -1))
        span = right-left
        if span > max_span:
            floor = 1.32*(len(cohort)-1)
            factor = (max_span-floor)/(span-floor)
            start = (left+right-max_span)/2
            for i, key in enumerate(cohort):
                x_coordinates[key] = start+i*1.32+(x_coordinates[key]-left-i*1.32)*factor
    initial = generations[0].requests
    center = (min(x_coordinates[key] for key in initial)+max(x_coordinates[key] for key in initial))/2
    positions = {key: (x_coordinates[key], -born[key]*ROW) for key in ids}
    return positions, center


def lineage_port(position, toward_x, outline, upper):
    x, y = position
    half = NODE_SIZE/2
    lean = max(-.25, min(.25, .15*(toward_x-x)))
    rise = sqrt(half**2-lean**2) if outline == "circle" else half
    return x+lean, y+rise if upper else y-rise


def crosses_box(start, end, box):
    enter, leave = 0, 1
    for a, b, lo, hi in zip(start, end, box[:2], box[2:]):
        delta = b-a
        if not delta:
            if a <= lo or a >= hi:
                return False
        else:
            first, last = sorted(((lo-a)/delta, (hi-a)/delta))
            enter, leave = max(enter, first), min(leave, last)
    return leave-enter > 1e-8


def lineage_route(start, end, boxes):
    boxes = [box for box in boxes if box[1] < start[1] and box[3] > end[1]]
    if not any(crosses_box(start, end, box) for box in boxes):
        return [start, end]
    if len(boxes) > 24:
        # Long archival jumps can route outside the cards without a cubic visibility search.
        start_y, end_y = start[1]-.24, end[1]+.24
        paths = [
            [start, (start[0], start_y), (rail, start_y), (rail, end_y), (end[0], end_y), end]
            for rail in (min(box[0] for box in boxes)-.12, max(box[2] for box in boxes)+.12)
        ]
        for path in sorted(paths, key=lambda points: abs(points[2][0]-start[0])+abs(points[2][0]-end[0])):
            if not any(crosses_box(a, b, box) for a, b in zip(path, path[1:]) for box in boxes):
                return path
    # A short detour around a card keeps an older or secondary parent edge readable.
    corners = [(x, y) for x0, y0, x1, y1 in boxes for x in (x0, x1) for y in (y0, y1)]
    graph = nx.DiGraph()
    graph.add_nodes_from((start, end))
    for a, b in combinations(sorted({start, end, *corners}, key=lambda point: (-point[1], point[0])), 2):
        if end[1] <= b[1] <= a[1] <= start[1] and not any(crosses_box(a, b, box) for box in boxes):
            distance = hypot(a[0]-b[0], a[1]-b[1])
            graph.add_edge(a, b, weight=distance)
            if a[1] == b[1]:
                graph.add_edge(b, a, weight=distance)
    if nx.has_path(graph, start, end):
        return nx.shortest_path(graph, start, end, weight="weight")
    return [start, end]


def add_lineage_edge(fig, route, secondary, metrics):
    # Parallel strokes keep each objective readable when winners share an ancestor.
    dash = "dash" if secondary else "solid"
    if not metrics:
        tracks = [(0, "#365e70" if secondary else "#66737d", 1.15)]
    else:
        side_metrics = [metric for metric in metrics if metric != "Q"]
        offsets = (-.12, .12, -.21, .21) if "Q" in metrics else (
            .09*(i-(len(side_metrics)-1)/2) for i in range(len(side_metrics))
        )
        tracks = [(offset, LINEAGE_COLORS[metric], LINEAGE_WIDTHS[metric])
                  for offset, metric in zip(offsets, side_metrics)]
        if "Q" in metrics:
            tracks.append((0, LINEAGE_COLORS["Q"], LINEAGE_WIDTHS["Q"]))
    (ax, ay), (bx, by) = route[0], route[-1]
    dx, dy = bx-ax, by-ay
    length = hypot(dx, dy)
    for offset, color, width in tracks:
        shifted = [(x-offset*dy/length, y+offset*dx/length) for x, y in route] if offset else route
        (ax, ay), (bx, by) = shifted[0], shifted[-1]
        geometry = ({"type": "line", "x0": ax, "y0": ay, "x1": bx, "y1": by} if len(shifted) == 2
                    else {"type": "path", "path": coordinates_path(shifted)})
        fig.add_shape(**geometry, layer="below", line={"color": color, "width": width, "dash": dash})


def build_lineage(archive, generations, rows, cutoff, highlighted=None, *, single_parent=None):
    current_id, comparison_id = highlighted if isinstance(highlighted, tuple) else (highlighted, None)
    if single_parent is None:
        single_parent = archive.config.get("schema") in SINGLE_PARENT_SCHEMAS
    fig = LineageLayers()
    placements, center = branch_positions(generations, rows, cutoff)
    left = min(x for x, _ in placements.values())
    right = max(x for x, _ in placements.values())
    half = NODE_SIZE/2
    compact = cutoff >= 7
    profile = None
    if single_parent:
        source = read(ROOT/"data/shell_source_v2.json")
        initial_layouts = [archive.layout(rows[key]) for key in generations[0].requests if rows[key]["layout_hash"]]
        if initial_layouts and all(layout.get("source_dxf_sha256") == source["source_dxf_sha256"]
                                   for layout in initial_layouts):
            profile = source
    coords = {}
    g0_labels = initial_labels(generations[0])
    for n in range(cutoff+1):
        ids = generations[n].requests
        y = -n*ROW
        row_label = f"G{n}" if single_parent else f"GEN {n}"
        text = f"<b>{row_label}</b>" if compact else f"<b>{row_label}</b><br>{len(ids)} 个"
        fig.add_annotation(x=left-1.10, y=y, text=text, showarrow=False,
                           font={"color": "#65737e", "size": 11})
    leaders = {metric: best_lineage(rows, cutoff, metric) for metric in LINEAGE_COLORS}
    edges = []
    pad = half+.06
    obstacles = {key: (x-pad, y-pad, x+pad, y+pad) for key, (x, y) in placements.items()}
    for identity, (x, y) in placements.items():
        for i, parent in enumerate(rows[identity]["parents"]):
            metrics = [metric for metric, (_, path) in leaders.items() if (parent, identity) in path]
            start = lineage_port(placements[parent], x, node_outline(rows[parent]), upper=False)
            end = lineage_port((x, y), placements[parent][0], node_outline(rows[identity]), upper=True)
            boxes = [box for key, box in obstacles.items() if key not in (identity, parent)]
            edges.append((metrics, lineage_route(start, end, boxes), i))
    for metrics, route, i in sorted(edges, key=lambda edge: (bool(edge[0]), "Q" in edge[0])):
        add_lineage_edge(fig, route, i != 0, metrics)
    if profile:
        add_dxf_root(fig, profile, (placements[key] for key in generations[0].requests), center)
    for identity, (x, y) in placements.items():
        row = rows[identity]
        q = display_q(row)
        score = f"{q:.1f}" if q is not None else "—"
        removed = discard(generations, row, cutoff)
        color = q_color(q)
        outline = node_outline(row)
        if outline == "cross":
            points = [(x+px*half, y+py*half) for px, py in CROSS_POINTS]
            coords_for_shape = {"type": "path", "path": coordinates_path(points, closed=True)}
        else:
            coords_for_shape = {"type": outline, "x0": x-half, "x1": x+half,
                                "y0": y-half, "y1": y+half}
        comparison = identity == comparison_id and identity != current_id
        active = identity == current_id
        fig.add_shape(**coords_for_shape, layer="below", fillcolor="white",
                      line={"color": color, "width": 4 if active or comparison else 2,
                            "dash": "dash" if comparison else "solid"})
        layout = archive.layout(row)
        if layout:
            source = thumbnail(layout, outline)
            if source:
                fig.add_layout_image(source=source, xref="x", yref="y", x=x, y=y,
                                     xanchor="center", yanchor="middle", sizex=NODE_SIZE,
                                     sizey=NODE_SIZE, sizing="contain", layer="above")
        elif not compact:
            fig.add_annotation(x=x, y=y, text="无布局", showarrow=False,
                               font={"size": 10, "color": "#697780"})
        label = g0_labels.get(identity, identity) if single_parent else identity
        if not compact:
            fig.add_annotation(x=x, y=y-half-.19, text=f"{escape(label)}<br><b>Q {score}</b>",
                               showarrow=False, bgcolor="white", borderpad=1,
                               font={"size": 10, "color": "#253440"})
        badges = [metric for metric in OBJECTIVES if leaders[metric][0] == identity]
        for i, metric in enumerate(badges):
            fig.add_annotation(x=x, y=y+.60, xshift=14*(i-(len(badges)-1)/2), text=f"<b>{metric}</b>",
                               showarrow=False, font={"color": LINEAGE_COLORS[metric], "size": 11 if compact else 15},
                               hovertext=f"最高 {metric} · {shown_scores(row)[metric]:.1f}")
        if identity == leaders["Q"][0]:
            fig.add_annotation(x=x+.46, y=y+.49, text="<b>★</b>", showarrow=False,
                               font={"color": "#a16a09", "size": 14 if compact else 19}, hovertext=f"最高 Q · {q:.1f}")
        marker = branch_marker(row, removed, single_parent)
        if marker:
            symbol, marker_color, meaning = marker
            bx, by = x+.61, y-.59
            fig.add_shape(type="line", x0=x+half*.94, x1=bx, y0=y-.17, y1=by,
                          line={"color": marker_color, "width": 1})
            fig.add_annotation(x=bx, y=by, text=f"<b>{symbol}</b>", showarrow=False,
                               font={"color": marker_color, "size": 12 if compact else 23}, hovertext=meaning)
        status = (f"G{removed[0]} {removed[1]}" if removed else f"G{cutoff} 仍保留")
        if marker and single_parent:
            status = f"{marker[2]} · {status}"
        op = row.get("operation") or [""]
        parents = " × ".join(row["parents"]) or "无"
        coords[identity] = (x, y, f"<b>{escape(identity)}</b><br>Q {score}<br>{escape(status)}"
                            f"<br>{escape(OP_NAMES.get(op[0], op[0]))}<br>父代 {escape(parents)}")
    # Hit regions use plot units, so they follow each thumbnail when zoomed or panned.
    fig = go.Figure(layout={"shapes": fig.shapes, "annotations": fig.annotations, "images": fig.images})
    fig.add_bar(x=[p[0] for p in coords.values()], y=[NODE_SIZE]*len(coords),
                base=[p[1]-half for p in coords.values()], width=NODE_SIZE,
                marker={"color": "rgba(0,0,0,0.01)", "line": {"width": 0}},
                customdata=list(coords), hovertext=[p[2] for p in coords.values()],
                hovertemplate="%{hovertext}<extra></extra>", showlegend=False, name="个体")
    fig.add_scatter(x=[None, None], y=[None, None], mode="markers", showlegend=False,
                    marker={"color": [0,100], "cmin": 0, "cmax": 100, "colorscale": RED_SCALE, "showscale": True,
                            "colorbar": {"title": {"text": "Q"}, "thickness": 10, "len": .68, "tickvals": [0,25,50,75,100]}})
    fig.update_layout(autosize=True, dragmode="pan", clickmode="event+select", hovermode="closest",
                      barmode="overlay", uirevision=f"{archive.config['run_id']}:{cutoff}:full-width",
                      margin={"l": 14, "r": 66, "t": 8, "b": 10}, plot_bgcolor="white", paper_bgcolor="white")
    # Keep the interactive plot area full width. Equal aspect expands the data range
    # on resize instead of squeezing the clipping rectangle into a central strip.
    fig.update_xaxes(visible=False, range=[left-1.53, right+.93], fixedrange=False, constrain="range")
    fig.update_yaxes(visible=False, range=[min(y for _, y in placements.values())-.91, ROW+.81 if profile else .83],
                     fixedrange=False, constrain="range", scaleanchor="x", scaleratio=1)
    return fig


def q_history(generations, rows):
    fig = go.Figure()
    numbers = list(generations)
    cohorts = [[q for identity in generations[n].survivors
                if rows[identity]["status"] == "COMPLETE_DRAFT"
                and (q := display_q(rows[identity])) is not None] for n in numbers]
    for label, statistic, color in (("当代最高 Q", max, "#a4272e"), ("当代均值", mean, "#566772"),
                                     ("中位数", median, "#9cabb5")):
        fig.add_scatter(x=numbers, y=[statistic(cohort) if cohort else None for cohort in cohorts],
                        text=[f"{len(cohort)} 个完整 Q" for cohort in cohorts], mode="lines+markers",
                        line={"color": color}, name=label,
                        hovertemplate="G%{x} · %{y:.2f}<br>%{text}<extra></extra>")
    history, best = [], None
    for number in numbers:
        for identity in generations[number].requests:
            q = display_q(rows[identity])
            if rows[identity]["status"] == "COMPLETE_DRAFT" and q is not None:
                best = q if best is None else max(best, q)
        history.append(best)
    fig.add_scatter(x=numbers, y=history, mode="lines+markers", name="历史最高 Q",
                    line={"color": "#a56a08", "dash": "dash", "shape": "hv"},
                    hovertemplate="G%{x} · 历史最高 %{y:.2f}<extra></extra>")
    return styled(fig, 340).update_xaxes(title="Generation", dtick=1).update_yaxes(
        title="Q", range=[0, 100])
