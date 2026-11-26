import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from shell_layout import build,shell_reference
from full_pcg.common import ROOT,read,write
from shapely.geometry import shape

def test(seed):
    try:
        l=build(seed)
        return dict(seed=seed,ok=True,layout=l)
    except ValueError as e:
        return dict(seed=seed,ok=False,reason=str(e))

def plot(rows,out):
    src=read(ROOT/'data/shell_source_v2.json')
    plt.rcParams["font.sans-serif"]=["Microsoft YaHei","DejaVu Sans"]
    boxes=[shell_reference(src).bounds]+[r["layout"]["bounds"] for r in rows[:6] if r["ok"]]
    bounds=[f(v) for f,v in zip([min,min,max,max],zip(*boxes))]
    fig,axes=plt.subplots(2,4,figsize=(16,6.5),layout='constrained')
    for ax in axes.flat:
        ax.set_aspect('equal');ax.set_xlim(bounds[0]-1,bounds[2]+1);ax.set_ylim(bounds[1]-1,bounds[3]+1);ax.axis('off')
    ax=axes.flat[0];ax.set_title('原始 DXF')
    for wall in src['wall_segments']:
        ax.plot(*zip(wall['start_m'],wall['end_m']),color='#192b35',lw=.8)
    for color,layer in [('#17849d','through'),('#a33b9f','window'),('#d26d3c','break')]:
        for p in src['connections']:
            if p['kind']==layer:ax.plot(*zip(p['start_m'],p['end_m']),color=color)
    for o in src['blocks']:ax.add_patch(plt.Circle(o['center_m'],o['radius_m'],color='#5a4f40'))
    for ax,r in zip(list(axes.flat)[1:],rows[:6]):
        ax.set_title('Seed '+str(r['seed']))
        if not r['ok']:ax.text(0,2,r['reason'][:45],wrap=True);continue
        l=r['layout']
        for room in l['rooms']:
            n=room['id'];color='#f4d290' if n in ('hall','foyer') else '#b4d4c3' if n.startswith(('left','north','south')) else '#b6cde2'
            ax.fill(*zip(*room['polygon']),color=color)
        w=shape(l['walls'])
        for poly in getattr(w,'geoms',[w]):
            for ring in [poly.exterior,*poly.interiors]: ax.plot(*ring.xy,color='#23343c',lw=.6)
        for p in l['portals']:
            if p['kind']!='normal':ax.plot(*zip(*p['segment']),color={'through':'#17849d','window':'#a33b9f','break':'#d26d3c'}[p['kind']],lw=2)
        for o in l['obstacles']:ax.add_patch(plt.Circle(o['position'],o['radius'],color='#5a4f40'))
        for field,color in [('spawn','#24733e'),('boss','#aa3542')]:ax.scatter(*l[field]['position'],s=18,c=color)
    axes.flat[-1].text(0,3,'绿色   左翼\n黄色   主廊与转接区\n蓝色   右翼\n\n紫色   可翻越射击窗\n青色   半开挤身门\n橙色   可撞破墙\n缺口   普通门洞',fontsize=11)
    fig.savefig(out/'seeds_1_6.png',dpi=160);plt.close(fig)

def main():
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);args=p.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=True)
    reps=[];rows=[];first=[]
    with ProcessPoolExecutor(max_workers=4) as pool:
        for row in pool.map(test,range(1,101)):
            if row['seed']<=6:first.append(row)
            if row['ok']:
                l=row['layout'];write(out/('layout_%03d.json'%row['seed']),l)
                g=nx.Graph(l['topology']['edges'])
                idx=next((i for i,r in enumerate(reps) if nx.is_isomorphic(g,r)),len(reps))
                if idx==len(reps):reps.append(g)
                rows.append(dict(seed=row['seed'],ok=True,rooms=len(l['rooms']),cycles=l['topology']['cycles'],topology=idx,metrics=l['metrics'],layout_hash=l['layout_hash'],repairs=l['repair_reasons']))
            else:rows.append(row)
            if row['seed']==6:plot(first,out)
    valid=[r for r in rows if r['ok']]
    stats=dict(valid=len(valid),room_counts=sorted({r['rooms'] for r in valid}),cycle_counts=sorted({r['cycles'] for r in valid}),classes=len(reps))
    write(out/'audit.json',dict(summary=stats,attempts=rows));print(stats,flush=True)

if __name__=='__main__': main()

