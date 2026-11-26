"""Plot the archived Layout and battle evidence in consistent world coordinates."""

import plotly.graph_objects as go

from full_pcg.viewer.archive import display_q, shown_scores
from full_pcg.viewer.depthmap import DEPTHMAP_METRICS, DISTANCE

INK = "#213745"
GRID = "#e9eff3"
GATE_COLORS = {"normal": "#7693a2", "through": "#087a95", "window": "#8355ae", "break": "#bf5828"}
PHASE_COLORS = {1: "#1b69ae", 2: "#b03e19"}
SCORE_COLORS = {"S": "#14636a", "F": "#4a67a8", "P": "#bd562c", "D": "#8b58a8"}
EVENTS = {
    "hit": ("命中时玩家位置", "#a56119", "circle-open"),
    "pickup_end": ("拾取", "#86630e", "square"),
    "split": ("分裂", "#9b3999", "diamond"),
    "portal_open": ("通道破坏", "#8355ae", "triangle-up"),
    "death": ("死亡", "#b5243a", "x"),
    "victory": ("胜利", "#157653", "star"),
}


def styled(fig, height):
    return fig.update_layout(
        height=height, paper_bgcolor="white", plot_bgcolor="white",
        font={"color": INK, "family": "Microsoft YaHei, Noto Sans CJK SC, sans-serif"},
        margin={"l": 48, "r": 20, "t": 14, "b": 42},
        legend={"orientation": "h", "y": -0.19, "font": {"size": 11}},
        hoverlabel={"namelength": -1},
    ).update_xaxes(gridcolor=GRID).update_yaxes(gridcolor=GRID)


def lines(fig, paths, scale=1, **kwargs):
    x, y = [], []
    for path in paths:
        if path:
            x.extend([p[0]*scale for p in path] + [None])
            y.extend([p[1]*scale for p in path] + [None])
    if x:
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", **kwargs))


def room_color(room):
    if room["role"] in {"hall", "foyer"}:
        return "#f5e2ad"
    return "#c9dce9" if room["id"].startswith("east") else "#cddfd4"


def changed_rooms(layout, reference):
    if reference is None:
        return set(), set()
    a = {r["id"]: r["polygon"] for r in layout["rooms"]}
    b = {r["id"]: r["polygon"] for r in reference["rooms"]}
    return {key for key, value in a.items() if value != b.get(key)}, set(b) - set(a)


def draw_room(fig, room, scale, outline=None, *, filled=True):
    path = room["polygon"]
    if path[-1] != path[0]:
        path = [*path, path[0]]
    label = f"{room['id']} · {room['role']} · {room['area']*scale**2:.1f} m²"
    lines(fig, [path], scale, fill="toself" if filled else None, fillcolor=room_color(room),
          line={"color": outline or "#84969f", "width": 2.7 if outline else 0.7},
          name=label, hoveron="points+fills", hovertemplate="%{fullData.name}<extra></extra>",
          showlegend=False)


def draw_depthmap(fig, grid, metric, scale, limits):
    xs, zs = zip(*grid.positions_m)
    left, bottom = min(xs), min(zs)
    step = grid.spacing_m
    columns = round((max(xs)-left)/step)+1
    rows = round((max(zs)-bottom)/step)+1
    matrix = [[None]*columns for _ in range(rows)]
    for (x, z), value in zip(grid.positions_m, grid.values[metric]):
        matrix[round((z-bottom)/step)][round((x-left)/step)] = value
    label = DEPTHMAP_METRICS[metric]
    unit = " 模型米" if metric == DISTANCE else " 点" if metric == "Connectivity" else ""
    number = ".0f" if metric == "Connectivity" else ".2f"
    fig.add_heatmap(
        x0=left*scale, dx=step*scale, y0=bottom*scale, dy=step*scale, z=matrix,
        zmin=limits[0], zmax=limits[1], colorscale="Viridis", opacity=.85, zsmooth=False,
        connectgaps=False, hoverongaps=False, name=label,
        colorbar={"title": {"text": "模型米" if metric == DISTANCE else "点" if unit else "HH", "side": "top"},
                  "len": .88, "thickness": 10, "x": 1.02, "tickfont": {"size": 10}},
        hovertemplate=f"{label} %{{z:{number}}}{unit}<br>X %{{x:.2f}} · Z %{{y:.2f}}<extra></extra>",
    )


