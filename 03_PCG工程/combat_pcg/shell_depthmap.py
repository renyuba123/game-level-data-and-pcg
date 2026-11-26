"""Eye-height DXF sections. Retain CLI geometry, point tables and command logs."""
import math
import sys
from pathlib import Path
import ezdxf
from shapely.geometry import LineString, Polygon, Point, shape, mapping
from shapely.ops import polygonize, unary_union
from shapely import set_precision
from full_pcg.common import ROOT, read, write
from combat_pcg.spatial import profile, state_distances
sys.path.insert(0,str(ROOT/'evolution'))
from metrics import analyze
import numpy as np


def aperture(a,b,kind):
    line=LineString([a,b])
    if kind=='break': return line
    width=min(line.length,.9 if kind=='window' else .2)
    # Through has an offset sight slit beside the leaf.
    offset=(line.length-width)/2 if kind=='window' else max(0,line.length/2+.25)
    offset=min(offset,line.length-width)
    segments=[]
    if offset>1e-8: segments.append(LineString([a,line.interpolate(offset)]))
    if line.length-offset-width>1e-8: segments.append(LineString([line.interpolate(offset+width),b]))
    return unary_union(segments)


def eye_obstacles(layout, state):
    obstacles=[shape(layout['base_obstacles'])]
    for p in layout['portals']:
        if p['kind']=='normal' or (state=='all_open' and p['kind']!='window'): continue
        obstacles.append(aperture(*p['segment'],p['kind']).buffer(.09,cap_style='flat'))
    return unary_union(obstacles)


# Centre lines across untagged gaps between opposing DXF wall end caps.
# Coordinates are in the source model frame; validate both jambs before use.
OPEN_GAPS = (
    ((5.145,6.0388),(6.145,6.0388)),
    ((2.8776,-1.991),(4.0776,-1.991)),
    ((14.1187,.988),(14.1187,1.988)),
    ((12.7902,-.9173),(13.7902,-.9173)),
    ((16.0451,-1.5591),(16.0451,-.5591)),
)


def reference_layout(source, floor, blocks):
    passages = [(g['id'],g['start_m'],g['end_m']) for g in source['connections']]
    for i,(a,b) in enumerate(OPEN_GAPS):
        if max(floor.boundary.distance(Point(pt)) for pt in (a,b)) > .001:
            raise ValueError(f'Unregistered source door jamb {i}')
        line = LineString([a,b])
        if not floor.contains(LineString([line.interpolate(.02),line.interpolate(line.length-.02)])):
            raise ValueError(f'Blocked source door {i}')
        passages.append((f'normal_{i}',a,b))
    # Thin virtual closings recover contiguous rooms. They only partition labels.
    closures = unary_union([LineString([a,b]).buffer(.006,cap_style='square') for _,a,b in passages])
    partitions = floor.difference(closures)
    rooms = sorted(getattr(partitions,'geoms',[partitions]),key=lambda p:p.bounds)
    if not all(p.geom_type=='Polygon' and p.area>1 for p in rooms) or len(rooms)<3:
        raise ValueError('Unexpected DXF room partition; inspect the source')
    portals=[]; internal=[]
    for name,a,b in passages:
        length=math.dist(a,b)
        nx,nz=(a[1]-b[1])/length,(b[0]-a[0])/length
        pair=[]
        for sign in (-1,1):
            probe=Point((a[0]+b[0])/2+sign*.12*nx,(a[1]+b[1])/2+sign*.12*nz)
            group=[i for i,room in enumerate(rooms) if room.covers(probe)]
            if len(group)!=1:
                raise ValueError(f'Ambiguous side of DXF portal {name}')
            pair.append(group[0])
        if pair[0]!=pair[1]:portals.append(dict(id=name,a=pair[0],b=pair[1]))
        else:internal.append(name)
    return dict(rooms=[dict(id=i,polygon=list(p.exterior.coords),region_geometry=mapping(p)) for i,p in enumerate(rooms)],
                floor=mapping(floor),base_obstacles=mapping(blocks),portals=portals,intra_room_features=internal,
                obstacles=[dict(position=b['center_m']) for b in source['blocks']])


