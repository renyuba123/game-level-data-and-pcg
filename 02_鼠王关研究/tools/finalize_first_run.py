"""Record the saved Illustrator and Depthmap deliverables with file hashes."""
import csv
import hashlib
import json
from pathlib import Path

root=Path(__file__).resolve().parents[1]
run=root/'runs/ratking_run-001';maps=root/'maps/ratking';out=root/'outputs/ratking_run-001'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
ai=root/'source/illustrator/鼠王关玩家路线图001.ai';edited=out/'ratking_run-001_edited.ai';graph=root/'source/depthmap/history/shuwangguan.graph'
figures={
 'movement_from_edited_ai':['F-Background','F-Walls','F-Movement-Labels'],
 'combat_from_edited_ai':['F-Background','F-Walls','F-Event-Labels'],
 'convex_from_edited_ai':['F-Background','F-Walls','F-Choice-Labels'],
 'visibility_from_edited_ai':['F-Background','F-Walls','F-VGA-Labels'],
 'gate_counts_from_edited_ai':['F-Background','F-Walls','F-Gate-Counts-Labels']}
files=[p for name in figures for p in (out/(name+'.svg'),out/(name+'.png'))]
assert all(p.is_file() for p in files)
assert len(list(root.rglob('*.ai')))==2
assert sha(ai)=='66238bc3f75c78f018a90749b2130a3cf0ed021977bbfbad4f8bff1d86ca2542'
m=json.loads((run/'run_manifest.json').read_text(encoding='utf-8'))
palette=json.loads((maps/'gate_counts_palette.json').read_text(encoding='utf-8'))
m.update(source_video='source/video/001/2026-11-14 20-03-35.mp4',
    coordinate_system='Depthmap_graph_XY_for_x_map_y_map; PDF_AI_points_y_up_for_x_ai_y_ai',
    metric_scale_known=False,depthmap_graph_sha256=sha(graph),
    convex_export_sha256=sha(maps/'convex_export.mif'),vga_export_sha256=sha(maps/'vga_export.txt'),
    map_transform_sha256=sha(maps/'map_transform.json'),
    edited_ai_sha256=sha(edited),edited_ai_reopened_in_illustrator=True,edited_ai_layer_count=8,
    ai_derived_figures=[p.name for p in files],
    figure_layer_views=figures,
    figure_sha256={p.name:sha(p) for p in files},
    visibility_figure_status='actual_Depthmap_Visual_Integration_HH_registered',
    gate_counts_figure_status='registered_VGA_points_with_image_calibrated_palette',
    gate_counts_render_method='derived_image_matched_value_bands',
    gate_counts_original_image='maps/ratking/gate_counts_depthmap_original.png',
    gate_counts_original_image_sha256=sha(maps/'gate_counts_depthmap_original.png'),
    gate_counts_image_native_size_px=[664,454],
    gate_counts_palette_file='maps/ratking/gate_counts_palette.json',
    gate_counts_palette_sha256=sha(maps/'gate_counts_palette.json'),
    gate_counts_palette_thresholds=palette['lower_bounds_inclusive'],
    gate_counts_palette_match_fraction=palette['matching_palette_fraction'],
    gate_counts_range=[4,7230],
    icon_audit_sha256=sha(out/'icon_audit.tsv'),
    registered_convex_rooms=9,vga_point_count=3462,
    max_registration_residual_ai_pt=2.327,
    analysis_status='spatial_data_registered_route_and_events_still_need_video_review')
m.pop('gate_counts_quantile_breaks',None)
(run/'run_manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
with (run/'review_needed.csv').open(encoding='utf-8-sig',newline='') as f:
    rows=list(csv.DictReader(f));fields=list(rows[0])
for row in rows:
    if row['review_id']=='Q008':row['status']='resolved_registered_9_convex_regions'
    if row['review_id']=='Q011':row['status']='resolved_real_exports_registered'
rows=[r for r in rows if r['review_id'] not in ('Q012','Q013')]
rows.extend([
 dict(review_id='Q012',category='event_registration',source_layer='Flamethrower',location='E012 / AI-uuid-736 AI (1129.352,779.968)',question='Marker lies outside all exported convex polygons; check whether it sits at a door, was offset in Illustrator, or belongs to a different map version.',status='needs_review'),
 dict(review_id='Q013',category='door_verification',source_layer='Convex Map Pajek',location='all 9 graph edges',question='Check physical opening, door centre and passability for each graph adjacency before using as a PCG traversal edge.',status='needs_review')])
with (run/'review_needed.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
print('finalized AI',m['edited_ai_sha256'],'figures',len(files))
