"""Planar anchor graph sampling. Anchors are generated, not a fixed room template."""
import random,math
import networkx as nx

def graph(genome):
    g=nx.Graph();g.add_nodes_from(r['id'] for r in genome['rooms'])
    g.add_edges_from((e['a'],e['b'],{'kind':e['kind']}) for e in genome['edges']);return g

def sample(seed,config):
    rng=random.Random(seed);n=rng.randint(*config['room_count'])
    # Grow a compact planar anchor complex; no fixed number, coordinates or adjacency.
    cells={(0,0),(1,0),(0,1),(1,1)}
    while len(cells)<n:
        options=sorted({(x+dx,y+dy) for x,y in cells for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]}-cells)
        weights=[1+sum((x+dx,y+dy) in cells for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)])**2 for x,y in options]
        cells.add(rng.choices(options,weights)[0])
    cells=sorted(cells);ids={c:f'room_{i:03d}' for i,c in enumerate(cells)}
    rooms=[]
    for i,(x,y) in enumerate(cells):
        rooms.append({'id':ids[x,y],'anchor':[x,y],'position':[x*4.7+rng.uniform(-.12,.12),y*4.7+rng.uniform(-.12,.12)],
            'rotation':rng.randrange(8)*45,'width':rng.uniform(2.65,3.05),'height':rng.uniform(2.65,3.05),
            'shape':rng.choice(['rectangle','chamfer','trapezoid','L','notch']),'role':'side'})
    edges=[]
    for x,y in cells:
        for dx,dy in [(1,0),(0,1)]:
            if (x+dx,y+dy) in ids:edges.append({'id':f'edge_{len(edges):03d}','a':ids[x,y],'b':ids[x+dx,y+dy],'kind':'normal'})
    g=nx.Graph();g.add_nodes_from(ids.values());g.add_edges_from((e['a'],e['b']) for e in edges)
    # Optional edge deletion produces distinct graphs even with identical anchors.
    target_cycles=rng.randint(2,max(2,len(nx.cycle_basis(g))))
    for e in rng.sample(edges,len(edges)):
        if len(nx.cycle_basis(g))<=target_cycles:break
        if rng.random()<.28:
            g.remove_edge(e['a'],e['b'])
            if not nx.is_connected(g):g.add_edge(e['a'],e['b'])
    edges=[e for e in edges if g.has_edge(e['a'],e['b'])]
    breaks=[]
    for e in rng.sample(edges,len(edges)):
        if len(breaks)>=min(config['break_count'][1],max(1,len(nx.cycle_basis(g))-1)):break
        g.remove_edge(e['a'],e['b'])
        if nx.is_connected(g) and nx.cycle_basis(g):e['kind']='break';breaks.append(e['id'])
        else:g.add_edge(e['a'],e['b'])
    normal=[e for e in edges if e['kind']=='normal'];rng.shuffle(normal)
    for e in normal[:rng.randint(config['through_count'][0],min(config['through_count'][1],len(normal)))]:e['kind']='through'
    lengths=dict(nx.all_pairs_shortest_path_length(g));a,b=max(((a,b) for a in lengths for b in lengths[a]),key=lambda ab:lengths[ab[0]][ab[1]])
    boss=max((r['id'] for r in rooms if r['id'] not in (a,b)),key=lambda r:lengths[a][r])
    hub=max(rooms,key=lambda r:g.degree[r['id']]);hub['role']='hub'
    cover=next(r for r in rooms if r['id']!=hub['id']);cover['role']='cover';cover['shape']='L'
    obstacle_rooms=sorted(rooms,key=lambda r:r['width']*r['height'],reverse=True)[:2]
    for r in obstacle_rooms:r.update(width=4.0,height=3.6,shape='chamfer',rotation=(r['rotation']//90)*90)
    obstacles=[{'id':f'block_{i:03d}','room':r['id'],'radius':.3,'offset':[.7,.7]} for i,r in enumerate(obstacle_rooms)]
    return {'schema_version':3,'seed':seed,'rooms':rooms,'edges':edges,'spawn':a,'boss':boss,'exit':b,'obstacles':obstacles,
        'target_area_ratio':rng.uniform(.95,1.05),'operations':[{'op':'sample_planar_anchor_graph','seed':seed}]}

def classify(genomes):
    reps=[];result=[]
    for genome in genomes:
        g=graph(genome)
        match=next((i for i,r in enumerate(reps) if nx.is_isomorphic(g,r)),None)
        if match is None:match=len(reps);reps.append(g)
        result.append(match)
    return result
