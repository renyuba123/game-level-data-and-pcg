"""Recover adjacency from sealed physical passages, independently of Genome edges."""
import numpy as np
from shapely.geometry import shape,Point,LineString
from shapely.ops import unary_union
from .geometry import parts

def reconstruct(layout,config):
    floor=shape(layout['floor']);base=shape(layout['base_obstacles'])
    # Seal every portal, including ordinary passages, to isolate functional regions.
    seals=[]
    for p in layout['portals']:
        c=np.array(p['center']);t=np.array(p['tangent'])
        seals.append(LineString([c-t*(p['width']/2+.12),c+t*(p['width']/2+.12)]).buffer(.09,cap_style='flat'))
    free=floor.difference(unary_union([base,*seals]).buffer(config['player_radius']+.025))
    regions=[p for p in parts(free) if p.geom_type=='Polygon' and p.area>.001]
    memberships={};issues=[]
    for r in layout['rooms']:
        matches=[i for i,p in enumerate(regions) if p.covers(Point(r['center']))]
        memberships[r['id']]=matches[0] if len(matches)==1 else None
        if len(matches)!=1:issues.append('sealed_room_anchor_missing:'+r['id'])
    inverse={}
    for rid,region in memberships.items():inverse.setdefault(region,[]).append(rid)
    for region,rooms in inverse.items():
        if region is not None and len(rooms)>1:issues.append('unrecorded_geometric_shortcut:'+','.join(sorted(rooms)))
    observed=[];mapping=[]
    for p in layout['portals']:
        # Room membership of the two adjacent sealed regions is inferred spatially.
        c=np.array(p['center']);n=np.array(p['normal']);sides=[]
        for sign in [-1,1]:
            found=None
            for distance in np.arange(.50,1.51,.10):
                q=Point(c+sign*n*distance)
                ids=[i for i,poly in enumerate(regions) if poly.covers(q)]
                if len(ids)==1 and ids[0] in inverse and len(inverse[ids[0]])==1:
                    found=inverse[ids[0]][0];break
            sides.append(found)
        if None in sides or set(sides)!={p['a'],p['b']}:issues.append('portal_geometry_mismatch:'+p['id'])
        else:observed.append(sorted(sides))
        mapping.append({'portal':p['id'],'observed_rooms':sides,'expected_rooms':[p['a'],p['b']]})
    return {'ok':not issues,'issues':issues,'room_components':memberships,'edges':observed,'portals':mapping,
            'method':'seal all portals, recover clearance components, identify rooms on each physical portal side'}