def analyze_floor(floor,obstacles,out,grid,**runtime):
    out.mkdir(exist_ok=True,parents=True)
    free=floor.difference(obstacles)
    doc=ezdxf.new('R2010');doc.units=4
    m=doc.modelspace(); fills=[]
    for region in getattr(free,'geoms',[free]):
        if region.geom_type!='Polygon': continue
        for ring in [region.exterior,*region.interiors]:
            pts=[(x*1000,y*1000) for x,y in ring.coords]
            for a,b in zip(pts,pts[1:]): m.add_line(a,b)
        # The CLI requires seed positions inside each physically disconnected component.
        point=region.representative_point();fills.append((point.x*1000,point.y*1000))
    dxf=out/'section.dxf';doc.saveas(dxf)
    # A continuous aperture can close on the analysis lattice. Seed the interior
    # of every room even when the point flood cannot pass such an aperture.
    step=grid/1000
    xmin,ymin,xmax,ymax=free.bounds
    safe=free.buffer(-step*.72)
    interior={(ix*grid,iy*grid) for ix in range(math.ceil(xmin/step),math.floor(xmax/step)+1)
              for iy in range(math.ceil(ymin/step),math.floor(ymax/step)+1)
              if safe.covers(Point(ix*step,iy*step))}
    rows,provenance=analyze(dxf,sorted(interior),out,grid,**runtime)
    present={(round(float(r['x'])),round(float(r['y']))) for r in rows}
    if interior-present:
        raise ValueError(f'Depthmap missed {len(interior-present)} interior grid points')
    converted=[dict(x_m=float(r['x'])/1000,z_m=float(r['y'])/1000,integration=float(r['Visual Integration [HH]']),
                    connectivity=float(r['Connectivity']),metric_m=float(r['Metric Mean Shortest-Path Distance'])/1000) for r in rows]
    return converted,provenance


def measure(layout,out,grid=400,**runtime):
    source=read(ROOT/'data/shell_source_v2.json')
    lines=[set_precision(LineString([w['start_m'],w['end_m']]),.0001) for w in source['wall_segments']]
    samples=unary_union([Polygon(r['polygon_m']) for r in source['convex_rooms']])
    ref=max(polygonize(unary_union(lines)),key=lambda f:f.intersection(samples).area)
    blocks=unary_union([Point(b['center_m']).buffer(b['radius_m'],quad_segs=12) for b in source['blocks']])
    regions=reference_layout(source,ref,blocks)
    result={}
    for state in ('initial','all_open'):
        rows,provenance=analyze_floor(shape(layout['floor']),eye_obstacles(layout,state),out/'candidate'/state,grid,**runtime)
        candidate=profile(rows,layout)
        walls=[blocks]
        for p in source['connections']:
            if p['kind']=='window' or state=='initial': walls.append(aperture(p['start_m'],p['end_m'],p['kind']).buffer(.09,cap_style='flat'))
        baseline,ref_provenance=analyze_floor(ref,unary_union(walls),out/'reference'/state,grid,**runtime)
        reference=profile(baseline,regions)
        result[state]=dict(candidate=candidate,reference=reference,reference_count=len(baseline),
                           candidate_key=provenance['key'],reference_key=ref_provenance['key'])
    states=('initial','all_open')
    result.update(state_distances({s:result[s]['candidate'] for s in states},{s:result[s]['reference'] for s in states}))
    result['reference_partition']=regions
    result['source_graph_sha256']=source['source_graph_sha256']
    result['grid_drawing_units']=grid
    result['layout_hash']=layout['layout_hash']
    result['source_dxf_sha256']=source['source_dxf_sha256']
    write(out/'comparison.json',result)
    return result


if __name__=='__main__':
    measure(read(sys.argv[1]),Path(sys.argv[2]))

