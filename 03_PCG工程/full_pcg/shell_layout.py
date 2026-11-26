"""DXF envelope subdivision for the rat king editor preview."""
import argparse
import itertools
import math
import random
from pathlib import Path

import networkx as nx
import numpy as np
from shapely import set_precision
from shapely.geometry import Point, Polygon, LineString, box, mapping, shape
from shapely.ops import polygonize, unary_union, polylabel
import sys
if __package__ in (None,"") and (Path(__file__).resolve().parents[1]/"project.godot").exists():
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from full_pcg.common import ROOT, digest, read, write
from full_pcg.godot_export import package, triangles
from full_pcg.validation import validate
from combat_pcg.layouts import _choose_spawns
from combat_pcg.protocol import default_combat
from full_pcg.room_limits import EAST_LOW, HALF_WALL, measure


def shell_reference(source):
    lines = [set_precision(LineString([w["start_m"], w["end_m"]]), .0001) for w in source["wall_segments"]]
    return max((Polygon(p.exterior) for p in polygonize(unary_union(lines))), key=lambda p:p.area)


# Design threshold for sibling clear floor areas. The two DXF inner-wall
# witnesses in room_limits still govern minimum dimensions on both sides.
MIN_SIBLING_RATIO = 1.8


def unequal_pair(host_name, host, small_name, small):
    if any(p.is_empty or p.geom_type != "Polygon" for p in (host,small)):
        return False
    host_size = measure(host_name, host)
    small_size = measure(small_name, small)
    return bool(host_size and small_size and
                host_size["net_area"] >= MIN_SIBLING_RATIO * small_size["net_area"])


def corner_l(host, pocket):
    """The two perpendicular arms and their corner room must tile one rectangle."""
    if any(p.geom_type != "Polygon" or p.is_empty or p.interiors for p in (host,pocket)):
        return False
    parent = host.union(pocket)
    if parent.geom_type != "Polygon": return False
    xmin,ymin,xmax,ymax = parent.bounds
    x0,y0,x1,y1 = pocket.bounds
    eps = 1e-5  # sub-millimetre overlay rounding, in model metres
    if not ((abs(x0-xmin)<eps) != (abs(x1-xmax)<eps)): return False
    if not ((abs(y0-ymin)<eps) != (abs(y1-ymax)<eps)): return False
    cut = box(x0,y0,x1,y1)
    envelope = box(xmin,ymin,xmax,ymax)
    return (pocket.symmetric_difference(cut).area < eps and
            host.symmetric_difference(envelope.difference(cut)).area < eps)


def corner_room(parent, host_name, small_name, rng, *, preferred_corner=None):
    """Carve a corner with two shared perpendicular wall runs and a usable return."""
    xmin,ymin,xmax,ymax = parent.bounds
    long,short = EAST_LOW
    sizes = [(long,short),(short,long)]
    corners = [(False,False),(False,True),(True,False),(True,True)]
    if preferred_corner is None:
        rng.shuffle(corners)
    else:
        corners = [preferred_corner]
    rng.shuffle(sizes)
    for w,h in sizes:
        w += 2*HALF_WALL + rng.uniform(.025,.14)
        h += 2*HALF_WALL + rng.uniform(.025,.14)
        for east,north in corners:
            if host_name == "east_high" and not (east or north): continue
            x = xmax-w if east else xmin
            y = ymax-h if north else ymin
            small = box(x,y,x+w,y+h)
            if not parent.buffer(1e-8).covers(small): continue
            small = parent.intersection(small)
            host = parent.difference(small)
            contact = small.boundary.intersection(host.boundary)
            spans = [l.bounds for l in getattr(contact,"geoms",[contact]) if l.geom_type=="LineString"]
            if not (any(b-a>1.85 for a,_,b,_ in spans) and any(d-c>1.85 for _,c,_,d in spans)):
                continue
            if corner_l(host,small) and unequal_pair(host_name,host,small_name,small):
                return host,small
    return None


