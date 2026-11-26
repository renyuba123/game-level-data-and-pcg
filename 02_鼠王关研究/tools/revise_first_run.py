"""Revise the first run using user-confirmed route direction and PDF geometry."""
import csv, json, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'.tools'))
from pypdf import PdfReader
from pypdf.generic import ContentStream

root=Path(__file__).resolve().parents[1]
source=root/'source/illustrator/鼠王关玩家路线图001.ai'
run=root/'runs/ratking_run-001'
r=PdfReader(str(source)); p=r.pages[0]; props=p['/Resources']['/Properties']
layer=None; ctm=(1,0,0,1,0,0); stack=[]; path=[]; segments=[]
def mult(a,b):
    return (a[0]*b[0]+a[2]*b[1],a[1]*b[0]+a[3]*b[1],a[0]*b[2]+a[2]*b[3],a[1]*b[2]+a[3]*b[3],a[0]*b[4]+a[2]*b[5]+a[4],a[1]*b[4]+a[3]*b[5]+a[5])
def point(v): return (ctm[0]*v[0]+ctm[2]*v[1]+ctm[4],ctm[1]*v[0]+ctm[3]*v[1]+ctm[5])
for args,op in ContentStream(p['/Contents'],r).operations:
    if op==b'BDC': layer=str(props[args[1]].get_object().get('/Name'))
    elif op==b'EMC': layer=None
    elif layer=='Route':
        if op==b'q': stack.append(ctm)
        elif op==b'Q': ctm=stack.pop() if stack else (1,0,0,1,0,0)
        elif op==b'cm': ctm=mult(ctm,tuple(map(float,args)))
        elif op in (b'm',b'l',b'c'):
            vals=list(map(float,args)); path.append(point(vals[-2:]))
        elif op in (b'S',b's',b'f',b'F',b'f*',b'B',b'B*',b'b',b'b*'):
            if len(path)>=2: segments.append({'paint_index':len(segments)+1,'start':path[0],'end':path[-1],'paint':op.decode()})
            path=[]
        elif op==b'n': path=[]
# Index 4 is a filled arrowhead, not a movement segment. Segment 45 joins 9 to 10.
order=list(range(1,4))+list(range(5,10))+[45,10,11,13,12]+list(range(14,45))
assert len(order)==44
native=[]
native_path=run/'native_items.tsv'
if native_path.is_file():
    with native_path.open(encoding='utf-8-sig',newline='') as f:
        for item in csv.DictReader(f,delimiter='\t'):
            item['xy']=[tuple(map(float,s.split(':'))) for s in item['anchors'].split(';') if s]
            native.append(item)
route_native=[n for n in native if n['layer']=='Route']
used_route=set()
for seg in segments:
    if seg['paint_index']==4: continue
    matches=[]
    for item in route_native:
        if item['uuid'] in used_route or not item['xy']: continue
        a,b=item['xy'][0],item['xy'][-1]
        p,q=seg['start'],seg['end']
        distance=min(math.dist((a[0],a[1]+1500),p)+math.dist((b[0],b[1]+1500),q),
                     math.dist((b[0],b[1]+1500),p)+math.dist((a[0],a[1]+1500),q))
        matches.append((distance,item))
    if matches:
        distance,item=min(matches,key=lambda x:x[0])
        if distance<1:
            seg['native_uuid']=item['uuid']; used_route.add(item['uuid'])
assert not native or len(used_route)==44, f'Native route matching incomplete: {len(used_route)}/44'
rows=[]; previous=None; gaps=[]
for seq,index in enumerate(order,1):
    seg=segments[index-1]; start,end=(seg['end'],seg['start']) if index==13 else (seg['start'],seg['end'])
    gap=math.dist(previous,start) if previous else 0
    if gap>3: gaps.append({'before_sequence':seq,'paint_index':index,'gap_pdf_pt':round(gap,2)})
    for side,pt in [('start',start),('end',end)]:
        rows.append({'run_id':'ratking_run-001','attempt_id':'','point_id':f'P{seq:03d}_{side}',
            'sequence_index':'','candidate_order':len(rows)+1,'sequence_evidence':'user_overall_direction_plus_pdf_endpoint_continuity',
            'timestamp_s':'','x_map':f'{pt[0]:.3f}','y_map':f'{pt[1]:.3f}',
            'x_ai':f'{pt[0]:.3f}','y_ai':f'{pt[1]:.3f}',
            'room_id':'','source_object_id':('AI-uuid-'+str(seg['native_uuid'])) if 'native_uuid' in seg else f'PDF-Route-paint-{index:02d}',
            'order_status':'unverified','confidence':'low',
            'notes':('User confirmed Spawn-to-Transform overall direction; local PDF path order and endpoint continuity inferred. '
                     + f' Source PDF paint {index}. '
                     + ('Segment reversed to join neighbors.' if index==13 else '')
                     + (f' Gap from prior segment {gap:.2f} PDF pt.' if side=='start' and gap>3 else ''))})
    previous=end
