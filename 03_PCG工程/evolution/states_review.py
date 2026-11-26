import numpy as np
from collections import deque
from shapely.geometry import Point,Polygon,LineString
from shapely.ops import unary_union
from common import ROOT,WORK,read_json,write_json
from metrics import candidate_geometry
from simulation import Navigation,door_anchors

def topology(layout,opened,role):
    edges=[e for e in layout['edges'] if e['kind']=='normal' or e['id'] in opened or (role=='player' and e['kind']=='through')]
    graph={i:[] for i in range(len(layout['rooms']))}
    for e in edges:
        graph[e['a']].append((e['b'],e['id'])); graph[e['b']].append((e['a'],e['id']))
    start=layout['spawn_room'] if role=='player' else layout['boss_room']
    def path(omit=None):
        queue=deque([(start,[],[start])]); seen={start}
        while queue:
            node,steps,nodes=queue.popleft()
            if node==layout['exit_room']:return steps,nodes
            for other,key in graph[node]:
                if other not in seen and key!=omit:
                    seen.add(other); queue.append((other,steps+[key],nodes+[other]))
        return [],[]
    unseen=set(graph); components=0
    while unseen:
        components+=1; queue=[unseen.pop()]
        while queue:
            for other,_ in graph[queue.pop()]:
                if other in unseen:unseen.remove(other);queue.append(other)
    route,nodes=path()
    return {'room_cycle_rank':len(edges)-len(graph)+components,'connected_components':components,
        'dead_end_room_ids':[layout['rooms'][n]['source_id'] for n,adj in graph.items() if len(adj)==1],
        'shortest_room_hop_route':[layout['rooms'][n]['source_id'] for n in nodes],
        'route_edges_with_alternative_after_removal':sum(bool(path(key)[1]) for key in route),
        'route_edge_count':len(route),'note':'Room topology only; not Depthmap Convex Choice or metric path length'}

def main():
    results=[]; seen=set()
    for label in ('balanced','exploration','pressure'):
        candidate=read_json(ROOT/f'data/evolution/{label}.json')
        key=candidate['evaluation'].get('fine_review',candidate['evaluation'])['key']
        if key in seen:continue
        seen.add(key); layout=read_json(WORK/'cache'/key/'layout.json')
        base,floor=candidate_geometry(layout,'all_open'); anchors=door_anchors(layout)
        barriers={}
        for e in layout['edges']:
            if e['kind']=='normal':continue
            a,b=np.array(e['shared_segment']); t=(b-a)/np.linalg.norm(b-a); c=np.array(e['door_anchor']); w=e['door_width_m']
            lines=[LineString([c-t*w/2,c+t*w/2])] if e['kind']=='break' else [LineString([c-t*w/2,c-t*.45]),LineString([c+t*.45,c+t*w/2])]
            barriers[e['id']]=unary_union(lines).buffer(.09,cap_style='flat')
        schedule=sorted(barriers); stages=[]
        for count in range(len(schedule)+1):
            opened=set(schedule[:count]); obstacles=unary_union([base,*[g for edge,g in barriers.items() if edge not in opened]])
            stage={'opened':sorted(opened),'newly_opened':schedule[count-1] if count else None,'roles':{}}
            for role,radius in [('player',.35),('boss',.58)]:
                nav=Navigation(floor,obstacles,radius,anchors=anchors)
                points=[]
                for room in layout['rooms']:
                    free=Polygon(room['polygon']).intersection(nav.free)
                    if free.is_empty:raise RuntimeError('Room without clearance')
                    p=free.representative_point(); points.append([p.x,p.y])
                origin=points[layout['spawn_room'] if role=='player' else layout['boss_room']]
                reached=[layout['rooms'][i]['source_id'] for i,p in enumerate(points) if nav.route(origin,p)]
                stage['roles'][role]={'clearance_reachable_rooms':reached,**topology(layout,opened,role)}
            stages.append(stage)
        results.append({'label':label,'candidate':key,'schedule':schedule,'stages':stages})
    write_json(WORK/'runs/search_v1/destruction_states.json',{'schedule_type':'Constructed deterministic edge-ID order for state testing, not an observed Boss timeline',
        'player_assumption':'Explicit squeeze actions are available; interaction time excluded from reachability', 'results':results})
    print('Destruction states reviewed',len(results),flush=True)

if __name__=='__main__':main()