def reference_net_area(source):
    # Select the playable DXF face by maximum overlap with the measured convex floor.
    lines = [set_precision(LineString([w["start_m"], w["end_m"]]),.0001) for w in source["wall_segments"]]
    reference = unary_union([Polygon(r["polygon_m"]) for r in source["convex_rooms"]])
    floor = max(polygonize(unary_union(lines)),key=lambda f:f.intersection(reference).area)
    blocks = unary_union([Point(b["center_m"]).buffer(b["radius_m"],quad_segs=12) for b in source["blocks"]])
    return floor.difference(blocks).area


def fit_outer_wings(shell,cells,target):
    # Move the two end facades within the shell. The inset east rooms and
    # the entire middle corridor retain their original world coordinates.
    from shapely.affinity import scale
    west = cells["left_inner"].bounds[0]
    east = cells["east_end"].bounds[0]
    # Even when the southern return reaches the western facade, a band inside
    # the west wing can absorb part of the reduction.
    west = max(west,shell.bounds[0]+2.8)
    middle=box(west,-100,east,100)
    bands=[(box(-100,-100,west,100),west),(box(east,-100,100,100),east)]
    ends=shell.area-shell.intersection(middle).area
    factor=max(.68,min(1.,1-(shell.area-target)/ends))
    def fit(poly):
        parts=[poly.intersection(middle)]
        for band,origin in bands:
            parts.append(scale(poly.intersection(band),xfact=factor,yfact=1,origin=(origin,0)))
        return set_precision(unary_union(parts).buffer(0),.000001)
    return fit(shell),{k:fit(p) for k,p in cells.items()}


