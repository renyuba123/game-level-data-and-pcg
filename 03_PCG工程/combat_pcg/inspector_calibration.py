"""Run and resume the preregistered Inspector balance calibration on Godot."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import math
from pathlib import Path
from statistics import mean, median

import numpy as np
from scipy.stats import qmc
from shapely import affinity, geometry

from full_pcg.common import ROOT, digest, read, write
from .contracts import require
from .godot_batch import batch, file_hash, godot_report, verify_replay
from .shell_depthmap import measure


RANGES = (
    ('Boss Speed', 'boss', 'speed_mps', 2, 3.2, .05),
    ('Boss Attack Warning', 'boss', 'attack_warning_s', .45, 1, .05),
    ('Player Aim Speed', 'player', 'aim_speed_mps', 1.75, 3.25, .05),
    ('Stalker Speed', 'stalker', 'speed_mps', 1.8, 3, .05),
    ('Stalker Damage', 'stalker', 'damage', 15, 30, 1),
    ('Weapon Damage', 'weapon', 'damage', 35, 55, 1),
    ('Weapon Fire Interval', 'weapon', 'fire_interval_s', .25, .40, .01),
    ('Weapon Aim Seconds', 'weapon', 'aim_s', .20, .45, .05),
    ('Weapon Reload Seconds', 'weapon', 'reload_s', 1.50, 2.50, .05),
    ('Supply Pickup Seconds', 'supplies', 'pickup_s', .20, .50, .05),
)
RUN_ID = 'inspector_balance_177_v1'
OBJECTIVES = ('F', 'P', 'D')
POLICIES = ('output', 'occlusion', 'supply')
DEVELOPMENT = (177, 6, 84)
INDEPENDENT = (1101, 1102, 1103, 1104)


def settings(combat):
    return {label: combat[group][key] for label, group, key, *_ in RANGES}


def snap(value, lo, hi, step):
    return round(max(lo, min(hi, lo + round((value-lo)/step)*step)), 4)


def sample_candidates(baseline):
    samples = qmc.LatinHypercube(d=len(RANGES), seed=177).random(24)
    result = {'baseline': baseline}
    for idx, sample in enumerate(samples, 1):
        candidate = deepcopy(baseline)
        for x, (_, group, key, lo, hi, step) in zip(sample, RANGES, strict=True):
            candidate[group][key] = snap(lo + float(x)*(hi-lo), lo, hi, step)
        result[f'grid_{idx:02}'] = candidate
    return result


def neighbours(candidates, leaders):
    result = {}
    for rank, parent_id in enumerate(leaders):
        parent = candidates[parent_id]
        for sign in (-1, 1):
            candidate = deepcopy(parent)
            for index in (rank, rank + 4, (rank + 8) % len(RANGES)):
                _, group, key, lo, hi, step = RANGES[index]
                value = parent[group][key]
                trial = snap(value + sign * 2 * step, lo, hi, step)
                if trial == value:
                    trial = snap(value - sign * step, lo, hi, step)
                candidate[group][key] = trial
            result[f'near_{rank+1}_{sign:+d}'] = candidate
    return result


def complete(row):
    return row['outcomes'].get('victory', 0) >= 2 and all(row['scores'][k] is not None for k in OBJECTIVES)


def wins(rows):
    return sum(r['outcomes'].get('victory', 0) for r in rows)


def passes(rows):
    return (wins(rows)*10 >= 7*sum(r['episodes'] for r in rows)
            and all(complete(row) and not row['violations'] for row in rows))


def rank_key(rows, combat, baseline):
    distance = sum(abs(combat[g][k]-baseline[g][k])/(hi-lo) for _, g, k, lo, hi, _ in RANGES)
    if passes(rows):
        values = [row['scores'][k] for row in rows for k in OBJECTIVES]
        return (1, min(values), mean(values), -distance)
    legal = not any(r['violations'] for r in rows)
    return (0 if legal else -1, wins(rows), sum(r['phase2'] for r in rows),
            -mean(r['median_final_boss_hp'] for r in rows), -distance)


def crossing_frames(positions, segment):
    """Find steps that cross the finite opening rather than its infinite plane."""
    a, b = np.asarray(segment)
    edge = b-a
    side = (positions[:, 0]-a[0])*edge[1] - (positions[:, 1]-a[1])*edge[0]
    indices = np.flatnonzero((side[:-1] < 0) != (side[1:] < 0))
    t = side[indices]/(side[indices]-side[indices+1])
    hit = positions[indices]+t[:, None]*(positions[indices+1]-positions[indices])
    interior = ((hit-a) @ edge)/(edge @ edge)
    return indices[(interior > 1e-5) & (interior < 1-1e-5)] + 1


def audit_episode(ep, packet, combat, scale, walls):
    """Check rule witnesses in addition to the engine's own collision queries."""
    layout = packet['layout']
    frames = ep['frames']
    violations = []
    hp = combat['boss']['hp']
    threshold = hp*combat['stalker']['split_hp_fraction']
    last_shot = split = None
    supplies = {p['id']:p['position'] for p in layout['supplies']}
    for event in ep['events']:
        step = event['step']
        kind = event['kind']
        data = event['data']
        if kind == 'shot':
            last_shot = step
        elif kind == 'hit':
            if last_shot != step:
                violations.append('unpaired_hit')
            if data['target'] == 'large_boss':
                hp = max(threshold if split is None else 0, hp-combat['weapon']['damage'])
                if not math.isclose(hp, data['hp'], abs_tol=1e-6) or (split is not None and step <= split):
                    violations.append('invalid_damage')
        elif kind == 'split':
            if split is not None or not math.isclose(hp,threshold):
                violations.append('invalid_split')
            split = step
        elif kind == 'victory' and (split is None or step <= split or hp != 0):
            violations.append('invalid_victory')
        elif kind == 'pickup_end':
            point = frames[step-1]['p']
            center = [x*scale for x in supplies[data['id']]]
            if math.dist(point, center) > combat['supplies']['pickup_radius_m'] + 1e-5:
                violations.append('pickup_out_of_range')
            if math.dist(point, center) > 1e-6 and geometry.LineString([point,center]).relate_pattern(walls,'T********'):
                violations.append('pickup_through_static_wall')
    track = {k:np.asarray([f[k] for f in frames]) for k in ('b','p')}
    for gate in layout['portals']:
        kind = gate['kind']
        if kind == 'normal':
            continue
        segment = np.asarray(gate['segment'])*scale
        for role in ('b','p') if kind == 'break' else ('b',):
            for idx in crossing_frames(track[role], segment):
                if kind == 'window' or gate['id'] not in frames[idx-1]['opened']:
                    violations.append(f'closed_{kind}_crossing:{role}:{gate["id"]}')
    return sorted(set(violations))


