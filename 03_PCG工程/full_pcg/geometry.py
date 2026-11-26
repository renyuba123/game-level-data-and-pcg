"""Single source of polygon geometry, portal barriers and navigation surfaces."""
import math,heapq
import numpy as np
import networkx as nx
from shapely.geometry import Polygon,Point,LineString,box,mapping,shape
from shapely.ops import unary_union,polylabel
from shapely.affinity import rotate,translate,scale
from shapely import constrained_delaunay_triangles
from .common import ROOT,read,digest

def baseline_area():
    source=read(ROOT/'data/source_profile.json')
    return unary_union([Polygon(r['polygon_m']) for r in source['convex_rooms']]).area

def polygon(room):
    w,h=room['width']/2,room['height']/2;k=room['shape'];cut=.26
    points=[(-w,-h),(w,-h),(w,h),(-w,h)]
    if k=='chamfer':points=[(-w+cut,-h),(w-cut,-h),(w,-h+cut),(w,h-cut),(w-cut,h),(-w+cut,h),(-w,h-cut),(-w,-h+cut)]
    elif k=='trapezoid':points=[(-w*.8,-h),(w*.8,-h),(w,h),(-w,h)]
    elif k=='L':points=[(-w,-h),(w,-h),(w,h*.45),(w*.45,h*.45),(w*.45,h),(-w,h)]
    elif k=='notch':points=[(-w,-h),(w,-h),(w,h),(w*.55,h),(w*.55,h*.65),(w*.2,h*.65),(w*.2,h),(-w,h)]
    p=rotate(Polygon(points),room['rotation'],origin=(0,0))
    return translate(p,*room['position'])

def route(a,b,blocked,width):
    """Deterministic A* with heading costs; straight path is the zero-turn optimum."""
    line=LineString([a,b])
    if not line.buffer(width/2+.04,cap_style='flat').intersects(blocked):return [a,b]
    cell=.25;origin=np.minimum(a,b)-4;target=tuple(np.rint((np.array(b)-origin)/cell).astype(int));start=tuple(np.rint((np.array(a)-origin)/cell).astype(int))
    def world(p):return tuple(origin+np.array(p)*cell)
    heap=[(0,0,start,-1)];dist={(start,-1):0};parent={};end=None
    directions=[(1,0),(-1,0),(0,1),(0,-1)]
    while heap and len(dist)<8000:
        _,cost,p,heading=heapq.heappop(heap)
        if p==target:end=(p,heading);break
        for h,(dx,dy) in enumerate(directions):
            q=(p[0]+dx,p[1]+dy);seg=LineString([world(p),world(q)])
            if seg.buffer(width/2+.04).intersects(blocked):continue
            v=cost+cell+(.12 if heading not in (-1,h) else 0);key=(q,h)
            if v>=dist.get(key,1e30):continue
            dist[key]=v;parent[key]=(p,heading);heapq.heappush(heap,(v+math.dist(q,target)*cell,v,q,h))
    if end is None:raise ValueError('corridor_unroutable')
    points=[]
    while end in parent:points.append(world(end[0]));end=parent[end]
    return [a,*reversed(points),b]

def parts(geom):return list(geom.geoms) if hasattr(geom,'geoms') else [geom]
def serialize(geom):return mapping(geom)