def draw_layout(layout, scale, extent, *, topology=False, reference=None,
                highlight=False, episode=None, spatial_grid=None, spatial_metric=None, spatial_limits=None):
    fig = go.Figure()
    positions = {room["id"]: room["center"] for room in layout["rooms"]}
    changed, removed = changed_rooms(layout, reference if highlight else None)
    if spatial_grid:
        draw_depthmap(fig, spatial_grid, spatial_metric, scale, spatial_limits)
    for room in layout["rooms"]:
        draw_room(fig, room, scale, "#b14233" if room["id"] in changed else None, filled=spatial_grid is None)
    walls = layout["walls"]
    surfaces = ([walls["coordinates"]] if walls["type"] == "Polygon" else walls["coordinates"])
    faces = [ring for polygon in surfaces for ring in polygon]
    lines(fig, faces, scale, line={"color": "#3d5262", "width": 1.4},
          name="实体墙", hoverinfo="skip", showlegend=False)
    if removed:
        lines(fig, [r["polygon"] for r in reference["rooms"] if r["id"] in removed], scale,
              line={"color": "#a54363", "width": 2, "dash": "dot"},
              name="参照图中移除的房间", hoverinfo="skip")
    for kind, color in GATE_COLORS.items():
        gates = [g for g in layout["portals"] if g["kind"] == kind]
        if topology:
            paths = [[positions[g["a"]], g["center"], positions[g["b"]]] for g in gates]
            lines(fig, paths, scale, name=f"{kind} 邻接", hoverinfo="skip",
                  line={"color": color, "dash": "dot", "width": 1.5})
        for gate in gates:
            label = f"{gate['id']} · {kind} · {gate['a']} ↔ {gate['b']}"
            lines(fig, [gate["segment"]], scale, name=kind, legendgroup=kind,
                  showlegend=gate is gates[0], text=[label]*3,
                  hovertemplate="%{text}<extra></extra>", line={"color": color, "width": 4})
    for obstacle in layout["obstacles"]:
        x, z = (p*scale for p in obstacle["position"])
        radius = obstacle["radius"]
        fig.add_shape(type="circle", x0=x-radius, x1=x+radius, y0=z-radius, y1=z+radius,
                      line={"width": 0}, fillcolor="#736759")
    markers = [
        ("玩家", [layout["spawn"]], "#087c50", "circle"),
        ("Boss", [layout["boss"]], "#af343f", "circle"),
        ("补给", layout["supplies"], "#8a640e", "cross"),
    ]
    for name, objects, color, symbol in markers:
        fig.add_scatter(x=[obj["position"][0]*scale for obj in objects],
                        y=[obj["position"][1]*scale for obj in objects],
                        text=[obj.get("id", obj.get("room")) for obj in objects],
                        mode="markers", name=name, marker={"color": color, "symbol": symbol, "size": 9},
                        hovertemplate="%{fullData.name} · %{text}<extra></extra>")
    if topology:
        fig.add_scatter(x=[p[0]*scale for p in positions.values()],
                        y=[p[1]*scale for p in positions.values()], text=list(positions),
                        mode="markers+text", textposition="top center",
                        marker={"size": 5, "color": INK}, showlegend=False, name="房间节点")
    if episode:
        draw_episode(fig, episode, layout, scale)
    x0, z0, x1, z1 = extent
    styled(fig, 505)
    # Reserve the same plotting area even if only one map has extra legend entries.
    fig.update_layout(margin={"l": 58, "r": 66 if spatial_limits else 20, "t": 26, "b": 135, "autoexpand": False},
                      legend={"y": -.17, "yanchor": "top", "maxheight": 72})
    fig.update_xaxes(range=[x0, x1], title="世界 X（模型米）", constrain="domain")
    fig.update_yaxes(range=[z0, z1], title="世界 Z（模型米）", scaleanchor="x",
                     scaleratio=1, constrain="domain")
    return fig