def register(out, packet_dir, snapshot):
    from .scoring import default_config
    independent = []
    bindings = {}
    seen = set()
    for seed in (*DEVELOPMENT, *INDEPENDENT):
        path = packet_dir/f'{seed}.json'
        packet = read(path)
        if not packet.get('ok', True):
            bindings[str(seed)] = dict(failed=packet['reason'])
            continue
        layout_hash = packet['layout']['layout_hash']
        require(packet['layout']['seed']==seed, 'wrong package seed')
        require(layout_hash not in seen, 'duplicate layout across cohorts')
        seen.add(layout_hash)
        bindings[str(seed)] = dict(layout=layout_hash, sha256=file_hash(path))
        if seed in INDEPENDENT:
            independent.append(seed)
    require(all(str(s) in bindings and 'layout' in bindings[str(s)] for s in DEVELOPMENT),
            'development layout missing')
    require(len(independent)>=2, 'fewer than two valid independent layouts')
    record = dict(run_id=RUN_ID, snapshot=snapshot, ranges=RANGES, development=DEVELOPMENT,
                  independent=independent[:2], bindings=bindings, development_seeds=[0,1,2,3],
                  independent_seeds=[110,111,112,113], policy_variant='paced',
                  scoring_config_hash=digest(default_config()), official_requests=0,
                  screening_samples=24, local_samples=8)
    path = out/'registration.json'
    if path.exists():
        require(digest(read(path))==digest(record), 'registration changed, use a new run directory')
    else:
        write(path, record)
    return record


def evaluate(godot, out, packet_path, space, candidate_id, combat, scale, scenarios, series, *, trace=None):
    seed = int(packet_path.stem)
    folder = out/series/str(seed)/candidate_id
    episodes = folder/'episodes'
    manifest = batch(godot, packet_path, episodes, policies=POLICIES, seeds=scenarios,
                     capture_controls=True, decision_variant='paced', combat=combat, layout_scale=scale, trace=trace)
    report_path = folder/'score.json'
    scores = godot_report(packet_path, space, episodes, report_path)
    require(scores['status'] not in ('ERROR','INVALID'), f'audit or scoring failure: {report_path}')
    cases = [read(episodes/f'{key}.json') for key in manifest['outcomes']]
    packet = read(packet_path)
    walls = affinity.scale(geometry.shape(packet['layout']['walls']), xfact=scale, yfact=scale, origin=(0,0))
    violations = {ep['case_id']: issues for ep in cases
                  if (issues := audit_episode(ep, packet, combat, scale, walls))}
    results = Counter(ep['result'] for ep in cases)
    deaths = Counter()
    by_policy = {}
    for ep in cases:
        policy = ep['case_id'].rsplit('_', 1)[0]
        by_policy.setdefault(policy, Counter())[ep['result']] += 1
        if ep['result'] == 'death':
            causes = [e['data']['by'] for e in ep['events'] if e['kind']=='grab']
            deaths[causes[-1] if causes else 'unknown'] += 1
    row = dict(candidate=candidate_id, seed=seed, scale=scale, episodes=len(cases), outcomes=results,
               phase2=sum(ep['phase']==2 for ep in cases), deaths=deaths, by_policy=by_policy,
               median_final_boss_hp=median(ep['frames'][-1]['hp'] for ep in cases),
               scores=scores['available_scores'], missing=scores.get('missing_measurements', []),
               violations=violations,
               report=str(report_path), manifest_sha256=file_hash(episodes/'manifest.json'))
    write(folder/'summary.json', row)
    print(series, seed, candidate_id, dict(results), 'phase2', row['phase2'], flush=True)
    return row


