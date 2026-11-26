"""Schedule live Godot combat from Python and validate the resulting evidence."""
import argparse
from contextlib import nullcontext
import hashlib
from itertools import product
import math
import os
from pathlib import Path
import subprocess
import time

from full_pcg.common import ROOT, read, write
from .contracts import SCHEMA, canonical_hash, require, validate_episode
from .protocol import default_combat

BACKEND = 'combat-batch/godot-1'
SCRIPTS = ('run_combat_batch.gd', 'auto_combat_level.gd', 'replay_combat_level.gd',
           'combat_level.gd', 'layout_decoder.gd')


def file_hash(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def default_godot():
    value = os.environ.get('RATKING_GODOT_EXE')
    return Path(value) if value else None


def read_result(path, case, package):
    result = read(path)
    require(result['schema']==BACKEND and result['case_id']==case['id'], 'wrong engine episode')
    require(result['package_hash']==package['package_hash'], 'wrong episode package')
    require(result['layout_hash']==package['layout']['layout_hash'], 'wrong episode layout')
    require(result['result'] in ('victory','death','timeout'), 'missing terminal result')
    require(bool(result['frames']), 'missing engine frames')
    require(result['events'][-1]['kind']==result['result'], 'terminal event mismatch')
    require(math.isclose(result['duration_s'],len(result['frames'])/result['physics_hz']), 'engine time mismatch')
    return result


DECISION_VARIANTS = (
    'reference', 'crossing', 'reengage', 'combined', 'mobile', 'paced',
    'paced_supply_v1', 'paced_exit_v1', 'paced_tactics_v1',
)

TUNING = {
    'baseline': (4.2, 2.0, 0.6),
    'moderate': (3.8, 2.8, 0.9),
    'relaxed': (3.5, 3.0, 1.2),
}


def batch(godot, package, out, policies=None, seeds=None, ability=None, capture_controls=False,
          tuning=None, decision_variant='reference', *, combat=None, layout_scale=1.0, trace=None):
    godot,package,out = map(lambda p: Path(p).resolve(),(godot,package,out))
    require(godot.is_file(), f'Godot executable missing: {godot}')
    packet = read(package)
    require(packet['layout']['schema_version']==5,'Godot batch requires Layout v5')
    require(math.isfinite(layout_scale) and layout_scale > 0, 'invalid layout scale')
    require(combat is None or tuning is None, 'use either a resolved combat configuration or a preset')
    cfg = default_combat() if combat is None else combat
    if tuning is not None:
        boss_speed, aim_speed, warning = TUNING[tuning]
        cfg['boss'].update(speed_mps=boss_speed, attack_warning_s=warning)
        cfg['player']['aim_speed_mps'] = aim_speed
        cfg['protocol_id'] = f'combat_v3_mechanism_tuning_1_{tuning}'
    ability = ability or {}
    policies = list(policies if policies is not None else cfg['sampling']['policies'])
    seeds = list(seeds if seeds is not None else cfg['sampling']['scenario_seeds'])
    require(bool(policies) and set(policies)<=set(cfg['sampling']['policies']) and len(set(policies))==len(policies),
            'invalid player policies')
    require(bool(seeds) and all(type(s) is int and 0<=s<2**31 for s in seeds) and len(set(seeds))==len(seeds),
            'invalid scenario seeds')
    require(set(ability)<= {'reaction_scale','error_scale'} and all(math.isfinite(v) and v>=0 for v in ability.values()),
            'invalid ability controls')
    require(decision_variant in DECISION_VARIANTS, 'unknown decision variant')
    cases = [dict(decision_variant=decision_variant,id=f'{policy}_{seed}',policy=policy,seed=seed,ability=ability,
                  output=str(out/f'{policy}_{seed}.json')) for policy,seed in product(policies,seeds)]
    godot_root = ROOT/'full_pcg'/'godot'
    recipe = dict(backend=BACKEND, package_hash=packet['package_hash'], package_file_sha256=file_hash(package),
                  godot_sha256=file_hash(godot), combat=cfg, ability=ability, policies=policies,
                  scenario_seeds=seeds, capture_controls=capture_controls,
                  implementation={name:file_hash(godot_root/name) for name in SCRIPTS},
                  project_settings_sha256=file_hash(ROOT/'project.godot'))
    recipe['decision_variant'] = decision_variant
    if layout_scale != 1.0:
        recipe['layout_scale'] = layout_scale
    manifest = out/'manifest.json'
    if manifest.exists():
        saved = read(manifest)
        require(saved['recipe']==recipe,'use a new evidence directory for a changed engine/configuration')
        if saved['complete']:
            for case in cases:
                path = Path(case['output'])
                require(file_hash(path)==saved['episode_hashes'][case['id']], 'stored episode hash mismatch')
                result = read_result(path,case,packet)
                require(result.get('layout_scale', 1.0)==layout_scale and result['combat']==cfg,
                        'stored episode combat configuration mismatch')
            return saved
    else:
        require(not out.exists() or not list(out.glob('*.json')),'evidence directory has no engine manifest')
    write(manifest,dict(recipe=recipe,complete=False))
    spec = out/'request.json'
    write(spec,dict(schema=BACKEND, package=str(package), package_hash=packet['package_hash'],
                    combat=cfg, cases=cases, capture_controls=capture_controls, layout_scale=layout_scale))
    env = dict(os.environ, RATKING_COMBAT_BATCH=str(spec),
               APPDATA=str(out/'appdata'), XDG_DATA_HOME=str(out/'appdata'))
    started = time.perf_counter()
    logfile = out/'godot.log'
    invocation = trace("godot", scheduled_episodes=len(cases), log=str(logfile)) if trace else nullcontext()
    with logfile.open('w', encoding='utf8') as log, invocation:
        subprocess.run([str(godot),'--headless','--fixed-fps','60',
                        '--script','res://full_pcg/godot/run_combat_batch.gd'],
                       cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env=env,
                       timeout=max(30, len(cases)*30),check=True)
    content = dict(recipe=recipe,complete=True,wall_seconds=time.perf_counter()-started,
                   episode_hashes={},outcomes={})
    for case in cases:
        path = Path(case['output'])
        result = read_result(path,case,packet)
        require(result.get('layout_scale', 1.0)==layout_scale, 'wrong engine layout scale')
        require(result['combat']==cfg, 'wrong engine combat configuration')
        content['episode_hashes'][case['id']] = file_hash(path)
        content['outcomes'][case['id']] = dict(result=result['result'],duration_s=result['duration_s'],
                                               phase=result['phase'],physics_hz=result['physics_hz'])
    require(recipe['package_file_sha256']==file_hash(package),'layout package changed during battle')
    write(manifest,content)
    return content


def verify_replay(godot, package, episode_path, out):
    from .paired_replay import run_godot

    packet = read(package)
    episode = read(episode_path)
    require(episode['schema']==BACKEND and episode['package_hash']==packet['package_hash'],
            'the replay requires its original engine episode and package')
    require(len(episode['inputs'])==len(episode['frames']) and bool(episode['inputs']),
            'record an episode with --capture-controls')
    out = Path(out).resolve()
    request = out/'case.json'
    trace = out/'replay.json'
    write(request,dict(schema='combat-replay/1', package=str(Path(package).resolve()),
                       package_hash=packet['package_hash'], output=str(trace),
                       combat=episode.get('combat',{}), dt=1/episode['physics_hz'], native_boss=True,
                       score_telemetry=episode.get('telemetry')=='godot-score/1',
                       layout_scale=episode.get('layout_scale',1.0),
                       reaction_scale=episode.get('ability',{}).get('reaction_scale',1.0),
                       start_player=packet['layout']['spawn']['position'],
                       start_boss=packet['layout']['boss']['position'], inputs=episode['inputs']))
    run_godot(Path(godot),request,out/'godot.log')
    replay = read(trace)
    summary = dict(case=episode['case_id'], source_sha256=file_hash(Path(episode_path)),
                   replay_sha256=file_hash(trace), frames=len(episode['frames']),
                   physics_hz=episode['physics_hz'], result=episode['result'],
                   same_events=episode['events']==replay['events'],
                   same_frames=episode['frames']==replay['frames'],
                   same_result=episode['result']==replay['result'])
    write(out/'comparison.json',summary)
    require(all(summary[k] for k in ('same_events','same_frames','same_result')),
            f'replay differs: {out}')
    return summary


def godot_report(package, space_path, episodes_dir, out):
    """Score available evidence; prediction-only metrics require new calibration."""
    from .battle_report import observation
    from .godot_measurements import audit_resources, phases_from_godot, world_route_packet
    from .scoring import default_config, score

    packet = read(package)
    space = read(space_path)
    manifest = read(episodes_dir/'manifest.json')
    recipe = manifest['recipe']
    require(manifest['complete'] and recipe['backend']==BACKEND,'incomplete Godot batch')
    layout = packet['layout']
    require(space['layout_hash']==layout['layout_hash'] and space['source_dxf_sha256']==layout['source_dxf_sha256'],
            'space/Layout mismatch')
    battle_hash = canonical_hash(recipe)
    episodes=[]
    engine_episodes=[]
    for policy,seed in product(recipe['policies'],recipe['scenario_seeds']):
        id = f'{policy}_{seed}'
        path = episodes_dir/f'{id}.json'
        require(file_hash(path)==manifest['episode_hashes'][id],'engine episode hash mismatch')
        raw = read_result(path, {'id':id},packet)
        audit_resources(raw,recipe['combat'],packet)
        engine_episodes.append(raw)
        split = next((e['t'] for e in raw['events'] if e['kind']=='split'),None)
        duration = raw['duration_s']
        first = split if split is not None else duration
        # The engine accumulates float time, so allow round-off at its last tick.
        events = [dict(e,t=min(e['t'],duration)) for e in raw['events']]
        episode=dict(schema_version=SCHEMA,layout_schema_version=5,episode_id=id,individual_id=layout['layout_hash'][:16],
                     layout_hash=layout['layout_hash'],combat_config_hash=battle_hash,policy=policy,scenario_seed=seed,
                     outcome=raw['result'],duration_s=duration,phase2_reached=split is not None,
                     phase_durations_s=dict(phase1=min(first,duration),phase2=max(0,duration-first)),events=events)
        episodes.append(validate_episode(episode))
    validated = layout['validation']['states']
    reach = all(len(validated[k]['rooms_reached'])==validated[k]['total']
                for k in ('initial_player','all_open_player','all_open_boss'))
    route_packet = world_route_packet(packet, recipe.get('layout_scale', 1.0))
    measurement = dict(schema_version=SCHEMA,evidence_kind='simulation',layout_hash=layout['layout_hash'],
                       combat_config_hash=battle_hash,
                       checks=dict(geometry='VALID' if packet['floor_faces'] else 'ERROR',
                                   topology='VALID' if reach else 'INVALID',combat_rules='UNCERTAIN'),
                       episodes=episodes,phases=phases_from_godot(engine_episodes,episodes,route_packet,recipe['combat']),
                       space={k:observation(space[k],2,[str(space_path)],'baseline_scale')
                              for k in ('global_distance','regional_distance')})
    config = default_config()
    result = score(measurement,config)
    subscores = result.get('subscores',{})
    result['available_scores'] = {
        group:sum(subscores[name]*weight for name,weight in weights.items())
        if all(subscores.get(name) is not None for name in weights) else None
        for group,weights in config['weights'].items()
    }
    result.update(backend=BACKEND,batch_recipe_hash=battle_hash,
                  episode_sha256=manifest['episode_hashes'],space_file_sha256=file_hash(space_path))
    write(out,result)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('godot',type=Path)
    parser.add_argument('package',type=Path)
    parser.add_argument('out',type=Path)
    parser.add_argument('--policies',nargs='+')
    parser.add_argument('--seeds',nargs='+',type=int)
    parser.add_argument('--decision-variant',default='reference',choices=['reference','crossing','reengage','combined','mobile','paced'])
    parser.add_argument('--tuning',choices=TUNING)
    parser.add_argument('--capture-controls',action='store_true')
    result=batch(**vars(parser.parse_args()))
    print(result['outcomes'],flush=True)
