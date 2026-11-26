import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as Patch,Circle
from shapely.geometry import shape
from .geometry import parts
def preview(layout,path,title='',bounds=(-30,-30,30,30)):
    fig,ax=plt.subplots(figsize=(7,7));ax.set_aspect('equal');ax.set_xlim(bounds[0],bounds[2]);ax.set_ylim(bounds[1],bounds[3]);ax.set_title(title,fontsize=9)
    for c in layout.get('corridors',[]):
        for p in parts(shape(c['shape'])):ax.add_patch(Patch(list(p.exterior.coords),fc='#eeeeee',ec='none'))
    for r in layout['rooms']:
        ax.add_patch(Patch(r['polygon'],fc={'hub':'#e7bd84','cover':'#b7caaa'}.get(r.get('role'),'#c5d8e7'),ec='#526575',lw=.6))
    if 'floor' in layout:
        for poly in parts(shape(layout['floor'])):
            for ring in [poly.exterior,*poly.interiors]:
                x,y=ring.xy;ax.plot(x,y,color='#252525',lw=.8)
    for p in layout.get('portals',[]):
        a,b=p['segment'];ax.plot([a[0],b[0]],[a[1],b[1]],c={'normal':'#328651','through':'#0b8ab8','break':'#d67532'}[p['kind']],lw=2)
    for field,color in [('spawn','green'),('boss','red'),('exit','purple')]:
        if field in layout:
            x,y=layout[field]['position'];ax.scatter(x,y,c=color,s=20);ax.annotate(field,(x,y),fontsize=8)
    for b in layout.get('obstacles',[]):ax.add_patch(Circle(b['position'],b['radius'],fc='#665747'))
    ax.grid(alpha=.12);ax.set_xlabel('Model metres');fig.tight_layout();fig.savefig(path,dpi=130);plt.close(fig)