def run(godot, packet_dir, snapshot_path, out, workers, prepare_only=False):
    require(workers >= 1, 'workers must be positive')
    snapshot = read(snapshot_path)
    require(snapshot['seed']==177 and snapshot['layout_scale']==1.5, 'expected Seed 177, Map Size 1.5')
    require(snapshot['combat']['supplies']['pickup_radius_m']==1.25, 'pickup fallback not resolved')
    registration = register(out, packet_dir, snapshot)
    code = ('inspector_calibration.py', 'godot_batch.py', 'godot_measurements.py', 'battle_report.py',
            'tactical_routes.py', 'scoring.py', 'shell_depthmap.py')
    identity = dict(godot_sha256=file_hash(godot),
                    implementation={name:file_hash(ROOT/'combat_pcg'/name) for name in code})
    identity_path = out/'implementation.json'
    if identity_path.exists():
        require(read(identity_path)==identity, 'implementation changed, use a new run directory')
    elif not prepare_only:
        write(identity_path, identity)
    baseline = deepcopy(snapshot['combat'])
    baseline['protocol_id'] = RUN_ID
    configs = sample_candidates(baseline)
    all_seeds = (*DEVELOPMENT, *registration['independent'])
    packages = {seed:packet_dir/f'{seed}.json' for seed in all_seeds}
    spaces = {seed:out/'space'/str(seed)/'comparison.json' for seed in all_seeds}

    with ThreadPoolExecutor(max_workers=workers) as executor:
        pending = []
        for seed in all_seeds:
            if spaces[seed].exists():
                spatial = read(spaces[seed])
                require(spatial['layout_hash']==registration['bindings'][str(seed)]['layout'],
                        'stale spatial measurement')
            else:
                pending.append(executor.submit(measure, read(packages[seed])['layout'], spaces[seed].parent))
        for task in pending:
            task.result()
        if prepare_only:
            return None

        def cohort(series, ids, maps, scale=1.5, independent=False):
            scenarios = registration['independent_seeds' if independent else 'development_seeds']
            tasks = [(id, executor.submit(evaluate, godot, out, packages[seed], spaces[seed], id,
                                           configs[id], scale, scenarios, series))
                     for id in ids for seed in maps]
            rows = {id: [] for id in ids}
            for id, job in tasks:
                rows[id].append(job.result())
            return rows

        def ordered(rows, exclude=()):
            return sorted((id for id in rows if id not in exclude),
                          key=lambda id: rank_key(rows[id], configs[id], baseline), reverse=True)

        write(out/'screening_configurations.json', configs)
        screening = cohort('screening', list(configs), [177])
        local = neighbours(configs, ordered(screening)[:4])
        configs.update(local)
        write(out/'candidate_configurations.json', configs)
        screening.update(cohort('screening', list(local), [177]))
        cross_ids = ['baseline', *ordered(screening, exclude=('baseline',))[:4]]
        cross = cohort('development', cross_ids, DEVELOPMENT[1:])
        dev = {id:screening[id]+cross[id] for id in cross_ids}
        recommendation = ordered(dev)[0]
        comparison = list(dict.fromkeys(['baseline', recommendation]))
        write(out/'locked_candidate.json', dict(id=recommendation, combat=configs[recommendation],
                                               development=dev[recommendation],
                                               passed_development=passes(dev[recommendation])))
        held = cohort('independent', comparison, registration['independent'], independent=True)
        sensitivity = cohort('scale_1', comparison, [177], scale=1.0)

    replays = {}
    for outcome in ('victory', 'death', 'timeout'):
        for row in dev[recommendation]:
            folder = Path(row['report']).parent/'episodes'
            manifest = read(folder/'manifest.json')
            case = next((key for key, value in manifest['outcomes'].items() if value['result']==outcome), None)
            if case:
                replays[outcome] = verify_replay(godot, packages[row['seed']], folder/f'{case}.json',
                                                 out/'replay'/outcome)
                break
    result = dict(run_id=RUN_ID, baseline=settings(baseline), candidate_settings=settings(configs[recommendation]),
                  candidate=recommendation, recommended=passes(dev[recommendation]) and passes(held[recommendation]),
                  screening=screening, development=dev, independent=held, sensitivity=sensitivity,
                  replays=replays, official_requests=0)
    write(out/'results.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ('godot','packet_dir','snapshot_path','out'):
        parser.add_argument(arg, type=lambda value:Path(value).resolve())
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--prepare-only', action='store_true')
    result = run(**vars(parser.parse_args()))
    if result:
        print(result['candidate'], result['recommended'], result['candidate_settings'], flush=True)
