"""Pure scoring of explicit measurements. No LLM, randomness, engine or network."""
import json
import math
from pathlib import Path
from .contracts import ContractError, SCHEMA, canonical_hash, hash_field, number, require, validate_episode

GROUPS=('S','F','P','D')

def default_config():
    return json.loads(Path(__file__).with_name('scoring_config.json').read_text(encoding='utf-8'))

def validate_config(config):
    require(config.get('schema_version')==SCHEMA,'score config schema mismatch')
    require(type(config.get('frozen')) is bool,'frozen flag required')
    require(set(config['weights'])==set(GROUPS) and set(config['display_weights'])==set(GROUPS),'four objectives required')
    for group,weights in [*config['weights'].items(),('Q',config['display_weights'])]:
        require(bool(weights),f'{group}: empty weights')
        for w in weights.values():number(w,'weight',0,1)
        require(math.isclose(sum(weights.values()),1,abs_tol=1e-9),f'{group}: weights must sum to 1')
    names={m for group in config['weights'].values() for m in group}
    require(names==set(config['metrics']),'metric definitions/weights mismatch')
    require(config['minimum_episodes']>=1 and config['minimum_wins_for_diversity']>=2,'sample thresholds invalid')
    for seconds in config['failure_exposure_reference_s'].values():number(seconds,'failure exposure reference',1e-9)
    for spec in config['metrics'].values():
        require(spec['curve'] in ['increase','distance','band'],'unknown curve')
        if spec['curve']!='increase':number(spec['tolerance'],'tolerance',1e-9)
        if spec['curve']=='band':require(spec['domain'][0]<=spec['target'][0]<=spec['target'][1]<=spec['domain'][1],'invalid target')
    # A boolean is not evidence that calibration happened. Phase 3 must supply a lock.
    if config['frozen']:
        lock=config.get('calibration_lock',{})
        for key in ['baseline_hash','validation_report_hash','combat_config_hash']:hash_field(lock.get(key),key)
        require(isinstance(lock.get('git_commit'),str) and len(lock['git_commit'])==40,'calibration commit missing')
    return config

def quality(value,spec):
    number(value,'metric',*spec['domain'])
    if spec['curve']=='increase':return 100.*value
    distance=value if spec['curve']=='distance' else max(spec['target'][0]-value,0.,value-spec['target'][1])
    return 100.*max(0.,1.-distance/spec['tolerance'])

def wilson(wins,total):
    if total==0:return None
    z=1.959963984540054;p=wins/total;den=1+z*z/total
    center=(p+z*z/(2*total))/den;half=z*math.sqrt(p*(1-p)/total+z*z/(4*total*total))/den
    return [max(0.,center-half),min(1.,center+half)]

def observation_score(obs,name,config,missing):
    if obs is None:
        missing.append(name);return None
    spec=config['metrics'][name]
    require(obs.get('unit')==spec['unit'],name+': unit mismatch')
    require(isinstance(obs.get('evidence'),list) and bool(obs['evidence']),name+': evidence references required')
    require(isinstance(obs.get('sample_count'),int) and not isinstance(obs['sample_count'],bool) and obs['sample_count']>=0,name+': count required')
    if obs.get('state')=='no_opportunities':
        require(obs.get('value') is None and obs['sample_count']==0,name+': no-opportunity must be null/0')
        return 0. # Explicit lack of an opportunity, not a fabricated measured zero.
    require(obs.get('state')=='measured' and obs['sample_count']>0,name+': invalid measurement state')
    return quality(obs.get('value'),spec)

