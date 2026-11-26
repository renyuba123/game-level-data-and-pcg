"""Read-only extraction of the PDF-compatible AI view. Never edits the AI."""
import base64, collections, csv, glob, hashlib, json, math, subprocess, sys
from pathlib import Path
sys.path.insert(0, '.tools')
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, ContentStream, NameObject
from PIL import Image

ROOT=Path(__file__).parent
SOURCE=next(p for p in ROOT.glob('*.ai') if p.is_file())
RUN='ratking_run-001'
while (ROOT/'runs'/RUN).exists() or (ROOT/'outputs'/RUN).exists():
    RUN=f'ratking_run-{int(RUN[-3:])+1:03d}'
RUNDIR=ROOT/'runs'/RUN; OUT=ROOT/'outputs'/RUN; MAP=ROOT/'maps'/'ratking'
for d in (RUNDIR,OUT,MAP): d.mkdir(parents=True,exist_ok=True)
r=PdfReader(str(SOURCE)); page=r.pages[0]; props=page['/Resources']['/Properties']
ocgs=r.trailer['/Root']['/OCProperties']['/OCGs']
layer_names=[str(o.get_object()['/Name']) for o in ocgs]
layer_refs={str(o.get_object()['/Name'])+'#'+str(i):o for i,o in enumerate(ocgs)}
occ=collections.Counter(); layer_data=[]; current=None; items=[]
for args,op in ContentStream(page['/Contents'],r).operations:
    if op==b'BDC':
        ref=props.raw_get(args[1]); current=(str(ref.get_object()['/Name']),ref.idnum); occ[current]+=1
    elif op==b'EMC': current=None
    elif current: items.append((current,args,op))
bylayer=collections.defaultdict(list)
for k,args,op in items: bylayer[k].append((args,op))
layers=[]
for ref in ocgs:
    name=str(ref.get_object()['/Name']); key=(name,ref.idnum)
    ops=bylayer[key]; c=collections.Counter(op.decode() for _,op in ops)
    layers.append(dict(name=name,ocg_id=ref.idnum,marked_blocks=occ[key],paint_ops=sum(c[x] for x in ['S','s','f','F','f*','B','B*','b','b*','Do']),stroke_ops=c['S']+c['s'],fill_ops=c['f']+c['F']+c['f*']+c['B']+c['B*'],visible_in_pdf=bool(ops)))
(OUT/'layer_inventory.json').write_text(json.dumps(layers,ensure_ascii=False,indent=2),encoding='utf-8')

def pdf_view(path, visible):
    w=PdfWriter(); w.clone_document_from_reader(r)
    conf=w._root_object['/OCProperties']['/D']
    refs=w._root_object['/OCProperties']['/OCGs']
    conf[NameObject('/ON')]=ArrayObject([x for x in refs if str(x.get_object()['/Name']) in visible])
    conf[NameObject('/OFF')]=ArrayObject([x for x in refs if str(x.get_object()['/Name']) not in visible])
    with path.open('wb') as f:w.write(f)

