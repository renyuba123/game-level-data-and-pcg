"""Cheap physical validation. Runs before Depthmap, never substitutes graph reachability."""
import sys,math
import numpy as np
from shapely.geometry import shape,Point,LineString,Polygon
from shapely.ops import unary_union
from .common import ROOT
from .geometry import parts
sys.path.insert(0,str(ROOT/'evolution'))
from simulation import Navigation
from .navigation import route

def barrier(portal):
    a,b=np.array(portal['segment']);c=np.array(portal['center']);t=np.array(portal['tangent'])
    lines=[LineString([a,b])] if portal['kind']=='break' else [LineString([a,c-t*.45]),LineString([c+t*.45,b])]
    return unary_union(lines).buffer(.09,cap_style='flat')

def validate(layout,config):
    floor=shape(layout['floor']);base=shape(layout['base_obstacles']);gates={p['id']:barrier(p) for p in layout['portals'] if p['kind']!='normal'}
    issues=[];states={};centers=[Point(r['center']) for r in layout['rooms']]
    for state,opened in [('initial',set()),('all_open',set(gates))]:
        obstacle=unary_union([base,*[v for k,v in gates.items() if k not in opened]])
        for role in ['player','boss']:
            free=floor.difference(obstacle.buffer(config[role+'_radius']+.025))
            origin=Point(layout['spawn' if role=='player' else 'boss']['position'])
            region=next((p for p in parts(free) if p.covers(origin)),None)
            reached=[r['id'] for r,p in zip(layout['rooms'],centers) if region is not None and region.covers(p)]
            states[state+'_'+role]={'rooms_reached':reached,'total':len(centers)}
            if (role=='player' or state=='all_open') and len(reached)!=len(centers):issues.append(state+'_'+role+'_disconnected')
    opened=set();schedule=[]
    for _ in range(len(gates)):
        free=floor.difference(unary_union([base,*[v for k,v in gates.items() if k not in opened]]).buffer(config['boss_radius']+.025))
        origin=Point(layout['boss']['position']);region=next((p for p in parts(free) if p.covers(origin)),None)
        options=[p for p in layout['portals'] if p['id'] in gates and p['id'] not in opened and region is not None and region.distance(gates[p['id']])<=config['boss_radius']+.04]
        if not options:break
        chosen=sorted(options,key=lambda p:p['id'])[0];opened.add(chosen['id']);schedule.append(chosen['id'])
    if opened!=set(gates):issues.append('boss_cannot_reach_smash_face')
    obstacle=unary_union([base,*gates.values()]);anchors=[r['center'] for r in layout['rooms']]
    for p in layout['portals']:
        anchors.extend((np.array(p['center'])+np.array(p['normal'])*v).tolist() for v in np.arange(-1.3,1.31,.15))
    nav=Navigation(floor,obstacle,config['player_radius'],cell=.3,anchors=anchors)
    start=layout['spawn']['position'];end=layout['exit']['position'];path=route(nav,start,end)
    # Legacy route only validates the start connector. Explicitly validate its end too.
    if not path:issues.append('exit_endpoint_disconnected');length=None;seconds=None;detour=None
    else:
        path=[np.array(start),*path,np.array(end)];trace=LineString(path);length=trace.length
        actions=sum(trace.intersects(gates[p['id']].buffer(.1)) for p in layout['portals'] if p['kind']=='through')
        seconds=length/5+.65*actions;detour=length/max(math.dist(start,end),.01)
        if seconds<config['minimum_escape_seconds']:issues.append('escape_too_short')
        if detour>config['max_detour']:issues.append('escape_detour_excessive')
    return {'ok':not issues,'issues':issues,'states':states,'boss_opening_schedule':schedule,'escape_length':length,'escape_seconds':seconds,'detour':detour,
        'method':'role-sized polygon connectivity; clearance-grid escape path; constructed reachable-face opening schedule'}