def score(measurements,config=None):
    config=default_config() if config is None else config
    base={'schema_version':SCHEMA,'protocol_id':config.get('protocol_id'),'scoring_config_hash':None,
          'measurement_hash':None,'status':'ERROR','reasons':[],'scores':None,'display_Q':None,'objectives':None,
          'formal_selection_allowed':False,'evidence_kind':measurements.get('evidence_kind'),'raw':measurements}
    try:
        validate_config(config);base['scoring_config_hash']=canonical_hash(config);base['measurement_hash']=canonical_hash(measurements)
        require(measurements.get('schema_version')==SCHEMA,'measurement schema mismatch')
        require(measurements.get('evidence_kind') in ['synthetic_test','simulation'],'evidence kind required')
        for key in ['layout_hash','combat_config_hash']:hash_field(measurements.get(key),key)
        checks=measurements.get('checks',{})
        require(set(checks)=={'geometry','topology','combat_rules'},'three check categories required')
        require(all(v in ['VALID','INVALID','UNCERTAIN','ERROR'] for v in checks.values()),'unknown check state')
        if 'ERROR' in checks.values():base['reasons']=['upstream_system_error'];return base
        if 'INVALID' in checks.values():base.update(status='INVALID',reasons=['confirmed_hard_constraint_violation']);return base
        episodes=measurements.get('episodes',[])
        require(isinstance(episodes,list),'episode list required')
        ids=set();scenarios=set();wins=0;coverage={'phase1':0.,'phase2':0.};reached={'phase1':0,'phase2':0}
        for e in episodes:
            validate_episode(e)
            require(e['episode_id'] not in ids,'duplicate episode');ids.add(e['episode_id'])
            scenario=(e['policy'],e['scenario_seed']);require(scenario not in scenarios,'duplicate policy/scenario');scenarios.add(scenario)
            require(e['layout_hash']==measurements['layout_hash'] and e['combat_config_hash']==measurements['combat_config_hash'],'mixed layout/combat versions')
            if e['outcome']=='error':base['reasons']=['episode_system_error'];return base
            wins+=int(e['outcome']=='victory')
            durations=e.get('phase_durations_s',{})
            require(set(durations)=={'phase1','phase2'},'phase durations missing')
            for value in durations.values():number(value,'phase duration',0)
            require(math.isclose(sum(durations.values()),e['duration_s'],abs_tol=1e-6),'phase durations do not sum to episode')
            # A split exactly at timeout has a real split event but zero phase-2 time.
            require(not durations['phase2'] or e['phase2_reached'],'positive phase 2 duration without split')
            require(e['outcome']!='victory' or (e['phase2_reached'] and durations['phase2']>0),'victory requires a nonzero second phase')
            for phase in coverage:
                entered=phase=='phase1' or e['phase2_reached'];completed=e['phase2_reached'] if phase=='phase1' else e['outcome']=='victory'
                reached[phase]+=int(entered)
                coverage[phase]+=float(completed) if completed else (min(1.,durations[phase]/config['failure_exposure_reference_s'][phase]) if entered else 0.)
        n=len(episodes);base['sample_summary']={'episodes':n,'wins':wins,'win_fraction':wins/n if n else None,
            'wilson95_descriptive':wilson(wins,n),'note':'descriptive binomial interval; fixed correlated policies are not a random human sample','phase_reached':reached}
        missing=[];subs={};space=measurements.get('space',{})
        for name in config['weights']['S']:subs[name]=observation_score(space.get(name),name,config,missing)
        subs['win_fraction']=quality(wins/n,config['metrics']['win_fraction']) if n else None
        if not n:missing.append('episodes')
        phase_details={}
        for group in ('F','P','D'):
            for name in config['weights'][group]:
                if name=='win_fraction':continue
                values=[];phase_details[name]={}
                for phase in ('phase1','phase2'):
                    if reached[phase]==0 or coverage[phase]==0:
                        q=0.;origin='unreached' if reached[phase]==0 else 'zero_duration'
                    else:
                        q=observation_score(measurements.get('phases',{}).get(phase,{}).get(name),name,config,missing);origin='observed'
                    # Every requested episode remains in the denominator. Early failed
                    # episodes cannot obtain full pressure by dying in one risky second.
                    exposure=coverage[phase]/n if n else 0.
                    phase_details[name][phase]={'quality_before_coverage':q,'coverage':exposure,'origin':origin}
                    values.append(None if q is None else q*exposure)
                subs[name]=None if None in values else sum(values)/2
        base['subscores']=subs;base['phase_details']=phase_details;base['missing_measurements']=sorted(set(missing))
        if missing:
            base.update(status='UNCERTAIN',reasons=['missing_required_measurements']);return base
        scores={g:sum(subs[k]*w for k,w in config['weights'][g].items()) for g in GROUPS}
        reasons=[]
        if n<config['minimum_episodes']:reasons.append('insufficient_episodes')
        if wins<config['minimum_wins_for_diversity']:reasons.append('insufficient_winning_routes')
        if 'UNCERTAIN' in checks.values():reasons.append('upstream_uncertain')
        base.update(status='UNCERTAIN' if reasons else 'VALID',reasons=reasons,scores=scores,
                    display_Q=sum(scores[g]*config['display_weights'][g] for g in GROUPS),objectives=[-scores[g] for g in GROUPS])
        base['formal_selection_allowed']=not reasons and config['frozen'] and measurements['evidence_kind']=='simulation'
        return base
    except (ContractError,KeyError,TypeError,ValueError,OverflowError) as exc:
        base.update(status='ERROR',reasons=[f'{type(exc).__name__}: {exc}'],scores=None,display_Q=None,objectives=None,formal_selection_allowed=False)
        # Invalid NaN/Infinity must not poison the error report's JSON serialization.
        try: json.dumps(base['raw'],allow_nan=False)
        except (ValueError,TypeError):base['raw']=None;base['raw_omitted_reason']='input not JSON-finite; retain original source file for diagnosis'
        return base
