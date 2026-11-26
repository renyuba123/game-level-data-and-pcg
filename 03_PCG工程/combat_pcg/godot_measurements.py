"""Derive the existing score observations from versioned Godot evidence."""
from collections import defaultdict
from itertools import pairwise

from .battle_report import combine, diversity
from .contracts import require


def world_route_packet(packet, scale):
    """Match Godot's world X/Z frame while retaining the fixed metric grid."""
    if scale == 1.0:
        return packet

    def point(xz):
        return [value * scale for value in xz]

    return {
        **packet,
        'navigation': {'player': [[point(p) for p in tri] for tri in packet['navigation']['player']]},
        'links': [dict(link, points=[point(p) for p in link['points']]) for link in packet['links']],
        'layout': dict(packet['layout'], portals=[dict(gate, segment=[point(p) for p in gate['segment']])
                                                for gate in packet['layout']['portals']]),
    }


def pairs_by_phase(raw, combat):
    dt = 1/raw['physics_hz']
    frames = raw['frames']
    targets = ('boss','stalker')
    totals = {f'phase{i}':defaultdict(lambda: [0,0]) for i in (1,2)}
    aim_duration = combat['weapon']['aim_s']+combat['weapon']['fire_interval_s']
    lost_min = combat['score_sampling']['loss_of_target_min_s']
    visible = dict.fromkeys(targets,False)
    threatened = dict.fromkeys(targets,False)
    lost_at = dict.fromkeys(targets,None)
    resource_phase = None
    window = 0
    window_phase = None

    def flush_window():
        if window_phase and window*dt+1e-9>=aim_duration:
            totals[window_phase]['shooting_window_fraction'][0] += window*dt

    for index,frame in enumerate(frames):
        phase = f"phase{frame['phase']}"
        obs = totals[phase]
        threatened_now = []
        for target in targets:
            was_visible=visible[target]
            visible[target]=frame[f'{target}_visible']
            eta=frame[f'{target}_eta_s']
            active=eta is not None and eta<=frame['threat_horizon_s']
            threatened_now.append(active)
            escape=frame['escape_s']
            reactable=escape is not None and (not active or eta+1e-9>=frame['reaction_s']+escape)
            detected=active and visible[target]
            if detected and not threatened[target]:
                obs['reaction_fraction'][1]+=1
                obs['reaction_fraction'][0]+=reactable
            threatened[target]=detected
            if was_visible and not visible[target]:
                lost_at[target]=index
            if visible[target] and not was_visible and lost_at[target] is not None:
                if (index-lost_at[target])*dt+1e-9>=lost_min:
                    obs['reacquisition_fraction'][1]+=1
                    obs['reacquisition_fraction'][0]+=reactable
                lost_at[target]=None
        threat=any(threatened_now)
        obs['threat_fraction'][0]+=dt*threat
        obs['threat_fraction'][1]+=dt
        obs['shooting_window_fraction'][1]+=dt
        ready=frame['ready'] and frame['escape_s'] is not None
        if not ready or phase!=window_phase:
            flush_window()
            window=0
        window_phase=phase
        window+=int(ready)
        if frame['action_risk']:
            obs['action_risk_fraction'][1]+=dt
            obs['action_risk_fraction'][0]+=dt*threat
        if frame['loaded']+frame['reserve']==0 and frame['hp']>0 and resource_phase is None:
            resource_phase=phase
            obs['supply_fraction'][1]+=1
        elif frame['loaded']+frame['reserve']>0 and resource_phase is not None:
            totals[resource_phase]['supply_fraction'][0]+=1
            resource_phase=None
    flush_window()
    fields=('reaction_fraction','supply_fraction','threat_fraction','shooting_window_fraction',
            'reacquisition_fraction','action_risk_fraction')
    return {phase:{name:tuple(obs[name]) for name in fields} for phase,obs in totals.items()}


def _winning_trajectory(raw, episode, packet):
    from shapely.geometry import LineString
    frames = raw['frames']
    events = []
    for event in raw['events']:
        frame=frames[max(0,min(len(frames)-1,event['step']-1))]
        data={**event['data'],'phase':event['data'].get('phase',frame['phase'])}
        if event['kind']=='hit':
            if data.get('target')!='large_boss':
                continue
            data['position']=frame['p']
        events.append(dict(event,data=data))
    breaks={p['id']:LineString(p['segment']) for p in packet['layout']['portals'] if p['kind']=='break'}
    for i,(before,after) in enumerate(pairwise(frames),2):
        if before['p']==after['p']:
            continue
        motion=LineString((before['p'],after['p']))
        for gate in set(before['opened']) & breaks.keys():
            if motion.crosses(breaks[gate]):
                events.append(dict(step=i,kind='crossing',data=dict(id=gate,role='p',phase=after['phase'])))
    for i,event in enumerate(sorted(events,key=lambda e:e['step'])):
        event['sequence']=i
    events.sort(key=lambda e:e['sequence'])
    return dict(episode={**episode,'events':events},frames=frames)


def phases_from_godot(raw_episodes, episodes, packet, combat):
    if any(r.get('telemetry')!='godot-score/1' for r in raw_episodes):
        return {}  # Historical batches have outcomes but lack scoring telemetry.
    grouped=defaultdict(lambda:defaultdict(dict))
    winners=[]
    for raw,episode in zip(raw_episodes,episodes,strict=True):
        key=(episode['policy'],episode['episode_id'])
        for phase,fields in pairs_by_phase(raw,combat).items():
            for name,pair in fields.items():
                grouped[phase][name][key]=pair
        if episode['outcome']=='victory':
            winners.append(_winning_trajectory(raw,episode,packet))
    output={}
    for phase,fields in grouped.items():
        output[phase]={name:combine(pairs) for name,pairs in fields.items()}
        if winners:
            output[phase].update(diversity(winners,int(phase[-1]),packet,combat))
    return output


def audit_resources(raw, combat, packet):
    supplies={p['id'] for p in packet['layout']['supplies']}
    picked=set()
    ammo=int(combat['supplies']['initial_rounds_including_magazine'])
    for event in raw['events']:
        if event['kind']=='shot':
            ammo-=1
            require(ammo>=0,'engine shot without obtainable ammo')
        elif event['kind']=='pickup_end':
            id=event['data']['id']
            require(id in supplies and id not in picked,'invalid or repeated Godot pickup')
            picked.add(id)
            ammo+=combat['supplies']['rounds_per_pack']
    final=raw['frames'][-1]
    require(final['loaded']+final['reserve']==ammo,'Godot terminal ammo accounting mismatch')
    if raw['result']=='victory':
        require(final['phase']==2 and final['hp']==0,'Godot victory lacks second-stage kill')