with (run/'route_points.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
with (run/'events.csv').open('r',encoding='utf-8-sig',newline='') as f:
    erows=list(csv.DictReader(f)); efields=list(erows[0])
for event in erows:
    event['x_map']=event['x_ai_pdf'];event['y_map']=event['y_ai_pdf']
    if event['source_layer']=='Spawn': event['notes']='Spawn is route start: user confirmed; timing and attempt still unverified'
    if event['source_layer']=='Transform': event['notes']='One of two Transform marks; exact end-associated marker needs review'
used_events=set()
for event in erows:
    candidates=[]
    for item in native:
        if item['layer']!=event['source_layer'] or item['uuid'] in used_events or not item['xy']: continue
        x=sum(p[0] for p in item['xy'])/len(item['xy'])
        y=sum(p[1] for p in item['xy'])/len(item['xy'])+1500
        candidates.append((math.dist((x,y),(float(event['x_map']),float(event['y_map']))),item))
    if candidates:
        distance,item=min(candidates,key=lambda x:x[0])
        if distance<30:
            event['source_object_id']='AI-uuid-'+str(item['uuid'])
            match_note='native object matched by layer and centroid'
            if match_note not in event['notes']:
                event['notes']+='; '+match_note
            used_events.add(item['uuid'])
assert not native or len(used_events)==24, f'Native event matching incomplete: {len(used_events)}/24'
with (run/'events.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=efields);w.writeheader();w.writerows(erows)
manifest=json.loads((run/'run_manifest.json').read_text(encoding='utf-8'))
manifest.update(schema_version='1.1',source_files=['source/illustrator/鼠王关玩家路线图001.ai'],source_video='2026-11-14 20-03-35.mp4',
    coordinate_system='PDF_AI_points_y_up',metric_scale_known=False,route_order_verified=False,
    route_direction_status='user_confirmed_spawn_to_transform',spawn_event_id=next(e['event_id'] for e in erows if e['source_layer']=='Spawn'),
    end_status='user_confirmed_near_transform_exact_marker_needs_review',
    route_sequence_status='candidate_from_user_direction_and_pdf_geometry',
    route_segment_count=len(order),route_junction_gaps=gaps,
    analysis_status='partially_derived_needs_review')
(run/'run_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
review=run/'review_needed.csv'
with review.open('r',encoding='utf-8-sig',newline='') as f:
    qrows=list(csv.DictReader(f));qfields=list(qrows[0])
qrows=[q for q in qrows if q['review_id'] not in ('Q004','Q009','Q010','Q011')]
qrows.extend([
    dict(review_id='Q004',category='route_sequence',source_layer='Route',location='all paths',question='Overall direction confirmed Spawn to left Transform-side endpoint; verify exact video sequence and attempts.',status='partially_resolved'),
    dict(review_id='Q009',category='route_junction',source_layer='Route',location='between PDF paints 16 and 17',question='8.64 PDF-pt gap: intentional movement discontinuity or drawing gap?',status='needs_review'),
    dict(review_id='Q010',category='route_endpoint',source_layer='Transform',location='left endpoint near PDF (197.68,730.90)',question='Which Transform mark (E001 or E002) corresponds to user-described endpoint?',status='needs_review'),
    dict(review_id='Q011',category='depthmap',source_layer='source/depthmap/history/shuwangguan.graph',location='Convex Map / VGA Map',question='Export actual convex polygons, connections, Choice/Integration values and VGA visibility attributes; register to AI page.',status='needs_review')])
with review.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=qfields);w.writeheader();w.writerows(qrows)
print('segments',len(order),'points',len(rows),'gaps',gaps)
