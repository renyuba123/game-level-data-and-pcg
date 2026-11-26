"""Independent opportunities and observed alternatives on the player clearance mesh."""
from itertools import pairwise
import math
import random

import networkx as nx
from shapely.geometry import Point, LineString, Polygon
from shapely.ops import unary_union
from shapely.prepared import prep


def erase_loops(seq):
    stack=[]; index={}
    for key in seq:
        if key in index:
            while stack[-1]!=key:
                del index[stack.pop()]
        else:
            index[key]=len(stack)
            stack.append(key)
    return tuple(stack)


def alternative_use(packet, episodes, phase, config):
    grid=config['score_sampling']['grid_m']
    mesh=unary_union([Polygon(t) for t in packet['navigation']['player']])
    walk=prep(mesh)
    x0,z0,x1,z1=mesh.bounds
    centers={(x,z):((x+.5)*grid,(z+.5)*grid)
             for x in range(math.floor(x0/grid),math.ceil(x1/grid))
             for z in range(math.floor(z0/grid),math.ceil(z1/grid))
             if walk.covers(Point((x+.5)*grid,(z+.5)*grid))}
    fixed=nx.Graph()
    fixed.add_nodes_from(centers)
    for (x,z),pt in centers.items():
        for neighbor in ((x+1,z),(x,z+1)):
            if neighbor in centers and walk.covers(LineString([pt,centers[neighbor]])):
                fixed.add_edge((x,z),neighbor)
    links=[]
    for gate in packet['links']:
        if gate['role']!='player':continue
        near=[]
        for end in gate['points']:
            legal=[(math.dist(end,p),key) for key,p in centers.items()
                   if math.dist(end,p)<=grid*2 and walk.covers(LineString([end,p]))]
            if legal:near.append(min(legal)[1])
        if len(near)==2:links.append((gate['portal'],gate['kind'],*near))
    nodes=sorted(centers)
    rng=random.Random(config['sampling']['scenario_seeds'][0])
    possible=set()
    while len(possible)<min(config['score_sampling']['maximum_alternative_endpoint_pairs'],len(nodes)*(len(nodes)-1)//2):
        possible.add(tuple(sorted(rng.sample(nodes,2))))
    signatures={pair:set() for pair in possible}
    eligible=set()
    known_states={}
    for rec in episodes:
        frames=[f for f in rec['frames'] if f['phase']==phase]
        from itertools import groupby
        for opened,segment in groupby(frames,key=lambda f:tuple(sorted(f['opened']))):
            if opened not in known_states:
                graph=fixed.copy()
                graph.add_edges_from((a,b) for id,kind,a,b in links if kind!='break' or id in opened)
                blocks=[c for c in nx.biconnected_components(graph) if len(c)>2]
                known_states[opened]=[pair for pair in possible if any(pair[0] in c and pair[1] in c for c in blocks)]
            eligible.update(known_states[opened])
            track=[(math.floor(f['p'][0]/grid),math.floor(f['p'][1]/grid)) for f in segment]
            for pair in known_states[opened]:
                start=None; used=[]
                for location in track:
                    if start is not None:used.append(location)
                    if location not in pair:continue
                    if start is not None and location!=start:
                        path=erase_loops(used)
                        signatures[pair].add(path if start==pair[0] else path[::-1])
                    start=location;used=[location]
    return sum(len(signatures[p])>=2 for p in eligible),len(eligible)
