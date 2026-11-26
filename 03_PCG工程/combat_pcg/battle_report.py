"""Recompute calibration observations from saved episodes, frames and real VGA tables."""
import argparse
import hashlib
import itertools
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

from full_pcg.common import read, write
from .tactical_routes import alternative_use
from .battle_audit import audit
from .contracts import SCHEMA, canonical_hash, require, validate_episode
from .protocol import default_combat, validate_combat
from .scoring import default_config, score


def cell(position, grid):
    return tuple(math.floor(x/grid) for x in position)


def episode_counts(record, phase, combat):
    episode = record['episode']
    split = next((e['t'] for e in episode['events'] if e['kind']=='split'), math.inf)
    start, end = (0, min(split,episode['duration_s'])) if phase==1 else (split,episode['duration_s'])
    frames = [f for f in record['frames'] if start<=f['t']<end]
    events = [e for e in episode['events'] if e['data'].get('phase')==phase]
    dt = combat['simulation']['tick_s']
    # A useful window must accommodate the whole aim+fire interval.
    used = span = 0
    for f in frames:
        if f['ready'] and f['can_relocate']:
            span+=1
        else:
            if span*dt+1e-9 >= combat['weapon']['aim_s']+combat['weapon']['fire_interval_s']: used+=span
            span=0
    if span*dt+1e-9 >= combat['weapon']['aim_s']+combat['weapon']['fire_interval_s']: used+=span
    warnings = [e for e in events if e['kind']=='attack_warning' and e['data']['perceived']]
    shortages = [e for e in events if e['kind']=='resource_empty']
    changed = [e for e in episode['events'] if e['kind'] in ('resource_empty','resource_restored')]
    resolved = sum(next((e['kind']=='resource_restored' for e in changed if e['sequence']>s['sequence']),False)
                   for s in shortages)
    finds=good_finds=0
    for target,field in [('boss','visible'),('stalker','stalker_visible')]:
        lost=None
        previously=False
        for f in frames:
            visible=f[field]
            if previously and not visible: lost=f['t']
            if visible and not previously and lost is not None:
                if f['t']-lost+1e-8 >= combat['score_sampling']['loss_of_target_min_s']:
                    finds+=1
                    good_finds+=int(f['can_relocate'] and f['reactable'].get(target,True))
                lost=None
            previously=visible
    return {
        'reaction_fraction':(sum(e['data']['margin_s'] is not None and e['data']['margin_s']>=0 for e in warnings),len(warnings)),
        'supply_fraction':(resolved,len(shortages)),
        'threat_fraction':(sum(f['threat'] for f in frames)*dt,len(frames)*dt),
        'shooting_window_fraction':(used*dt,len(frames)*dt),
        'reacquisition_fraction':(good_finds,finds),
        'action_risk_fraction':(sum(f['threat'] and f['action_risk'] for f in frames)*dt,
                                sum(f['action_risk'] for f in frames)*dt),
    }


def observation(value, count, evidence, unit='fraction'):
    return dict(value=value,sample_count=count,state='measured' if count else 'no_opportunities',
                unit=unit,evidence=evidence)


def combine(pairs):
    groups=defaultdict(list)
    for (policy,episode_id),(a,b) in pairs.items():
        require(0<=a<=b+1e-7,'invalid opportunity counts')
        if b: groups[policy].append(a/b)
    value=mean(mean(v) for v in groups.values()) if groups else None
    return {**observation(value,sum(map(len,groups.values())),[key[1] for key in pairs]),
            'episode_counts':{key[1]:list(ab) for key,ab in pairs.items()},
            'aggregation':'Within-episode fraction conditional on opportunities, then equal policy means.'}


def diversity(records, phase, packet, combat):
    winners = [r for r in records if r['episode']['outcome']=='victory']
    refs = [r['episode']['episode_id'] for r in records]
    if not winners:
        # No winning trajectory exists. Leave the pairwise comparison missing.
        return {m:observation(None,0,refs) for m in
                ['firing_position_diversity','alternative_use','destruction_use']}
    from shapely.geometry import Point,Polygon
    from shapely.ops import unary_union
    grid=combat['score_sampling']['grid_m']
    nav=unary_union([Polygon(t) for t in packet['navigation']['player']])
    x0,z0,x1,z1=nav.bounds
    cells={(x,z) for x in range(math.floor(x0/grid),math.ceil(x1/grid))
           for z in range(math.floor(z0/grid),math.ceil(z1/grid))
           if nav.covers(Point((x+.5)*grid,(z+.5)*grid))}
    paths=[]; firing=Counter(); used=opened=0
    for r in winners:
        route={cell(f['p'],grid) for f in r['frames'] if f['phase']==phase}
        paths.append(route)
        e=r['episode']['events']
        hits=Counter(cell(x['data']['position'],grid) for x in e if x['kind']=='hit' and x['data']['phase']==phase)
        hits=Counter({k:v for k,v in hits.items() if k in cells})
        for k,v in hits.items():firing[k]+=v/hits.total()
        for x in e:
            if x['kind']=='portal_open' and x['data']['phase']==phase:
                opened+=1
                is_new=any(g['id']==x['data']['id'] and g['kind']=='break' for g in packet['layout']['portals'])
                used+=is_new and any(y['kind']=='crossing' and y['data']['role']=='p' and
                          y['data']['id']==x['data']['id'] and y['sequence']>x['sequence'] for y in e)
    out={'destruction_use':observation(used/opened if opened else None,opened,refs)}
    if firing:
        entropy=-sum((v/firing.total())*math.log(v/firing.total()) for v in firing.values())
        out['firing_position_diversity']=observation(math.exp(entropy)/len(cells),len(firing),refs)
    else:out['firing_position_diversity']=observation(None,0,refs)
    distances=[len(a^b)/len(a|b) for a,b in itertools.combinations(paths,2) if a|b]
    if distances:out['route_difference']=observation(mean(distances),len(distances),refs)
    num,den=alternative_use(packet,winners,phase,combat)
    out['alternative_use']={**observation(num/den if den else None,den,refs),'used_pairs':num,'eligible_pairs':den}
    return out