def draw_episode(fig, episode, layout, scale):
    frames = episode["frames"]
    stride = max(1, len(frames)//1000)
    lines(fig, [[f["b"] for f in frames[::stride]]], name="Boss 轨迹", hoverinfo="skip",
          line={"color": "#852656", "width": 1.3, "dash": "dot"})
    for phase, color in PHASE_COLORS.items():
        positions = [f["p"] for f in frames if f["phase"] == phase]
        points = positions[::stride] + positions[-1:]
        lines(fig, [points], name=f"玩家阶段 {phase}", hoverinfo="skip",
              line={"color": color, "width": 2.2})
    gates = {gate["id"]: gate["center"] for gate in layout["portals"]}
    for kind, (label, color, symbol) in EVENTS.items():
        events = [e for e in episode["events"] if e["kind"] == kind]
        if not events:
            continue
        points = []
        for event in events:
            frame = frames[max(0, min(len(frames)-1, event["step"]-1))]
            gate = gates.get(event["data"].get("id")) if kind == "portal_open" else None
            points.append([v*scale for v in gate] if gate else frame["b" if kind == "split" else "p"])
        fig.add_scatter(x=[p[0] for p in points], y=[p[1] for p in points],
                        text=[f"{label} · {e['t']:.2f} s" for e in events], mode="markers",
                        marker={"color": color, "symbol": symbol, "size": 8},
                        showlegend=False, name=label, hovertemplate="%{text}<extra></extra>")


def plot_pareto(ids, rows, front, axis_x, axis_y, identity):
    fig = go.Figure()
    for on_front in (False, True):
        group = [key for key in ids if (key in front) == on_front and
                 all(shown_scores(rows[key])[axis] is not None for axis in (axis_x, axis_y))]
        if not group:
            continue
        fig.add_scatter(x=[rows[key]["scores"][axis_x] for key in group],
                        y=[rows[key]["scores"][axis_y] for key in group],
                        text=group, mode="markers", name="四目标 Pareto" if on_front else "其他已测",
                        marker={"color": "#087c72" if on_front else "#8195a4",
                                "size": [14 if key == identity else 9 for key in group],
                                "symbol": ["diamond" if key == identity else "circle" for key in group]},
                        hovertemplate="%{text}<br>%{x:.2f} / %{y:.2f}<extra></extra>")
    return styled(fig, 395).update_xaxes(title=axis_x, range=[-3, 103]).update_yaxes(
        title=axis_y, range=[-3, 103])


def plot_scores(generations, rows, representatives, mode):
    fig = go.Figure()
    numbers = list(generations)
    for axis, color in SCORE_COLORS.items():
        if mode == "当代代表":
            values = [shown_scores(rows[representatives[n]])[axis] if representatives[n] else None
                      for n in numbers]
            identities = [representatives[n] for n in numbers]
        else:
            identities = []
            for n in numbers:
                candidates = generations[n].survivors if mode == "当代各目标最优" else [
                    key for key, row in rows.items() if row["born"] <= n]
                complete = [key for key in candidates if display_q(rows[key]) is not None and
                            rows[key]["status"] in {"VALID", "COMPLETE_DRAFT"}]
                identities.append(max(complete, key=lambda key: (rows[key]["scores"][axis], key))
                                  if complete else None)
            values = [rows[key]["scores"][axis] if key else None for key in identities]
        fig.add_scatter(x=numbers, y=values, text=identities, mode="lines+markers",
                        name=axis, line={"color": color},
                        hovertemplate="%{text}<br>%{fullData.name} %{y:.2f}<extra></extra>")
    return styled(fig, 370).update_xaxes(title="Generation", dtick=1).update_yaxes(
        title="分数", range=[-3, 103])
