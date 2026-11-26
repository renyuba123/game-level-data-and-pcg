"""Versioned, scale-comparable spatial summaries; never use supplied room labels."""
import math
import numpy as np
from shapely.geometry import Polygon,Point,shape
from .contracts import require,number

METRICS=('integration','connectivity_ratio','metric_over_sqrt_area')
QUANTILES=(.05,.25,.5,.75,.95)

def functional_regions(layout):
    rooms=layout['rooms'];areas=[(shape(r['region_geometry']) if 'region_geometry' in r else Polygon(r['polygon'])).area for r in rooms];cut=float(np.quantile(areas,.75))
    neighbors={r['id']:set() for r in rooms}
    for p in layout['portals']:
        neighbors[p['a']].add(p['b']);neighbors[p['b']].add(p['a'])
    degree={k:len(v) for k,v in neighbors.items()}
    regions=[]
    for r,area in zip(rooms,areas):
        poly=shape(r['region_geometry']) if 'region_geometry' in r else Polygon(r['polygon']);rect=list(poly.minimum_rotated_rectangle.exterior.coords)
        lengths=[math.dist(a,b) for a,b in zip(rect,rect[1:])];aspect=max(lengths)/max(min(lengths),1e-9)
        blocked=any(poly.covers(Point(b['position'])) for b in layout['obstacles'])
        role='core' if area>=cut and degree[r['id']]>=3 else 'connector' if aspect>=3 else 'cover' if poly.area/poly.convex_hull.area<.9 or blocked else 'terminal' if degree[r['id']]==1 else 'side'
        regions.append((poly,role))
    # Geometry order, not ID/label, resolves boundary points reproducibly.
    return sorted(regions,key=lambda item:item[0].wkt)

def profile(rows,layout):
    require(len(rows)>=2,'insufficient VGA points')
    # Analysis population is physical floor minus physical static obstacles.
    area=shape(layout['floor']).difference(shape(layout['base_obstacles'])).area
    number(area,'playable area',1e-9)
    regions=functional_regions(layout);values=[];roles=[]
    for row in rows:
        point=Point(row['x_m'],row['z_m'])
        role=next((role for poly,role in regions if poly.covers(point)),'connector')
        require(shape(layout['floor']).buffer(1e-7).covers(point),'VGA point outside floor: registration/units error')
        v=[number(row['integration'],'integration',0),number(row['connectivity'],'connectivity',0,len(rows)-1)/(len(rows)-1),number(row['metric_m'],'metric_m',0)/math.sqrt(area)]
        values.append(v);roles.append(role)
    a=np.array(values)
    return {'point_count':len(rows),'playable_area_m2':area,'global':{m:np.quantile(a[:,i],QUANTILES).tolist() for i,m in enumerate(METRICS)},
        'roles':{role:{m:np.quantile(a[np.array(roles)==role,i],QUANTILES).tolist() for i,m in enumerate(METRICS)} for role in sorted(set(roles))}}

def distances(candidate,reference):
    """Only reference quantiles set scale; absent reference roles receive distance 1."""
    global_terms=[];regional_terms=[]
    for m in METRICS:
        q=np.array(reference['global'][m]);scale=max(q[-1]-q[0],abs(q[2])*.01,1e-9)
        global_terms.append(float(np.abs(np.array(candidate['global'][m])-q).mean()/scale))
        for role,fields in reference['roles'].items():
            other=candidate['roles'].get(role)
            regional_terms.append(1. if other is None else float(np.abs(np.array(other[m])-np.array(fields[m])).mean()/scale))
    require(bool(regional_terms),'reference has no functional populations')
    return {'global_distance':float(np.mean(global_terms)),'regional_distance':float(np.mean(regional_terms))}

def state_distances(candidates,references):
    require(set(candidates)==set(references)=={'initial','all_open'},'both states required')
    values=[distances(candidates[s],references[s]) for s in ['initial','all_open']]
    return {k:sum(v[k] for v in values)/2 for k in values[0]}