def divide(seed, source, shape_attempt=0, partition_attempt=0):
    rng = random.Random(seed)
    original = shell_reference(source)
    # Piecewise affine horizontal scaling keeps the left, neck and right landmarks ordered.
    scales = [rng.uniform(.91, 1.11) for _ in range(3)]
    depth = rng.uniform(.94, 1.10)
    def x(v):
        return .70*min(1,max(0,(v-10.3127)/3.7)) + v*scales[0] + max(0,v-8.2)*(scales[1]-scales[0]) + max(0,v-14)*(scales[2]-scales[1])
    # Draw a single exterior first. The wing spans, north/south projections,
    # shoulder, and east facade are genes; only the through-hall relationship is fixed.
    form=random.Random(f"envelope:{seed}:{shape_attempt}" if partition_attempt<2 else
                       f"envelope:{seed}:{shape_attempt}:repair:{partition_attempt}")
    west=form.uniform(-3.5,.2)
    south=form.uniform(-6.8,-4.75)
    north_tip=form.uniform(8.65,10.25)
    east=form.uniform(19.75,21.8)
    upper=form.uniform(2.05,3.10)
    lower=form.uniform(-2.85,-1.75)
    bevel=form.choice([0.,.45,.95])
    # A rectangular, chamfered, or stepped terminal changes the actual corner sequence.
    nose=[(east,upper),(east,lower)] if bevel==0 else [(east-bevel,upper),(east,upper-bevel),(east,lower+bevel),(east-bevel,lower)]
    if form.random()<.33:
        nose=[(east-1.4,upper),(east,upper-.9),(east,lower)]
    # West wing facade sometimes extends continuously to the south projection.
    foot=form.choice([2.0391,2.0391,west])
    if shape_attempt == 8:
        west,foot,south,east = -.5,2.0391,-4.95,20.1
        nose=[(east,upper),(east,lower)]
    # In a broad north bay, there is room for a second, distinctly smaller room.
    broad_north = seed % 7 in (0,4)
    north_edge = 1.55 if broad_north else 2.8227
    boundary=[(west,2.9633),(north_edge,2.9633),(north_edge,north_tip),(8.2557,north_tip),(8.2557,5.7204),(10.116,4.5284),
              (15.4507,4.5284),(16.1451,3.8339),(16.1451,upper),*nose,(16.1451,lower),(16.1451,-3.62),
              (10.3127,-3.62),(10.3127,2.435),(8.1508,2.435),(8.1508,south),(foot,south)]
    if foot!=west: boundary.extend([(foot,-2.091),(west,-2.091)])
    shell=Polygon([(x(a),b*depth) for a,b in boundary])
    if shell.area>1.25*original.area and shape_attempt<8:
        return divide(seed,source,shape_attempt+1,partition_attempt)
    # Boundaries are cut in world coordinates. Every piece belongs to the same envelope.
    def mask(x0,y0,x1,y1):
        return box(x(x0), depth*y0, x(x1), depth*y1)
    yhall = rng.uniform(2.54,2.70)
    turn = 10.3127 + max(3.73/scales[1],rng.uniform(3.70,3.89))
    north = rng.uniform(5.75,6.05) if seed%4 else rng.uniform(4.88,5.04)
    if broad_north: north = 4.68
    # In a sparse wing the turn is part of the spawn hall. Reserve enough depth
    # for a central pillar and boss-sized lanes on both sides of it.
    if seed%13==0 or (seed%4==0 and not broad_north):
        north = min(north_tip-2.55/depth,6.8)
    left = shell.intersection(mask(-5,-10,8.1508,yhall).union(mask(-5,-10,north_edge,3.1)))
    right = shell.intersection(mask(10.3127,-10,turn,yhall))
    end = shell.intersection(mask(16.1451,-10,25,12))
    top = shell.intersection(mask(-5,north,8.2557,12))
    hall = shell.difference(unary_union([left,right,end,top]))
    rooms = {"hall":hall, "east_end":end}
    def slice_part(poly, cutter):
        return poly.intersection(cutter),poly.difference(cutter)
    low,upper = slice_part(left,mask(foot,-10,10,min(rng.uniform(-1.18,-.65),yhall-3.42/depth)))
    core,inside = slice_part(upper,mask(-5,-10,rng.uniform(5.16,5.38),5))
    rooms["left_core"] = core
    partition = random.Random(f"inner-walls:{seed}:{shape_attempt}:{partition_attempt}")
    # The west return wraps the core. Where the south bay is generous, take
    # a small corner out of it; otherwise leave the bend as one playable room.
    west_return = inside.union(low)
    pair = None
    if seed%13 and (seed%4 != 0 or broad_north):
        # The old west return already had an inside corner. Cutting a pocket
        # from it made a staircase. Reserve a rectangular bay first.
        x0,y0,x1,y1 = low.bounds
        for extension in (0,.35,.70,1.05,1.40):
            bay = box(x0,y0,x1,y1+extension)
            if not left.buffer(1e-8).covers(bay): continue
            spare = left.difference(bay)
            if not measure("left_core",spare): continue
            candidate = corner_room(bay,"left_inner","left_low",partition)
            if not candidate: continue
            pair = candidate
            rooms["left_inner"],rooms["left_low"] = pair
            if extension==0 and partition.random()<.55 and measure("left_upper",inside):
                rooms["left_upper"] = inside
            else:
                rooms["left_core"] = spare
            break
    if not pair:
        rooms["left_inner"] = west_return

    rooms["north"] = top
    for name,region in (("north",top),("east_end",end)):
        if seed%13 != 0 and (partition.random() < .55 or broad_north):
            extra = corner_room(region,name,name+"_side",partition)
            if extra: rooms[name],rooms[name+"_side"] = extra

    # Some wings have enough frontage for an additional unequal pair.
    # Try an offset cross-wall only when a corner alcove will not fit.
    for name in ("north","east_end","left_core","left_inner"):
        parent=rooms[name]
        if seed%13==0 or name+"_side" in rooms or (partition.random()>=.53 and not broad_north): continue
        xmin,ymin,xmax,ymax=parent.bounds
        short=(2.294 if name=="north" else EAST_LOW[1])+2*HALF_WALL+partition.uniform(.03,.13)
        strips=[box(xmin-1,ymin-1,xmin+short,ymax+1),box(xmax-short,ymin-1,xmax+1,ymax+1),
                box(xmin-1,ymin-1,xmax+1,ymin+short),box(xmin-1,ymax-short,xmax+1,ymax+1)]
        partition.shuffle(strips)
        for strip in strips:
            small=parent.intersection(strip)
            host=parent.difference(strip)
            if name=="left_inner" and "left_low" in rooms and pair:
                if not corner_l(host,rooms["left_low"]) or not unequal_pair(name,host,"left_low",rooms["left_low"]): continue
            if unequal_pair(name,host,name+"_side",small):
                rooms[name],rooms[name+"_side"]=host,small
                break

    # Give the folded eastern wing a short/deep corner room. Its remaining
    # floor wraps the corner and is separated from it by real shared walls.
    pair = corner_room(right,"east_high","east_low",partition)
    if not pair: raise ValueError("east_corner_clearance")
    rooms["east_high"],rooms["east_low"] = pair
    if (rng.random()<.45 or len(rooms)>=10) and seed%13:
        rooms["hall"],rooms["foyer"]=slice_part(hall,mask(7.8,-10,25,12))
    # Independently unfold either wing about the centre of the shared neck section.
    # Both profiles meet on exactly the same interval, so the building stays continuous.
    from shapely.affinity import scale
    pivot=x(10.2)
    mid=(4.5284+2.435)*depth/2
    west_flip=form.random()<.50
    east_flip=form.random()<.50
    def orient(poly):
        pieces=[]
        for half,flip in ((box(-100,-100,pivot,100),west_flip),(box(pivot,-100,100,100),east_flip)):
            part=poly.intersection(half)
            if not part.is_empty:
                pieces.append(scale(part,xfact=1,yfact=-1,origin=(pivot,mid)) if flip else part)
        return set_precision(unary_union(pieces).buffer(0),.000001)
    return orient(shell),{k:orient(p.buffer(0)) for k,p in rooms.items()},rng


