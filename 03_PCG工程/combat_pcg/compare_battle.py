"""Evaluate shared Python and Godot geometry probes and compare discrete events."""
import argparse
from pathlib import Path

from .battle_sensing import RayField
from .event_order import resolve_step
from .protocol import default_combat
from full_pcg.common import read, write


def probes(package, out):
    packet=read(package)
    layout=packet['layout']
    window=packet['window']
    field=RayField(layout,window)
    cases=[]
    for state in ('initial','all_open'):
        opened={p['id'] for p in layout['portals'] if p['kind'] in ('break','through')} if state=='all_open' else set()
        for p in layout['portals']:
            for offset in (-.32,0.,.34):
                center=tuple(a+offset*b for a,b in zip(p['center'],p['tangent']))
                start=tuple(a-.35*b for a,b in zip(center,p['normal']))
                end=tuple(a+.35*b for a,b in zip(center,p['normal']))
                for height in (.35,1.15,2.10):
                    cases.append(dict(id=len(cases),portal=p['id'],kind=p['kind'],start=start,end=end,
                        height=height,state=state,expected=field.clear(start,end,opened,height=height)))
    write(out/'cases.json',dict(package=str(package),package_hash=packet['package_hash'],probes=cases,
                                 output=str(out/'godot.json')))


def compare(out, episode_path):
    spec=read(out/'cases.json')
    tested=read(out/'godot.json')
    if tested['package_hash']!=spec['package_hash']: raise ValueError('Probe package changed')
    ids={r['id']:r['clear'] for r in tested['results']}
    if len(ids)!=len(spec['probes']):raise ValueError('Incomplete Godot probes')
    mismatches=[{**c,'actual':ids[c['id']]} for c in spec['probes'] if ids[c['id']]!=c['expected']]
    result=dict(probe_count=len(ids),mismatches=mismatches)
    if episode_path:
        e=read(episode_path)
        if e['package_hash']!=spec['package_hash']:raise ValueError('Combat episode package changed')
        cfg=default_combat()
        state=dict(boss_hp=cfg['boss']['hp'],split=False,player_alive=True,
                   loaded=cfg['weapon']['magazine'],reserve=cfg['supplies']['initial_rounds_including_magazine']-
                   cfg['weapon']['magazine'])
        comparisons=[]
        hit_index=0
        for ev in e['events']:
            d=ev['data'];kind=ev['kind'];inputs={};expected=[]
            if kind=='hit':
                # Subsequent direct damage is the explicit mechanism probe input.
                # Read expected HP from the engine log, not the calculation.
                inputs=dict(kind='hit',line_of_sight=True,damage=(cfg['weapon']['damage'],1000,500)[hit_index])
                hit_index+=1
                expected=['hit']
                if not state['split'] and d['hp']==cfg['boss']['hp']*.5:expected.append('split')
                if d['hp']==0:expected.append('victory')
            elif kind=='shot':inputs=dict(kind='shot');expected=['shot']
            elif kind=='portal_open':inputs=dict(kind=kind,by=d['by'],id=d['id']);expected=[kind]
            elif kind=='pickup_end':inputs=dict(kind=kind,rounds=cfg['supplies']['rounds_per_pack']);expected=[kind]
            if not inputs:continue
            state,events,_=resolve_step(state,[inputs],cfg)
            key={'hit':'boss_hp','shot':'loaded','pickup_end':'reserve'}.get(kind)
            obs_key='hp' if kind=='hit' else key
            valid=events==expected and (key is None or state[key]==d[obs_key])
            comparisons.append(dict(event=kind,pass_exact=valid,expected=expected,python=events))
        result['mechanism_steps']=comparisons
        result['mechanism_scope']='Input-controlled event probes with direct damage after first physical shot. Reload timing and autonomous movement are not paired.'
    result['passed']=not mismatches and all(x['pass_exact'] for x in result.get('mechanism_steps',[]))
    write(out/'comparison.json',result)
    print(result['probe_count'],len(mismatches),result['passed'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('prepare');a.add_argument('package',type=Path);a.add_argument('out',type=Path)
    b=sub.add_parser('compare');b.add_argument('out',type=Path);b.add_argument('--episode',type=Path)
    args=p.parse_args()
    if args.command=='prepare':probes(args.package,args.out)
    else:compare(args.out,args.episode)