def generate(genome,config):
    issues=[];repairs=[];polys={r['id']:polygon(r) for r in genome['rooms']};g=nx.Graph();g.add_nodes_from(polys)
    for e in genome['edges']:g.add_edge(e['a'],e['b'])
    corridors=[];portals=[];junctions=[];width=config['corridor_width']
    try:
        for e in genome['edges']:
            positions={r['id']:r['position'] for r in genome['rooms']}
            a=Point(positions[e['a']]);b=Point(positions[e['b']])
            blocked=unary_union([p for rid,p in polys.items() if rid not in [e['a'],e['b']]])
            points=route(a.coords[0],b.coords[0],blocked,width)
            line=LineString(points);c=line.buffer(width/2,cap_style='flat',join_style='mitre')
            for prev in corridors:
                shared=set([e['a'],e['b']])&set(prev['endpoints'])
                allowed=unary_union([polys[r] for r in shared])
                intersection=c.intersection(prev['shape']).difference(allowed)
                if intersection.area>.005:
                    if not shared:raise ValueError('undeclared_corridor_intersection')
                    # A flared entry belongs to the common room, not a new room-to-room shortcut.
                    junctions.append({'id':f'junction_{len(junctions):03d}','room':sorted(shared)[0],
                        'corridors':[e['id'],prev['id']],'shape':intersection})
            corridors.append({'id':e['id'],'shape':c,'endpoints':[e['a'],e['b']],'centerline':points})
            outside=line.difference(unary_union([polys[e['a']],polys[e['b']]]))
            pieces=[p for p in parts(outside) if p.geom_type=='LineString' and p.length>.15]
            if not pieces:raise ValueError('no_external_portal_span')
            segment=max(pieces,key=lambda p:p.length);center=segment.interpolate(.5,normalized=True);v=np.array(segment.coords[-1])-np.array(segment.coords[0]);v=v/np.linalg.norm(v);t=np.array([-v[1],v[0]])
            portals.append({**e,'center':list(center.coords[0]),'tangent':t.tolist(),'normal':v.tolist(),'width':width,'segment':[(np.array(center.coords[0])+sgn*t*width/2).tolist() for sgn in [-1,1]]})
        floor=unary_union([*polys.values(),*[c['shape'] for c in corridors]])
        if floor.geom_type!='Polygon':raise ValueError('disconnected_floor')
        factor=math.sqrt(baseline_area()*genome['target_area_ratio']/floor.area)
        if width*factor<1.36:raise ValueError('scaled_corridor_too_narrow')
        polys={k:scale(v,factor,factor,origin=(0,0)) for k,v in polys.items()};floor=scale(floor,factor,factor,origin=(0,0))
        for c in corridors:
            c['shape']=scale(c['shape'],factor,factor,origin=(0,0));c['centerline']=(np.array(c['centerline'])*factor).tolist()
        for p in portals:
            p['center']=(np.array(p['center'])*factor).tolist();p['segment']=(np.array(p['segment'])*factor).tolist();p['width']*=factor
        junctions=[{**j,'shape':serialize(scale(j['shape'],factor,factor,origin=(0,0)))} for j in junctions]
        walls=floor.boundary.buffer(config['wall_thickness']/2,cap_style='flat',join_style='mitre')
        obstacles=[]
        safe_centers=[polylabel(poly,tolerance=.01) for poly in polys.values()]
        for item in genome['obstacles']:
            room_poly=polys[item['room']];center=np.array(polylabel(room_poly,tolerance=.01).coords[0]);offset=np.array(item.get('offset',[.7,.7]));p=center+offset
            candidates=[p]
            for angle in range(45,360,45):
                rad=math.radians(angle);candidates.append(center+np.array([[math.cos(rad),-math.sin(rad)],[math.sin(rad),math.cos(rad)]])@offset)
            selected=None
            for q in candidates:
                obstacle=Point(q).buffer(item['radius'])
                if not room_poly.buffer(-.11).covers(obstacle):continue
                trial=unary_union([walls,obstacle,*[Point(o['position']).buffer(o['radius'],quad_segs=12) for o in obstacles]])
                safe=floor.difference(trial.buffer(config['boss_radius']+.025))
                if any(all(region.covers(c) for c in safe_centers) for region in parts(safe)):
                    selected=q;break
            if selected is None:raise ValueError('obstacle_cannot_fit_room')
            if not np.allclose(selected,p):repairs.append({'op':'rotate_obstacle_offset','id':item['id'],'before':p.tolist(),'after':selected.tolist()})
            p=selected
            obstacles.append({'id':item['id'],'room':item['room'],'position':p.tolist(),'radius':item['radius']})
        base=unary_union([walls,*[Point(o['position']).buffer(o['radius'],quad_segs=12) for o in obstacles]])
        rooms=[{**r,'polygon':list(polys[r['id']].exterior.coords)[:-1],'center':list(polylabel(polys[r['id']],tolerance=.01).coords[0]),'area':polys[r['id']].area} for r in genome['rooms']]
        for i,a in enumerate(rooms):
            for b in rooms[i+1:]:
                if polys[a['id']].intersection(polys[b['id']]).area>.001:issues.append('room_overlap')
        coords={r['id']:r['center'] for r in rooms}
        for edge in portals:g[edge['a']][edge['b']]['weight']=LineString(next(c['centerline'] for c in corridors if c['id']==edge['id'])).length
        initial=g.copy();initial.remove_edges_from((p['a'],p['b']) for p in portals if p['kind']=='break')
        if not nx.is_connected(initial):issues.append('initial_graph_disconnected')
        if not nx.cycle_basis(initial):issues.append('no_initial_loop')
        if not any(p['kind']=='break' for p in portals):issues.append('no_break_shortcut')
        layout={'schema_version':3,'seed':genome['seed'],'genome_hash':digest(genome),'rooms':rooms,'corridors':[{**c,'shape':serialize(c['shape'])} for c in corridors],
            'floor':serialize(floor),'walls':serialize(walls),'base_obstacles':serialize(base),'portals':portals,'obstacles':obstacles,'junctions':junctions,
            'spawn':{'room':genome['spawn'],'position':coords[genome['spawn']]},'boss':{'room':genome['boss'],'position':coords[genome['boss']]},'exit':{'room':genome['exit'],'position':coords[genome['exit']]},
            'area':floor.area,'bounds':floor.bounds,'repairs':repairs,'topology':{'nodes':list(g.nodes),'edges':list(g.edges),'cycles':len(nx.cycle_basis(g))}}
        # Exact role-sized free polygons are also the Godot nav source.
        layout['navigation']={}
        for role,radius in [('player',config['player_radius']),('boss',config['boss_radius'])]:
            free=floor.difference(base.buffer(radius+.025));layout['navigation'][role]=[]
            for region in parts(free):
                if region.geom_type!='Polygon':continue
                for tri in constrained_delaunay_triangles(region).geoms:layout['navigation'][role].append(list(tri.exterior.coords)[:3])
            for rid,point in coords.items():
                if not free.covers(Point(point)):issues.append(role+'_room_anchor_blocked:'+rid)
        layout['layout_hash']=digest(layout)
        return layout,{'ok':not issues,'issues':sorted(set(issues)),'repairs':repairs}
    except ValueError as e:return {'schema_version':3,'genome_hash':digest(genome),'rooms':[{'id':k,'polygon':list(p.exterior.coords)[:-1]} for k,p in polys.items()]},{'ok':False,'issues':[str(e)],'repairs':repairs}
