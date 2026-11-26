"""Package the authoritative polygons for Godot; no second geometry generator."""
import numpy as np
from shapely import constrained_delaunay_triangles
from shapely.geometry import shape,Point,LineString
from shapely.ops import unary_union
from .geometry import parts
from .common import digest

def triangles(geometry):
    return [list(t.exterior.coords)[:3] for p in parts(geometry) if p.geom_type=='Polygon'
            for t in constrained_delaunay_triangles(p).geoms]

def prism(geometry,height,bottom=0.):
    faces=[]
    for p in parts(geometry):
        if p.geom_type!='Polygon':continue
        for t in triangles(p):
            a,b,c=[np.array(x) for x in t]
            if (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])<0:b,c=c,b
            faces.extend([[a[0],height,a[1]],[c[0],height,c[1]],[b[0],height,b[1]]])
            if bottom!=height:faces.extend([[a[0],bottom,a[1]],[b[0],bottom,b[1]],[c[0],bottom,c[1]]])
        if bottom!=height:
            for ring in [p.exterior,*p.interiors]:
                coords=list(ring.coords)
                for a,b in zip(coords,coords[1:]):
                    v=[[a[0],bottom,a[1]],[b[0],bottom,b[1]],[b[0],height,b[1]],[a[0],height,a[1]]]
                    faces.extend([v[i] for i in [0,1,2,0,2,3]])
    return faces

def package(layout,config):
    from .validation import barrier
    from .common import ROOT,read
    window = read(ROOT/"combat_pcg/window_v1.json") if layout.get("schema_version")==5 else None
    floor=shape(layout['floor']);base=shape(layout['base_obstacles']);seals=[]
    for p in layout['portals']:
        c=np.array(p['center']);t=np.array(p['tangent'])
        seals.append(LineString([c-t*(p['width']/2+.12),c+t*(p['width']/2+.12)]).buffer(.09,cap_style='flat'))
    nav={};links=[]
    for role in ['player','boss']:
        free=floor.difference(unary_union([base,*seals]).buffer(config[role+'_radius']+.025))
        nav[role]=triangles(free)
        for p in layout['portals']:
            c=np.array(p['center']);n=np.array(p['normal']);t=np.array(p['tangent'])
            candidates=[]
            safe=free.buffer(-.02)
            for sign in [-1,1]:
                side=[]
                for distance in np.arange(.55,2.51,.1):
                    for offset in [0,-.15,.15,-.3,.3,-.45,.45]:
                        q=c+sign*n*distance+t*offset
                        if safe.covers(Point(q)):side.append(q.tolist())
                side.sort(key=lambda q:(np.linalg.norm(np.array(q)-c),q))
                candidates.append(side[:40])
            if not all(candidates):raise ValueError('godot_link_endpoint_missing:'+role+':'+p['id'])
            # A link must cross near its own portal and remain inside the
            # post-open, role-sized walkable polygon. Never bridge a wall.
            available=floor.difference(base.buffer(config[role+'_radius']+.025))
            endpoints=None
            for a in candidates[0]:
                for b in candidates[1]:
                    line=LineString([a,b])
                    if line.distance(Point(c))<.15 and available.covers(line):
                        endpoints=[a,b];break
                if endpoints is not None:break
            if endpoints is None:raise ValueError('godot_link_crosses_wall:'+role+':'+p['id'])
            links.append({'portal':p['id'],'role':role,'kind':p['kind'],'points':endpoints})
    gates=[]
    for p in layout['portals']:
        if p['kind']=='normal':continue
        # Through shoulders are physical for both roles; central interaction blocker
        # is split by collision layers so the A action cannot unlock it for Boss.
        half = window["opening_half_width_m"] if p["kind"]=="window" else .45
        middle=LineString([np.array(p['center'])-np.array(p['tangent'])*half,
                           np.array(p['center'])+np.array(p['tangent'])*half]).buffer(.09,cap_style='flat')
        frame=[]
        if layout.get('schema_version')==5:
            if p['kind']=='window':
                frame=prism(middle,window["sill_m"])+prism(middle,2.4,window["lintel_m"])
            elif p['kind']=='through':
                c=np.array(p['center']);t=np.array(p['tangent'])
                leaf=LineString([c-t*.45,c+t*.25]).buffer(.09,cap_style='flat')
                frame=prism(leaf,2.4)
        gates.append({'id':p['id'],'kind':p['kind'],'faces':prism(barrier(p),2.4),
                      'middle_faces':prism(middle,2.4) if p['kind'] in ('through','window') else []})
        if layout.get('schema_version')==5: gates[-1]['ballistic_faces']=frame
    pack={'schema_version':1,'layout_hash':layout['layout_hash'],'layout':layout,
          'floor_faces':prism(floor,0), 'wall_faces':prism(shape(layout['walls']),2.4),
          'obstacle_faces':prism(unary_union([Point(o['position']).buffer(o['radius'],quad_segs=12) for o in layout['obstacles']]),1.4),
          'navigation':nav,'links':links,'gates':gates,'role_radii':{r:config[r+'_radius'] for r in ['player','boss']}}
    if window:
        pack['window']=window
        pack['window_config_hash']=digest(window)
    pack['package_hash']=digest(pack)
    return pack

def main():
    from pathlib import Path
    from .common import ROOT,read,write
    cfg=read(ROOT/'configs/full_pcg_v2.json');source=Path(read(ROOT/'full_pcg_output/latest_audit.json')['path'])
    selected=[];seen=set();rows=[read(p) for p in sorted(source.glob('seed_*.json'))]
    # Cover all available room counts first, then a further distinct seed.
    for row in rows:
        if row['validation']['ok'] and row['rooms'] not in seen:selected.append(row);seen.add(row['rooms'])
    for row in rows:
        if len(selected)>=12:break
        if row['validation']['ok'] and row not in selected:selected.append(row)
    paths=[]
    for row in selected:
        out=ROOT/f'full_pcg_output/godot/seed_{row["seed"]:04d}.json'
        write(out,package(row['layout'],cfg));paths.append(str(out));print('packaged',row['seed'],row['rooms'],flush=True)
    write(ROOT/'full_pcg_output/godot/manifest.json',{'packages':paths,'source_audit':str(source),'count':len(paths)})
if __name__=='__main__':main()
