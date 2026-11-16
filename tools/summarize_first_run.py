"""Produce inspectable first-run, room, and VGA summaries without causal claims."""
import csv
import json
import math
from collections import Counter
from pathlib import Path
from register_depthmap import point_in_polygon

root=Path(__file__).resolve().parents[1]
maps=root/'maps/ratking';run=root/'runs/ratking_run-001'
rooms=json.loads((maps/'rooms.json').read_text(encoding='utf-8'))['rooms']
edges=json.loads((maps/'connections.json').read_text(encoding='utf-8'))['connections']
with (run/'route_points.csv').open(encoding='utf-8-sig',newline='') as f:points=list(csv.DictReader(f))
with (run/'events.csv').open(encoding='utf-8-sig',newline='') as f:events=list(csv.DictReader(f))
with (maps/'vga_export.txt').open(encoding='utf-8-sig',newline='') as f:vga=list(csv.DictReader(f,delimiter='\t'))
room_sequence=[];length_by_room=Counter()
for a,b in zip(points[::2],points[1::2]):
    r=a['room_id'] if a['room_id']==b['room_id'] else ''
    if r:length_by_room[r]+=math.dist((float(a['x_ai']),float(a['y_ai'])),(float(b['x_ai']),float(b['y_ai'])))
    room_sequence.append((a['room_id'],b['room_id']))
collapsed=[]
for a,b in room_sequence:
    for r in (a,b):
        if r and (not collapsed or collapsed[-1]!=r):collapsed.append(r)
degree=Counter()
for e in edges:degree[e['from_room_id']]+=1;degree[e['to_room_id']]+=1
values={r['room_id']:[] for r in rooms}
gate_values={r['room_id']:[] for r in rooms}
unassigned=0
for p in vga:
    x=float(p['x']);y=float(p['y']);hits=[r['room_id'] for r in rooms if point_in_polygon(x,y,r['polygon_graph'])]
    if len(hits)==1:
        values[hits[0]].append(float(p['Visual Integration [HH]']))
        gate_values[hits[0]].append(float(p['Gate Counts']))
    else:unassigned+=1
event_by_room=Counter(e['room_id'] or 'unassigned' for e in events)
room_stats=[]
for r in rooms:
    k=r['room_id'];v=values[k]
    room_stats.append({'room_id':k,'choice':r['choice'],'convex_degree':degree[k],
        'route_segment_endpoint_count':sum(p['room_id']==k for p in points),
        'drawn_segment_length_ai_pt_within_one_room':round(length_by_room[k],2),
        'event_mark_count':event_by_room[k],
        'vga_point_count':len(v),'vga_visual_integration_hh_mean':round(sum(v)/len(v),3) if v else None,
        'vga_visual_integration_hh_min':round(min(v),3) if v else None,
        'vga_visual_integration_hh_max':round(max(v),3) if v else None,
        'vga_gate_counts_mean':round(sum(gate_values[k])/len(gate_values[k]),1) if v else None,
        'vga_gate_counts_min':int(min(gate_values[k])) if v else None,
        'vga_gate_counts_max':int(max(gate_values[k])) if v else None})
summary={'map_id':'ratking','run_id':'ratking_run-001',
    'route_status':'candidate local order; overall Spawn-to-Transform direction user confirmed',
    'room_visit_sequence_candidate':collapsed,
    'room_visit_count_candidate':dict(Counter(collapsed)),
    'room_stats':room_stats,'vga_unassigned_point_count':unassigned,
    'events_unassigned_count':event_by_room['unassigned'],
    'topology_cycle_count':len(edges)-len(rooms)+1,
    'caveats':['one run; no population frequency or success-rate inference',
        'event semantics and times not verified against video',
        'drawn segment lengths are AI points, not game metres',
        'VGA point-in-polygon follows exported Convex geometry; boundary cells may be unassigned',
        'Gate Counts is a Depthmap point metric, not player traversal frequency']}
(run/'derived_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
