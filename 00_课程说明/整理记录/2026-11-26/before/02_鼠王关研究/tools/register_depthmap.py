"""Register exported Depthmap+ Convex/VGA data to the source AI page.

The control points are the centres of the large, exact-colour regions in the
AI's embedded Depthmap raster. Their source coordinates are the matching MIF
REGION CENTER records. This is a cross-file registration, not a new analysis.
"""
import csv
import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / 'maps/ratking'
RUN = ROOT / 'runs/ratking_run-001'
IMAGE_W, IMAGE_H = 1570, 1028
# PDF Form /Fm0 image matrix in the unmodified original AI.
PDF_IMAGE = (1402.6358688, 918.4138045, 49.1482391, 267.3764787)
# Image component centres from tools/inspect_depthmap_raster.py. Ref 10 is
# omitted because its irregular red fill has a visibly biased pixel centroid.
CONTROL_PIXELS = {
    1: (234.080, 615.172), 2: (520.118, 781.040),
    4: (575.121, 104.755), 5: (1011.536, 589.450),
    6: (1009.719, 792.172), 7: (1225.301, 653.529),
    8: (1426.030, 640.092), 9: (378.115, 108.780),
}
ROOM_IDS = {9:'R01', 4:'R02', 10:'R03', 1:'R04', 2:'R05',
            5:'R06', 6:'R07', 7:'R08', 8:'R09'}
ROOM_DESCRIPTIONS = {9:'upper-left',4:'upper-right',10:'central long hall',
    1:'left room',2:'lower L-shaped room',5:'mid-right room',
    6:'lower-right small room',7:'right passage',8:'far-right room'}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def solve3(a,b):
    a=[list(row)+[v] for row,v in zip(a,b)]
    for i in range(3):
        p=max(range(i,3),key=lambda j:abs(a[j][i]))
        a[i],a[p]=a[p],a[i]
        assert abs(a[i][i])>1e-12
        z=a[i][i]
        a[i]=[v/z for v in a[i]]
        for j in range(3):
            if j!=i:
                z=a[j][i];a[j]=[u-z*v for u,v in zip(a[j],a[i])]
    return [row[-1] for row in a]

def fit_affine(pairs):
    q=[(x,y,1.0) for x,y,_,_ in pairs]
    n=[[sum(r[i]*r[j] for r in q) for j in range(3)] for i in range(3)]
    cx=solve3(n,[sum(r[i]*tx for r,(_,_,tx,_) in zip(q,pairs)) for i in range(3)])
    cy=solve3(n,[sum(r[i]*ty for r,(_,_,_,ty) in zip(q,pairs)) for i in range(3)])
    return (cx,cy)

def xy(t,x,y):
    return (t[0][0]*x+t[0][1]*y+t[0][2],
            t[1][0]*x+t[1][1]*y+t[1][2])

def inverse(t,x,y):
    a,b,c=t[0];d,e,f=t[1]
    det=a*e-b*d
    return ((e*(x-c)-b*(y-f))/det,(-d*(x-c)+a*(y-f))/det)

def parse_mif():
    s=(MAP/'convex_export.mif').read_text(encoding='latin1')
    body=s.split('\nData\n',1)[1]
    parts=re.split(r'(?=^REGION\s+1\s*$)',body,flags=re.M)
    shapes=[]
    for part in parts:
        if not part.lstrip().startswith('REGION'): continue
        lines=[v.strip() for v in part.splitlines() if v.strip()]
        n=int(lines[1]); polygon=[tuple(map(float,lines[i].split())) for i in range(2,2+n)]
        centre=next(tuple(map(float,m.group(1).split())) for line in lines
                    if (m:=re.match(r'CENTER\s+(.+)',line)))
        shapes.append((polygon,centre))
    with (MAP/'convex_export.txt').open(encoding='utf-8-sig',newline='') as f:
        rows=list(csv.DictReader(f,delimiter='\t'))
    valid=[r for r in rows if int(r['Ref'])!=0]
    assert len(shapes)==len(valid)==9,(len(shapes),len(valid))
    for row,(poly,center) in zip(valid,shapes):
        assert math.dist((float(row['cx']),float(row['cy'])),center)<.01
        row['polygon_graph']=poly
    return rows,valid

