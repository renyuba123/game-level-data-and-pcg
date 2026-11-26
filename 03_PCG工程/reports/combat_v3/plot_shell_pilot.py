"""Render a deterministic, paired father/child replay from the pilot archive."""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

from full_pcg.common import read,write
from full_pcg.shell_pilot import load_packet


def evidence(root, row):
    folder = root/'evaluation'/str(row['seed'])/row['layout_hash']/'episodes'
    return folder,read(folder/'manifest.json')['outcomes']


def select_pair(root):
    archive = {}
    pairs = []
    for gen in range(3):
        required = root/'genetic'/f'generation_{gen:02}.json'
        for child in read(required)['requests']:
            if child['topology_changed'] and child['status']!='INVALID':
                parent = archive[child['parents'][0]]
                left,a = evidence(root,parent)
                right,b = evidence(root,child)
                for case in sorted(a.keys() & b.keys()):
                    pair_rank = (a[case]['result']=='victory' and b[case]['result']=='victory',
                                 a[case]['phase']==b[case]['phase']==2,
                                 b[case]['result']=='victory')
                    pairs.append((pair_rank,parent,child,case,left/f'{case}.json',right/f'{case}.json'))
            archive[child['id']] = child
    if not pairs:
        raise ValueError('no valid non-isomorphic parent/child comparison')
    return max(pairs,key=lambda item:item[0])


def annotate(ax, layout, raw, scale):
    for room in layout['rooms']:
        n = room['id']
        tint = '#efd28f' if n in ('hall','foyer') else '#adc9d9' if n.startswith('east') else '#c1d8cb'
        poly = scale*np.asarray(room['polygon'])
        ax.fill(*poly.T,color=tint,edgecolor='#344950',lw=.55,alpha=.65)
    for gate in layout['portals']:
        color = {'normal':'#f8f9f6','through':'#0086a2','window':'#8150a5','break':'#b35d32'}[gate['kind']]
        ax.plot(*(scale*np.asarray(gate['segment'])).T,color=color,lw=2.5)
    for o in layout['obstacles']:
        ax.add_patch(plt.Circle(scale*np.asarray(o['position']),o['radius'],color='#594d43'))
    for supply in layout['supplies']:
        ax.scatter(*(scale*np.asarray(supply['position'])),s=14,c='#555d55',marker='+')

    frames = raw['frames']
    hz = raw['physics_hz']
    track = np.asarray([f['p'] for f in frames])
    boss = np.asarray([f['b'] for f in frames])
    ax.plot(*boss.T,color='#83505a',lw=.7,alpha=.35,ls=':')
    stages = np.asarray([f['phase'] for f in frames])
    for phase,color in ((1,'#15609b'),(2,'#ab461b')):
        if np.any(stages==phase):
            ax.plot(*track[stages==phase].T,color=color,lw=1.3,alpha=.8)
    prefix = min(5*hz,len(track))
    ax.plot(*track[:prefix].T,color='#177359',lw=2.3)
    ax.scatter(*track[0],c='#177359',s=30,marker='o',zorder=5)
    ax.scatter(*track[-1],c='#442f37',s=35,marker='x',zorder=5)
    events = raw['events']
    first = next((e for e in events if e['kind']=='hit' and e['data']['target']=='large_boss'),None)
    split = next((e for e in events if e['kind']=='split'),None)
    pickups = [e for e in events if e['kind']=='pickup_end']
    second = [e for e in pickups if split and e['step']>split['step']]
    for items,marker,color,label in (([first] if first else [],'*','#fbc94a','首击'),
                                      (second,'s','#137676','二阶段取弹')):
        for event in items:
            pos = track[min(event['step']-1,len(track)-1)]
            ax.scatter(*pos,s=50,c=color,marker=marker,edgecolors='#263235',linewidths=.4,zorder=6)
            ax.annotate(f"{label} {event['t']:.1f}s",pos,xytext=(4,6),textcoords='offset points',
                        fontsize=8,zorder=7)
    ax.set_aspect('equal')
    ax.set_xlabel('世界 X（模型米）')
    outcome = {'death':'死亡','victory':'胜利','timeout':'超时'}[raw['result']]
    ax.text(.02,.02,f"{outcome} · {raw['duration_s']:.1f} 秒 · 二阶段取弹 {len(second)} 次",
            transform=ax.transAxes,fontsize=9,va='bottom')
    return dict(result=raw['result'], first_hit_s=first['t'] if first else None,
                split_s=split['t'] if split else None, pickups=len(pickups),
                phase2_pickups=len(second), duration_s=raw['duration_s'])


def plot(root):
    _,parent,child,case,parent_ep,child_ep = select_pair(root)
    layouts = [load_packet(root,row['layout_hash'])['layout'] for row in (parent,child)]
    scale = read(root/'config_snapshot.json')['layout_scale']
    plt.rcParams.update({'font.sans-serif':['Microsoft YaHei','DejaVu Sans'],'axes.unicode_minus':False})
    fig,axes = plt.subplots(1,2,figsize=(13,6),sharex=True,sharey=True,layout='constrained')
    bounds = scale*np.asarray([l['bounds'] for l in layouts])
    axes[0].set(xlim=(bounds[:,0].min()-1,bounds[:,2].max()+1),
                ylim=(bounds[:,1].min()-1,bounds[:,3].max()+1),ylabel='世界 Z（模型米）')
    compare = []
    for ax,layout,row,ep,label in zip(axes,layouts,(parent,child),(parent_ep,child_ep),('父代','子代')):
        ax.set_title(f"{label} {row['id']} · {len(layout['rooms'])} 房")
        compare.append(dict(id=row['id'], layout=layout['layout_hash'], trace=str(ep),
                            **annotate(ax,layout,read(ep),scale)))
    labels = [('前 5 秒路线','#177359','-'),('第一阶段','#15609b','-'),
              ('第二阶段','#ab461b','-'),('Boss 路线','#83505a',':'),
              ('through','#0086a2','-'),('window','#8150a5','-'),
              ('break','#b35d32','-'),('补给','#555d55','+')]
    handles = [Line2D([0],[0],color=c,ls=style,lw=2) if style!='+' else
               Line2D([0],[0],color=c,marker='+',ls='') for _,c,style in labels]
    fig.legend(handles,[name for name,_,_ in labels],
               loc='outside lower center',ncol=4,frameon=False)
    fig.suptitle(f'同种子父子两阶段对照 · {case} · 1.5 倍')
    fig.savefig(root/'parent_child_replay.png',dpi=150)
    fig.savefig(root/'parent_child_replay.svg')
    plt.close(fig)
    write(root/'parent_child_replay.json',dict(case=case, map_scale=scale, operation=child['operation'],
                                              pair=compare))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path)
    plot(parser.parse_args().run.resolve())