def stable_cycles(graph):
    """Record fundamental cycles with fixed graph traversal, origin and direction."""
    ordered = nx.Graph()
    ordered.add_nodes_from(sorted(graph))
    ordered.add_edges_from(sorted(tuple(sorted(edge)) for edge in graph.edges))
    result = []
    for cycle in nx.cycle_basis(ordered):
        start = cycle.index(min(cycle))
        forward = cycle[start:] + cycle[:start]
        result.append(min(forward, forward[:1] + forward[:0:-1]))
    return sorted(result)


def attempt(seed,repair,*,partition=None,closed_pairs=(),opening_shifts=None):
    source=read(ROOT/"data/shell_source_v2.json")
    cfg=read(ROOT/"configs/full_pcg_v2.json")
    approved = read(ROOT/"data/reviewed_shell_partitions.json").get(str(seed))
    variant = approved["partition_attempt"] if approved else repair
    shell,cells,rng=divide(seed,source,partition_attempt=variant)
    reference_net=reference_net_area(source)
    if repair:
        target=reference_net*1.25+10.
        if shell.area>target:
            shell,cells=fit_outer_wings(shell,cells,target)
    if approved:
        # Carry forward the signed-off floor outlines in their original coordinates.
        locked = {k:Polygon(points) for k,points in approved["rooms"].items()}
        existing = unary_union([cells[k] for k in locked])
        if (approved["source_dxf_sha256"] != source["source_dxf_sha256"] or
                existing.symmetric_difference(unary_union(list(locked.values()))).area > 1e-5):
            raise ValueError("reviewed_partition_envelope_changed")
        cells.update(locked)
    if repair:
        rng.seed(f"{seed}:doors:{repair}")
    if partition is not None:
        cells = {name:Polygon(coords) for name, coords in partition}
    opening_shifts = opening_shifts or {}
    if shell.geom_type!="Polygon" or not shell.is_valid or not .75<=shell.area/shell_reference(source).area<=1.25:
        raise ValueError("shell_shape_or_area")
    if any(p.geom_type!="Polygon" or not p.is_valid or p.area<2 for p in cells.values()):
        raise ValueError("invalid_partition")
    if unary_union(list(cells.values())).symmetric_difference(shell).area>1e-5 or abs(sum(p.area for p in cells.values())-shell.area)>1e-5:
        raise ValueError("partition_coverage")
    for host,pocket in (("east_high","east_low"),("left_inner","left_low")):
        if pocket in cells and not corner_l(cells[host],cells[pocket]):
            raise ValueError("invalid_corner_L:"+host)
    sizes={n:measure(n,p) for n,p in cells.items() if n not in ("hall","foyer")}
    if not all(sizes.values()): raise ValueError("small_room:"+",".join(n for n,v in sizes.items() if not v))
    wall_lines = [shell.boundary]
    shared = []
    degree = dict.fromkeys(cells, 0)
    net = nx.Graph()
    net.add_nodes_from(cells)
    for (a, pa), (b, pb) in itertools.combinations(cells.items(), 2):
        contact = pa.boundary.intersection(pb.boundary)
        for line in getattr(contact, "geoms", [contact]):
            if line.geom_type != "LineString" or line.length < .001:
                continue
            if line.length < 1.85:
                wall_lines.append(line)
                continue
            shared.append((a, b, line))
            degree[a] += 1
            degree[b] += 1
            net.add_edge(a, b)
    if not nx.is_connected(net):
        raise ValueError("missing_shared_opening")
    if seed % 3 == 0 and len(nx.cycle_basis(net)) >= 3:
        for a,b,line in rng.sample(shared,len(shared)):
            if sum({x,y}=={a,b} for x,y,_ in shared)>1: continue
            trial=net.copy()
            trial.remove_edge(a,b)
            if not nx.is_connected(trial): continue
            if not nx.cycle_basis(trial.subgraph([n for n in cells if n.startswith("east") or n=="hall"])): continue
            if any(trial.degree[n]==1 and not any(n in (x,y) and span.length>=3.70
                for x,y,span in shared if span is not line) for n in (a,b)): continue
            net=trial
            wall_lines.append(line)
            shared.remove((a,b,line))
            degree[a]-=1
            degree[b]-=1
            break
    if closed_pairs:
        for a,b,line in shared[:]:
            if tuple(sorted((a,b))) in closed_pairs:
                shared.remove((a,b,line))
                wall_lines.append(line)
                degree[a]-=1
                degree[b]-=1
        net = nx.Graph()
        net.add_nodes_from(cells)
        net.add_edges_from((a,b) for a,b,_ in shared)
        if not nx.is_connected(net):
            raise ValueError("mutation_disconnects_rooms")
    portals = []
    secondary = []
    for a, b, line in shared:
        # For a terminal sharing only one wall, separate the two openings by a solid pier.
        split = min(degree[a], degree[b]) == 1 and line.length >= 3.70
        count = 2 if split else 1
        half = rng.uniform(.73, .76)
        centers = ([line.length * .25, line.length * .75] if split else
                   [line.length / 2 + rng.uniform(-.65,.65) * max(0,line.length/2-half-.3)])
        jamb = line.coords[0]
        for index, mid in enumerate(centers):
            shift = opening_shifts.get(tuple(sorted((a,b))), 0)
            if shift and not split:
                mid = min(line.length-half-.09,max(half+.09,mid+shift))
            ends = np.array([line.interpolate(mid-half).coords[0], line.interpolate(mid+half).coords[0]])
            tangent = (ends[1]-ends[0])/(2*half)
            wall_lines.append(LineString([jamb, ends[0]]))
            jamb = ends[1]
            gate = dict(id=f"gate_{len(portals)}", a=a, b=b, segment=ends.tolist(),
                        center=ends.mean(axis=0).tolist(), width=2*half, tangent=tangent.tolist(),
                        normal=[-tangent[1],tangent[0]],kind="normal")
            portals.append(gate)
            if index: secondary.append(gate)
        wall_lines.append(LineString([jamb, line.coords[-1]]))
    # Keep a connected non-window backbone even after all breakable gates have opened.
    # Keep the player's eastern circuit intact in the initial state.
    def graph(excluded):
        result = nx.Graph()
        result.add_nodes_from(cells)
        result.add_edges_from((p["a"],p["b"]) for p in portals if p["kind"] not in excluded)
        return result
    def assign(kind):
        order = rng.sample(secondary,len(secondary)) + rng.sample(portals,len(portals))
        for gate in order:
            if gate["kind"] != "normal": continue
            gate["kind"] = kind
            initial = graph({"break"})
            ordinary = graph({"break", "window"})
            east = initial.subgraph([n for n in cells if n.startswith("east") or n=="hall"])
            if nx.is_connected(ordinary) and nx.cycle_basis(east):
                return True
            gate["kind"] = "normal"
        return False
    for kind in ("window","break"):
        if not assign(kind): raise ValueError("no_safe_"+kind)
    for kind in ("window","break","window"):
        assign(kind)
    available = [p for p in portals if p["kind"]=="normal"]
    for gate in rng.sample(available,min(len(available),rng.randint(2,4))):
        gate["kind"]="through"
    initial=graph({"break"})
    access={}
    for zone in cells:
        gates=[p for p in portals if zone in (p["a"],p["b"])]
        access[zone]=dict(openings=len(gates),neighbors=net.degree[zone],kinds=[p["kind"] for p in gates])
        if len(gates)==1:
            raise ValueError("shared_wall_too_short_for_two_clear_openings:"+zone)
        if not any(p["kind"] in ("normal","through") for p in gates):
            raise ValueError("no_regular_entry:"+zone)
    walls=unary_union(wall_lines).buffer(.09,cap_style="flat",join_style="mitre").intersection(shell)
    blocks=[]
    # Rank the actual floor inside each room, then use the most spacious interior point.
    net_areas={k:v.difference(walls).area for k,v in cells.items()}
    ranked=sorted(cells,key=lambda n:-net_areas[n])
    large=ranked[:math.ceil(len(cells)/4)]
    centers={n:polylabel(cells[n],tolerance=.025) for n in large}
    block_rng=random.Random(f"block-position:{seed}")
    for i,ref in enumerate(source["blocks"]):
        radius=ref["radius_m"]
        need=radius+.09+2*(cfg["player_radius"]+.04)
        choices=[n for n in large if n not in {b["room"] for b in blocks}
                 and centers[n].distance(cells[n].boundary)>need]
        if not choices: raise ValueError("no_large_room_for_block")
        boss_clearance=radius+.09+2*(cfg["boss_radius"]+.03)
        spacious=[n for n in choices if centers[n].distance(cells[n].boundary)>boss_clearance]
        zone=max(spacious or choices,key=lambda n:(i==0 and n=="left_core",
                 (n not in ("hall","foyer")) if repair>=2 else True,net_areas[n]))
        if spacious: need=boss_clearance
        center=centers[zone]
        limit=min(.50,center.distance(cells[zone].boundary)-need)
        angle=block_rng.uniform(0,2*math.pi)
        distance=limit*math.sqrt(block_rng.random())
        offset=[distance*math.cos(angle),distance*math.sin(angle)]
        pos=[center.x+offset[0],center.y+offset[1]]
        blocks.append(dict(id=zone+"_block",room=zone,radius=radius,position=pos,
                           center_anchor=list(center.coords[0]),offset_m=offset,
                           offset_limit_m=limit,room_area_rank=ranked.index(zone)+1))
    solids=unary_union([walls,*[Point(o["position"]).buffer(o["radius"],quad_segs=12) for o in blocks]])
    net_area=shell.difference(solids).area
    if not .75<=net_area/reference_net<=1.25: raise ValueError("net_playable_area_ratio")
    free=shell.difference(solids.buffer(cfg["boss_radius"]+.025))
    seals=unary_union([LineString(p["segment"]).buffer(.10,cap_style="square") for p in portals])
    free=free.difference(seals.buffer(cfg["boss_radius"]+.04))
    rows=[]
    for name,p in cells.items():
        regions=p.intersection(free)
        large=max((v for v in getattr(regions,"geoms",[regions]) if v.geom_type=="Polygon"),key=lambda v:v.area,default=None)
        if not large:raise ValueError("room_without_clearance:"+name)
        center=polylabel(large,tolerance=.03)
        rows.append(dict(id=name,role=name,area=p.area,polygon=list(p.exterior.coords),center=list(center.coords[0])))
    layout=dict(seed=seed,door_attempt=repair,schema_version=5,room_access=access,rooms=rows,floor=mapping(shell),walls=mapping(walls),base_obstacles=mapping(solids),
                area=shell.area,bounds=list(shell.bounds),portals=portals,obstacles=blocks,source_dxf_sha256=source["source_dxf_sha256"],
                topology=dict(nodes=list(net),edges=list(net.edges),cycles=len(nx.cycle_basis(net))))
    cutoff=sorted((r["area"] for r in rows),reverse=True)[math.ceil(len(rows)/4)-1]
    eligible=[r for r in rows if r["id"] in ("hall","foyer") and net.degree[r["id"]]>=3 and initial.degree[r["id"]]>=2 and r["area"]>=cutoff]
    core=max(eligible,key=lambda r:(r["id"]=="hall", r["area"]),default=None)
    if not core or core["area"]<sorted((r["area"] for r in rows),reverse=True)[math.ceil(len(rows)/4)-1]: raise ValueError("opening_core")
    # Sample opening positions only in the main traversable component, including a rounding margin.
    from combat_pcg.layouts import _candidates
    combat=default_combat()
    points=[]
    for role in ("player","boss"):
        region=shell.difference(solids.buffer(cfg[role+"_radius"]+.05))
        main=max(getattr(region,"geoms",[region]),key=lambda p:p.area)
        points.append(_candidates(cells[core["id"]],main,cfg[role+"_radius"]))
    pairs=((a,b) for a in points[0] for b in points[1] if math.dist(a,b)<=4.6)
    pair=max(pairs,key=lambda ab:math.dist(*ab),default=None)
    if pair is None or math.dist(*pair)<2: raise ValueError("opening_clearance")
    for field,a,b in [("spawn",*pair),("boss",*pair[::-1])]:
        layout[field]=dict(room=core["id"],position=a,heading_rad=math.atan2(b[1]-a[1],b[0]-a[0]))
    layout["opening_reaction_margin_s"]=(math.dist(*pair)-combat["boss"]["grab_range_m"])/combat["boss"]["speed_mps"]+combat["boss"]["attack_warning_s"]-combat["player"]["reaction_s"]
    layout["exit"]=dict(room="east_end",position=next(r["center"] for r in rows if r["id"]=="east_end"),victory_condition=False)
    targets=[r for r in rows if r!=core]
    rng.shuffle(targets)
    layout["supplies"]=[dict(id=f"supply_{i}",room_id=r["id"],position=r["center"]) for i,r in enumerate(targets[:6])]
    # Physical route around the west pillar, sampled at capsule clearance.
    o=blocks[0]
    clearance=cfg["player_radius"]+.025
    ring=Point(o["position"]).buffer(o["radius"]+clearance+.08,quad_segs=24).exterior
    if not cells[o["room"]].covers(ring) or not shell.difference(solids.buffer(clearance)).covers(ring): raise ValueError("west_pillar_loop")
    # Transverse wall-to-wall sections across the horizontal straight run.
    hall=cells["hall"].difference(walls)

    # The full straight run begins at the left wing's eastern facade.
    start=max(p.bounds[2] for n,p in cells.items() if n.startswith("left_"))
    finish=cells["east_high"].bounds[2]
    widths=[]
    heights=[]
    for x in np.linspace(start+.18,finish-.18,15):
        section=hall.intersection(LineString([(x,-30),(x,30)]))
        lines=[v for v in getattr(section,"geoms",[section]) if v.geom_type=="LineString"]
        if not lines:raise ValueError("hall_section_missing")
        span=max(lines,key=lambda v:v.length)
        widths.append(span.length)
        heights.append(span.centroid.y)
    probe_y=float(np.median(heights))
    run=hall.intersection(LineString([(start,probe_y),(shell.bounds[2],probe_y)]))
    aspect=max((v.length for v in getattr(run,"geoms",[run])),default=0)/float(np.median(widths))
    if aspect<3: raise ValueError("short_horizontal_run")
    layout["metrics"]=dict(room_sizes=sizes,shell_area=shell.area,net_area=net_area,reference_net_area=reference_net,fill=shell.area/shell.envelope.area,
        aspect=(shell.bounds[2]-shell.bounds[0])/(shell.bounds[3]-shell.bounds[1]),hall_aspect=aspect,
        left_net=sum(cells[n].difference(solids).area for n in cells if n.startswith(("left","north","south"))),
        right_net=sum(cells[n].difference(solids).area for n in cells if n.startswith("east")),
        left_loop=list(ring.coords),east_cycles=stable_cycles(initial.subgraph([n for n in cells if n.startswith("east") or n=="hall"])))
    qa=validate(layout,cfg)
    issues=set(qa["issues"])-{"escape_too_short","escape_detour_excessive","exit_endpoint_disconnected"}
    if issues:raise ValueError(",".join(sorted(issues)))
    layout["validation"]=dict(states=qa["states"],smash_order=qa["boss_opening_schedule"])
    layout["layout_hash"]=digest(layout)
    return layout