def read_network(valid):
    lines=(MAP/'convex_network.net').read_text().splitlines()
    vstart=lines.index('*Vertices 10')+1
    estart=lines.index('*Edges')
    # File vertex 1 is the non-polygon PLINE; remaining vertices follow MIF order.
    vertices={i:int(valid[i-2]['Ref']) for i in range(2,11)}
    edges=[]
    for line in lines[estart+1:]:
        a,b,*_=line.split();a=int(a);b=int(b)
        assert a in vertices and b in vertices
        edges.append(tuple(sorted((vertices[a],vertices[b]))))
    return edges

def point_in_polygon(x,y,p):
    inside=False
    for (ax,ay),(bx,by) in zip(p,p[1:]+p[:1]):
        if (ay>y)!=(by>y) and x<(bx-ax)*(y-ay)/(by-ay)+ax:inside=not inside
    return inside

def save_csv(path,rows):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    rows,valid=parse_mif()
    to_pdf=lambda u,v:(PDF_IMAGE[2]+PDF_IMAGE[0]*u/IMAGE_W,
                       PDF_IMAGE[3]+PDF_IMAGE[1]*(1-v/IMAGE_H))
    pairs=[]
    for r in valid:
        ref=int(r['Ref'])
        if ref in CONTROL_PIXELS:
            x,y=map(float,(r['cx'],r['cy']))
            tx,ty=to_pdf(*CONTROL_PIXELS[ref]);pairs.append((x,y,tx,ty))
    t=fit_affine(pairs)
    residuals=[]
    for r in valid:
        ref=int(r['Ref'])
        if ref not in CONTROL_PIXELS:continue
        x,y=map(float,(r['cx'],r['cy']))
        tx,ty=to_pdf(*CONTROL_PIXELS[ref])
        residuals.append({'depthmap_ref':ref,'room_id':ROOM_IDS[ref],
            'residual_pdf_pt':round(math.dist(xy(t,x,y),(tx,ty)),3)})
    # Grid spacing is 200 exported Depthmap units. The stated tolerance is half
    # one grid cell when projected to the AI page.
    half_grid=100*min(math.hypot(t[0][0],t[1][0]),math.hypot(t[0][1],t[1][1]))
    max_error=max(v['residual_pdf_pt'] for v in residuals)
    print('control residuals',residuals,'max',max_error,'half grid',half_grid)
    assert max_error < half_grid, 'Registration failed: residual exceeds half a VGA cell'
    graph=ROOT/'shuwangguan.graph'
    transform={'map_id':'ratking','status':'registered',
        'source_coordinate_system':'Depthmap graph XY; MIF declares NonEarth metres but game scale is unverified',
        'target_coordinate_system':'PDF_AI_points_y_up',
        'transform':{'x_ai':t[0],'y_ai':t[1]},
        'controls':residuals,'max_residual_pdf_pt':round(max_error,3),
        'rms_residual_pdf_pt':round(math.sqrt(sum(r['residual_pdf_pt']**2 for r in residuals)/len(residuals)),3),
        'acceptance_tolerance_pdf_pt':round(half_grid,3),
        'vga_grid_spacing_graph_units':200,'graph_sha256':sha(graph),
        'convex_mif_sha256':sha(MAP/'convex_export.mif'),
        'vga_export_sha256':sha(MAP/'vga_export.txt'),
        'scale_known':False}
    (MAP/'map_transform.json').write_text(json.dumps(transform,ensure_ascii=False,indent=2),encoding='utf-8')
    rooms=[]
    for r in valid:
        ref=int(r['Ref']);p=r['polygon_graph']
        rooms.append({'room_id':ROOM_IDS[ref],'depthmap_ref':ref,
            'description':ROOM_DESCRIPTIONS[ref],
            'polygon_graph':[[round(x,3),round(y,3)] for x,y in p],
            'polygon_ai':[[round(u,3),round(v,3)] for u,v in (xy(t,x,y) for x,y in p)],
            'center_graph':[float(r['cx']),float(r['cy'])],
            'center_ai':[round(v,3) for v in xy(t,float(r['cx']),float(r['cy']))],
            'choice':float(r['Choice']),'convex_connectivity':int(float(r['Connectivity'])),
            'integration_hh':float(r['Integration [HH]']),
            'source':'Depthmap+ Beta 1.0 Convex Map MIF/MID and tab export'})
    rooms.sort(key=lambda r:r['room_id'])
    edges=read_network(valid)
    degrees={r['depthmap_ref']:0 for r in rooms}
    for a,b in edges:degrees[a]+=1;degrees[b]+=1
    for r in rooms:
        assert degrees[r['depthmap_ref']]==r['convex_connectivity'],r['room_id']
    connections=[{'from_room_id':ROOM_IDS[a],'to_room_id':ROOM_IDS[b],
        'depthmap_refs':[a,b],'source':'Depthmap+ Convex Map Pajek edge',
        'passable_door_verified':False,'door_center_graph':None}
        for a,b in edges]
    (MAP/'rooms.json').write_text(json.dumps({'map_id':'ratking','status':'registered_depthmap_convex_polygons',
        'room_count':len(rooms),'source_graph_sha256':sha(graph),'rooms':rooms},ensure_ascii=False,indent=2),encoding='utf-8')
    (MAP/'connections.json').write_text(json.dumps({'map_id':'ratking','status':'depthmap_graph_edges_door_positions_pending',
        'connection_count':len(connections),'connections':connections},ensure_ascii=False,indent=2),encoding='utf-8')
    graph_hash=sha(graph)
    convex_rows=[{'room_id':r['room_id'],'depthmap_ref':r['depthmap_ref'],
        'Choice':r['choice'],'Integration_HH':r['integration_hh'],
        'Convex_Connectivity':r['convex_connectivity'],
        'source_graph_sha256':graph_hash,'metric_status':'observed_depthmap_export'} for r in rooms]
    save_csv(MAP/'convex_metrics.csv',convex_rows)
    for name in ('route_points.csv','events.csv'):
        with (RUN/name).open(encoding='utf-8-sig',newline='') as f: data=list(csv.DictReader(f))
        for row in data:
            x=float(row['x_ai'] if name=='route_points.csv' else row['x_ai_pdf'])
            y=float(row['y_ai'] if name=='route_points.csv' else row['y_ai_pdf'])
            gx,gy=inverse(t,x,y)
            row['x_map']=f'{gx:.3f}';row['y_map']=f'{gy:.3f}'
            hits=[r['room_id'] for r in rooms if point_in_polygon(gx,gy,r['polygon_graph'])]
            row['room_id']=hits[0] if len(hits)==1 else ''
        save_csv(RUN/name,data)
        print(name,'room-assigned',sum(bool(r['room_id']) for r in data),'/',len(data))
    with (MAP/'vga_export.txt').open(encoding='utf-8-sig',newline='') as f:vga=list(csv.DictReader(f,delimiter='\t'))
    point_rows=[]
    for p in vga:
        gx,gy=float(p['x']),float(p['y'])
        ax,ay=xy(t,gx,gy)
        point_rows.append({'point_ref':p['Ref'],'x_graph':p['x'],'y_graph':p['y'],
            'x_ai':round(ax,3),'y_ai':round(ay,3),
            'Visual_Integration_HH':p['Visual Integration [HH]'],
            'VGA_Connectivity':p['Connectivity'],'Gate_Counts':p['Gate Counts'],
            'Visual_Mean_Depth':p['Visual Mean Depth'],
            'source_graph_sha256':graph_hash,'metric_status':'observed_depthmap_export'})
    save_csv(MAP/'vga_points.csv',point_rows)
    metrics={}
    for field in ('Visual Integration [HH]','Connectivity','Gate Counts','Visual Mean Depth'):
        vals=[float(r[field]) for r in vga if r[field] and float(r[field])>=0]
        metrics[field]={'count':len(vals),'min':min(vals),'max':max(vals),'mean':sum(vals)/len(vals)}
        if field=='Gate Counts':
            ordered=sorted(vals)
            breaks=[ordered[math.ceil(len(ordered)*q/5)-1] for q in range(1,5)]
            metrics[field]['quantile_breaks_20_40_60_80']=breaks
            metrics[field]['unit']='count'
            metrics[field]['interpretation']='Depthmap VGA Gate Counts; not player traversal frequency'
    summary={'map_id':'ratking','point_count':len(vga),'metrics':metrics,
        'grid_spacing_graph_units':200,'scale_known':False,
        'source':'Depthmap+ Beta 1.0 Map > Export, VGA Map tab-delimited text',
        'source_sha256':sha(MAP/'vga_export.txt')}
    (MAP/'vga_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print('rooms',len(rooms),'edges',len(edges),'vga',len(vga),metrics)

if __name__=='__main__':main()