def render_pdf(pdf,prefix):
    exe=Path('C:/Users/人于八/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe')
    subprocess.run([str(exe),'-f','1','-singlefile','-r','140','-png',str(pdf),str(prefix)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return prefix.with_suffix('.png')

underpdf=OUT/'space_regions.pdf'; pdf_view(underpdf,{'depthmap'})
underpng=render_pdf(underpdf,OUT/'space_regions')
datauri='data:image/png;base64,'+base64.b64encode(underpng.read_bytes()).decode()

def mm(a,b):
    return (a[0]*b[0]+a[2]*b[1],a[1]*b[0]+a[3]*b[1],a[0]*b[2]+a[2]*b[3],a[1]*b[2]+a[3]*b[3],a[0]*b[4]+a[2]*b[5]+a[4],a[1]*b[4]+a[3]*b[5]+a[5])
def nums(a): return ' '.join(f'{float(x):.3f}'.rstrip('0').rstrip('.') for x in a)
def col(a):
    v=[float(x) for x in a]
    if len(v)==1:v=v*3
    if len(v)<3:return '#555d66'
    return '#'+''.join(f'{max(0,min(255,round(x*255))):02x}' for x in v[:3])
def pathsvg(ops,kind):
    out=[]; stack=[]; ctm=(1,0,0,1,0,0); stroke='#555d66'; fill='#777777'; width=.8; path=[]
    def emit(paint):
        nonlocal path
        if not path:return
        d=' '.join(path); path=[]
        if kind=='route': s='#147dce' if paint in ('S','B','b') else 'none'; f='none' if paint in ('S','B','b') else '#147dce'; sw=2.6
        elif kind=='event': s=stroke if paint in ('S','B','b') else 'none'; f=fill if paint in ('f','B','b') else 'none'; sw=max(.8,width)
        else: s='#555d66' if paint in ('S','B','b') else 'none'; f=fill if paint in ('f','B','b') else 'none'; sw=.9
        a,b,c,d0,e,f0=ctm
        out.append(f'<path d="{d}" transform="matrix({a:.6f} {-b:.6f} {c:.6f} {-d0:.6f} {e:.6f} {1500-f0:.6f})" fill="{f}" stroke="{s}" stroke-width="{sw}" stroke-linejoin="round" stroke-linecap="round"/>')
    for args,op in ops:
        o=op.decode()
        if o=='q':stack.append((ctm,stroke,fill,width))
        elif o=='Q':
            if stack:ctm,stroke,fill,width=stack.pop()
        elif o=='cm':ctm=mm(ctm,tuple(float(x) for x in args))
        elif o in ('SCN','RG','G'):stroke=col(args)
        elif o in ('scn','rg','g'):fill=col(args)
        elif o=='w':width=float(args[0])
        elif o=='m':path.append('M '+nums(args))
        elif o=='l':path.append('L '+nums(args))
        elif o=='c':path.append('C '+nums(args))
        elif o=='h':path.append('Z')
        elif o=='re':
            x,y,w,h=map(float,args);path.append(f'M {x} {y} h {w} v {h} h {-w} Z')
        elif o in ('S','s','f','F','f*','B','B*','b','b*'):emit(o[0])
        elif o=='n':path=[]
    return '\n'.join(out)

base='\n'.join(pathsvg(ops,'base') for (name,_),ops in bylayer.items() if name=='Base')
route='\n'.join(pathsvg(ops,'route') for (name,_),ops in bylayer.items() if name=='Route')
ev='\n'.join(pathsvg(ops,'event') for (name,_),ops in bylayer.items() if name not in ('Base','Route','depthmap'))
event_marks=[]
for (name,ocg),ops in bylayer.items():
    if name in ('Base','Route','depthmap'):continue
    ctm=(1,0,0,1,0,0);stack=[];coords=[]
    for args,op in ops:
        o=op.decode()
        if o=='q':stack.append(ctm)
        elif o=='Q':
            if stack:ctm=stack.pop()
        elif o=='cm':ctm=mm(ctm,tuple(float(x) for x in args))
        elif o in ('m','l','c','re'):
            values=[float(x) for x in args]
            if o=='re':
                x,y,w,h=values; pts=[(x,y),(x+w,y+h)]
            else:pts=list(zip(values[::2],values[1::2]))
            for x,y in pts:coords.append((ctm[0]*x+ctm[2]*y+ctm[4],ctm[1]*x+ctm[3]*y+ctm[5]))
        elif o in ('f','F','f*','B','B*','b','b*'):
            if coords:
                x=sum(p[0] for p in coords)/len(coords);y=sum(p[1] for p in coords)/len(coords)
                event_marks.append(dict(event_id=f'E{len(event_marks)+1:03d}',layer=name,ocg=ocg,x=x,y=y))
            coords=[]
        elif o in ('S','s','n'):coords=[]
def make_svg(kind):
    movement=kind=='movement_clean'
    title='Movement Trajectory' if movement else 'Combat Events Distribution'
    labels='\n'.join(f'<text x="{m["x"]+7:.1f}" y="{1500-m["y"]-7:.1f}" font-family="Arial" font-size="12" fill="#26384a">{m["event_id"]}</text>' for m in event_marks)
    body=route if movement else f'<g opacity="0.27">{route}</g>\n{ev}\n{labels}'
    legend='<text x="1120" y="107" font-size="18">Blue: route geometry</text><text x="1120" y="140" font-size="18">Direction / order unverified</text>' if movement else '<text x="1120" y="107" font-size="18">Original event symbols</text><text x="1120" y="140" font-size="18">Layer meanings to confirm</text>'
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1500" height="1500" viewBox="0 0 1500 1500"><rect width="1500" height="1500" fill="white"/><image x="0" y="0" width="1500" height="1500" opacity="0.22" xlink:href="{datauri}"/><g>{base}</g><g>{body}</g><rect x="20" y="20" width="1460" height="170" fill="white" fill-opacity="0.92"/><text x="42" y="75" font-family="Arial" font-size="31" fill="#1c2733">Rat King | {title}</text><text x="42" y="111" font-family="Arial" font-size="18" fill="#34445a">{RUN} · AI vector source · map units · not to scale</text><text x="42" y="144" font-family="Arial" font-size="16" fill="#8b3f29">Review required: route sequence, event meanings, space IDs</text>{legend}</svg>'''
    p=OUT/f'{RUN}_{kind}_v01.svg';p.write_text(svg,encoding='utf-8')
    pdf=OUT/f'{RUN}_{kind}_source_layers_v01.pdf'; visible={'depthmap','Base','Route'} if movement else set(layer_names)
    pdf_view(pdf,visible)
    png=OUT/f'{RUN}_{kind}_v01.png'
    uri=p.as_uri()
    chrome=Path('C:/Program Files/Google/Chrome/Application/chrome.exe')
    subprocess.run([str(chrome),'--headless=new','--disable-gpu','--no-sandbox','--hide-scrollbars','--window-size=1500,1500',f'--screenshot={png}',uri],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
    if not png.exists():raise RuntimeError(f'PNG render failed: {png}')
make_svg('movement_clean');make_svg('combat_events')
legend=OUT/f'{RUN}_legend_v01.svg'
legend.write_text(f'''<svg xmlns="http://www.w3.org/2000/svg" width="850" height="400"><rect width="850" height="400" fill="white"/><text x="30" y="48" font-family="Arial" font-size="30">Rat King | Figure legend</text><path d="M 35 95 H 105" stroke="#147dce" stroke-width="4"/><text x="125" y="102" font-family="Arial" font-size="20">Observed route geometry; direction unknown</text><rect x="35" y="135" width="70" height="24" fill="#b8d9e7" opacity=".4"/><text x="125" y="154" font-family="Arial" font-size="20">Original space regions; no syntax values verified</text><path d="M 35 190 H 105" stroke="#555d66" stroke-width="2"/><text x="125" y="197" font-family="Arial" font-size="20">Building geometry</text><text x="35" y="255" font-family="Arial" font-size="20">Event symbols retain source appearance.</text><text x="35" y="289" font-family="Arial" font-size="20">Layer names are source labels, not confirmed actions.</text><text x="35" y="355" font-family="Arial" font-size="17">{RUN} · not to scale · review required</text></svg>''',encoding='utf-8')
subprocess.run([str(Path('C:/Program Files/Google/Chrome/Application/chrome.exe')),'--headless=new','--disable-gpu','--no-sandbox','--window-size=850,400',f'--screenshot={OUT/f"{RUN}_legend_v01.png"}',legend.as_uri()],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)

def csvwrite(path,fields,rows):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
csvwrite(RUNDIR/'route_points.csv','run_id attempt_id point_id sequence_index timestamp_s x_map y_map room_id source_object_id order_status confidence notes'.split(),[])
csvwrite(RUNDIR/'events.csv','run_id attempt_id event_id event_type source_layer source_object_id timestamp_s x_map y_map room_id route_point_id verification_status notes x_ai_pdf y_ai_pdf'.split(),[
    dict(run_id=RUN,attempt_id='',event_id=m['event_id'],event_type='unknown',source_layer=m['layer'],source_object_id=f'OCG-{m["ocg"]}:{m["event_id"]}',timestamp_s='',x_map='',y_map='',room_id='',route_point_id='',verification_status='needs_review',notes='Visible filled symbol; source action and timestamp unverified',x_ai_pdf=f'{m["x"]:.3f}',y_ai_pdf=f'{m["y"]:.3f}') for m in event_marks])
csvwrite(RUNDIR/'review_needed.csv','review_id category source_layer location question status'.split(),[
    dict(review_id=f'Q{i:03d}',category='source_review',source_layer=layer,location=loc,question=q,status='needs_review') for i,(layer,loc,q) in enumerate([
    ('Route','upper long segment','Does this segment follow a passable corridor?'),('Route','central crossing','Which lines cross in time, and are they connected?'),('Route','right narrow passage','Does route cross a wall or doorway?'),('Route','all paths','Confirm direction and attempt boundaries from video.'),('Break','two OCG layers','What does each Break layer mean?'),('Crossbow','layer','Confirm action represented.'),('Transform','layer','Confirm action represented.'),('depthmap','all regions','Provide stable room IDs and metric legend/source.')],1)])
(RUNDIR/'raw_vectors.json').write_text(json.dumps({'source':'PDF-compatible AI','route_paint_ops':next(x['paint_ops'] for x in layers if x['name']=='Route'),'object_order_is_time':False,'coordinate_status':'AI/PDF points, map transform unregistered'},indent=2),encoding='utf-8')
(RUNDIR/'run_manifest.json').write_text(json.dumps({'schema_version':'1.0','map_id':'ratking','run_id':RUN,'source_files':[str(SOURCE.name)],'source_video':None,'coordinate_system':'map_units_unregistered','metric_scale_known':False,'route_order_verified':False,'event_layer_mapping_verified':False,'contains_retries':None,'analysis_status':'needs_review','source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest()},indent=2),encoding='utf-8')
for name,data in [('rooms.json',{'map_id':'ratking','status':'needs_review','rooms':[]}),('connections.json',{'map_id':'ratking','status':'needs_review','connections':[]}),('map_transform.json',{'map_id':'ratking','status':'needs_review','source_coordinate_system':'PDF/AI points','target_coordinate_system':'map_units','transform':None,'scale_known':False})]:
    p=MAP/name
    if not p.exists():p.write_text(json.dumps(data,indent=2),encoding='utf-8')
print(RUN,[(x['name'],x['paint_ops']) for x in layers])
