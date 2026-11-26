"""Explicit new-protocol reference endpoints; never modifies historical baseline files."""
import sys
import numpy as np
from shapely.geometry import Polygon,Point,LineString
from shapely.ops import unary_union,polylabel,polygonize
from shapely import set_precision
from .common import ROOT,read,write,digest
from .geometry import parts
sys.path.insert(0,str(ROOT/'evolution'))
from simulation import Navigation
from .navigation import route
def calibrate():
    source=read(ROOT/'data/source_profile.json');rooms=source['convex_rooms'];floor=unary_union([Polygon(r['polygon_m']) for r in rooms])
    reference_partition_area=floor.area
    rings=list(polygonize(unary_union([set_precision(LineString([w['start_m'],w['end_m']]),.0001) for w in source['wall_segments']])))
    shells=sorted([Polygon(p.exterior) for p in rings],key=lambda p:p.area,reverse=True)
    if shells and shells[0].intersection(floor).area/floor.area>.98 and shells[0].area<1.4*floor.area:
        floor=shells[0]
    else:raise RuntimeError('Cannot reconstruct verified outer DXF floor shell')
    obstacles=unary_union([*[LineString([w['start_m'],w['end_m']]).buffer(.09,cap_style='flat') for w in source['wall_segments']],
        *[Point(b['center_m']).buffer(b['radius_m'],quad_segs=12) for b in source['blocks']]])
    free=floor.difference(obstacles.buffer(.375));centers={}
    for r in rooms:
        available=Polygon(r['polygon_m']).intersection(free);poly=max((p for p in parts(available) if p.geom_type=='Polygon'),key=lambda p:p.area)
        centers[r['room_id']]=list(polylabel(poly,tolerance=.01).coords[0])
    anchors=list(centers.values())
    for c in source['connections']:
        ends=np.array([c['start_m'],c['end_m']]);center=ends.mean(axis=0);t=ends[1]-ends[0];t=t/np.linalg.norm(t);normal=np.array([-t[1],t[0]])
        anchors.extend((center+normal*v).tolist() for v in np.arange(-1.5,1.51,.1))
    nav=Navigation(floor,obstacles,.35,cell=.3,anchors=anchors)
    # Explicit interaction links across source narrow gaps; never free teleport links.
    links=[];matrix=nav.graph.tolil()
    for c in source['connections']:
        if c['kind']!='through':continue
        ends=np.array([c['start_m'],c['end_m']]);center=ends.mean(axis=0);t=ends[1]-ends[0];t=t/np.linalg.norm(t);normal=np.array([-t[1],t[0]])
        sides=[]
        for sign in [-1,1]:
            choices=[]
            for distance in [.5,.75,1.,1.25]:
                p=center+normal*sign*distance;i=nav.nearest(p);actual=nav.points[i]
                if np.dot(actual-center,normal)*sign>.3 and np.linalg.norm(actual-p)<.35:choices.append(i)
            sides.append(choices)
        if not all(sides):continue
        i,j=sides[0][0],sides[1][0];crossing=LineString([nav.points[i],nav.points[j]])
        if crossing.distance(Point(center))>.2:continue
        if not floor.buffer(.01).covers(crossing):continue
        cost=crossing.length+3.25;matrix[i,j]=cost;matrix[j,i]=cost
        links.append({'id':c['id'],'indices':[i,j],'positions':[nav.points[i].tolist(),nav.points[j].tolist()],'cost_m_equivalent':cost})
    nav.graph=matrix.tocsr();nav.fields.clear()
    a=centers['R01'];b=centers['R11'];path=route(nav,a,b)
    if not path:
        from scipy.sparse.csgraph import connected_components
        count,labels=connected_components(nav.graph)
        write(ROOT/'full_pcg_output/reference_calibration_failure.json',{'components':int(count),'rooms':{k:{'position':v,'inside_free':nav.free.covers(Point(v)),'component':int(labels[nav.nearest(v)])} for k,v in centers.items()},'interaction_links':links})
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig,ax=plt.subplots(figsize=(11,8));ax.scatter(nav.points[:,0],nav.points[:,1],c=labels,s=4,cmap='tab20')
        for w in source['wall_segments']:ax.plot(*zip(w['start_m'],w['end_m']),c='black',lw=.6)
        for c in source['connections']:
            p=np.mean([c['start_m'],c['end_m']],axis=0);ax.text(*p,c['id'],fontsize=7,color='red');ax.plot(*zip(c['start_m'],c['end_m']),c='red')
        for k,v in centers.items():ax.text(*v,k,fontsize=9)
        ax.set_aspect('equal');fig.savefig(ROOT/'full_pcg_output/reference_calibration_failure.png',dpi=130);plt.close(fig)
        raise RuntimeError('reference endpoint path invalid; diagnostics saved')
    trace=LineString([a,*path,b]);actions=sum(any(np.allclose(x,l['positions'][0]) and np.allclose(y,l['positions'][1]) or np.allclose(y,l['positions'][0]) and np.allclose(x,l['positions'][1]) for x,y in zip(path,path[1:])) for l in links)
    seconds=trace.length/5+.65*actions
    result={'protocol':'full_pcg_v2_development','reference_endpoints':{'player':'R01','boss':'R09','exit':'R11'},'positions':centers,
        'source_profile_hash':digest(source),'path_length':trace.length,'squeeze_actions':actions,'interaction_links':links,'shortest_time_proxy':seconds,
        'minimum_escape_seconds':max(4,.6*trace.length/5),'area':floor.area,'convex_partition_area':reference_partition_area,
        'reference_state':'breaks open; original through gaps use squeeze links',
        'initial_exit_reachable':False,'initial_exit_note':'R11 is separated from the player by BREAK-01 in the original DXF; a finite static initial escape time does not exist.',
        'protocol_frozen':False,
        'note':'Configured reference scenario, not observed trajectory. Use walking-distance-only conservative time bound; actions and Boss destruction add delay. Full opened-through geometry and Boss schedule require separate validation. Floor from verified outer DXF shell.'}
    write(ROOT/'full_pcg_output/reference_calibration.json',result);print(result)
if __name__=='__main__':calibrate()