def certify_navigation(result, packet):
    # Verify coverage and safe crossing for each role on the exported links.
    for role,actor in (("boss","boss"),("player","spawn")):
        nav=unary_union([Polygon(t) for t in packet["navigation"][role]])
        pieces=list(getattr(nav,"geoms",[nav]))

        def component(pos):
            return min(range(len(pieces)),key=lambda i:pieces[i].distance(Point(pos)))

        connections=nx.Graph()
        connections.add_nodes_from(range(len(pieces)))
        for link in packet["links"]:
            if link["role"]==role and not (role=="boss" and link["kind"]=="window"):
                connections.add_edge(*map(component,link["points"]))
        accessible=nx.node_connected_component(connections,component(result[actor]["position"]))
        if any(component(r["center"]) not in accessible for r in result["rooms"]):
            raise ValueError("disconnected_navigation_links:"+role)
    from full_pcg.validation import barrier
    for link in packet["links"]:
        if link["kind"] not in ("through","window") or link["role"]!="player":
            continue
        p=next(p for p in result["portals"] if p["id"]==link["portal"])
        if LineString(link["points"]).intersects(barrier(p).buffer(.375)):
            raise ValueError("off_center_squeeze:"+p["id"])


def build(seed):
    failures=[]
    for repair in range(9):
        try:
            result=attempt(seed,repair)
            packet=package(result,read(ROOT/"configs/full_pcg_v2.json"))
            certify_navigation(result, packet)
            result["repair_reasons"]=failures
            result.pop("layout_hash")
            result["layout_hash"]=digest(result)
            return result
        except ValueError as exc:
            failures.append(str(exc))
            # A later bounded attempt may use a different shell and inner partition.
    raise ValueError(" | ".join(failures))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("seed",type=int)
    parser.add_argument("output",type=Path)
    args=parser.parse_args()
    try:
        layout=build(args.seed)
        packet=package(layout,read(ROOT/"configs/full_pcg_v2.json"))
        packet["zones"]={r["id"]:triangles(Polygon(r["polygon"])) for r in layout["rooms"]}
        result=dict(ok=True,seed=args.seed,**packet)
    except ValueError as exc:
        result=dict(ok=False,seed=args.seed,reason=str(exc))
    write(args.output,result)

if __name__=="__main__":
    main()