def report(package, space_path, episodes_dir, out, cohort='training'):
    packet,space=read(package),read(space_path)
    layout=packet['layout']; config=default_config(); combat=default_combat()
    validate_combat(combat)
    require(space['layout_hash']==layout['layout_hash'],'space/Layout mismatch')
    require(space['source_dxf_sha256']==layout['source_dxf_sha256'],'reference DXF mismatch')
    samples=combat['sampling']; seeds=samples['scenario_seeds' if cohort=='training' else 'heldout_seeds']
    manifest=read(episodes_dir/'manifest.json');recipe=manifest['recipe']
    require(manifest['complete'] and recipe['package_hash']==packet['package_hash'],'unfinished or wrong episode batch')
    require(recipe['scenario_seeds']==seeds and recipe['policies']==samples['policies'],'cohort mismatch')
    records=[]; hashes={}
    for policy,seed in itertools.product(samples['policies'],seeds):
        fname=episodes_dir/f'{policy}_{seed}.json'
        rec=read(fname); e=validate_episode(rec['episode'])
        require(e['event_protocol']=='shell-battle/1' and e['policy']==policy and e['scenario_seed']==seed,'wrong cohort')
        require(e['package_hash']==packet['package_hash'] and e['window_config_hash']==packet['window_config_hash'],'stale navigation or portal configuration')
        require(e['layout_hash']==layout['layout_hash'],'episode/Layout mismatch')
        require(e['combat_config_hash']==canonical_hash({'combat':{**combat,'window':packet['window']},'ability':rec['ability']}),'combat configuration changed')
        records.append(rec);hashes[fname.name]=hashlib.sha256(fname.read_bytes()).hexdigest()
    phases={}
    for phase in (1,2):
        groups=defaultdict(dict)
        for rec in records:
            e=rec['episode']; key=(e['policy'],e['episode_id'])
            for name,pair in episode_counts(rec,phase,combat).items():
                groups[name][key]=pair
        phases[f'phase{phase}']={**{k:combine(v) for k,v in groups.items()},**diversity(records,phase,packet,combat)}
    valid=layout['validation']['states']
    reach=all(len(valid[k]['rooms_reached'])==valid[k]['total'] for k in ('initial_player','all_open_player','all_open_boss'))
    violations=audit(packet,records,combat)
    measures=dict(schema_version=SCHEMA,evidence_kind='simulation',layout_hash=layout['layout_hash'],
        combat_config_hash=records[0]['episode']['combat_config_hash'],episodes=[r['episode'] for r in records],
        checks=dict(geometry='VALID' if layout['schema_version']==5 and packet['floor_faces'] else 'ERROR',
                    topology='VALID' if reach else 'INVALID',combat_rules='ERROR' if violations else 'UNCERTAIN'),
        phases=phases,space={k:observation(space[k],2,[str(space_path)],'baseline_scale') for k in ('global_distance','regional_distance')})
    result=score(measures)
    result['event_rule_violations']=violations
    result['available_scores']={g:sum(result['subscores'][k]*w for k,w in weights.items())
                              if all(result.get('subscores',{}).get(k) is not None for k in weights) else None
                              for g,weights in config['weights'].items()}
    result.update(batch_recipe_hash=canonical_hash(recipe),cohort=cohort,episode_sha256=hashes,space_file_sha256=hashlib.sha256(space_path.read_bytes()).hexdigest(),
                  skill_evidence='2D proxy; player experience not measured')
    write(out,result)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for argument in ['package','space_path','episodes_dir','out']:parser.add_argument(argument,type=Path)
    parser.add_argument('--cohort',choices=['training','heldout'],default='training')
    args=parser.parse_args()
    r=report(**vars(args))
    print(r['status'],r['available_scores'],r.get('sample_summary'))
    if r['status']=='ERROR':raise SystemExit(2)
