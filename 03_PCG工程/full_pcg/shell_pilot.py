"""Run the preregistered draft two-generation shell layout pilot."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
import math
from pathlib import Path
import random

import networkx as nx

from combat_pcg.contracts import require
from combat_pcg.godot_batch import file_hash
from combat_pcg.inspector_calibration import evaluate
from combat_pcg.shell_depthmap import measure
from full_pcg.common import digest, read, write
from full_pcg.pilot_contract import register
from full_pcg.shell_genome import graph, initial, mutate, realize


ARMS = ('genetic','random')
OBJECTIVES = ('S','F','P','D')


def eligible(row):
    return row['status']=='COMPLETE_DRAFT' and all(row['scores'][k] is not None for k in OBJECTIVES)


def dominates(a,b):
    x = [a['scores'][k] for k in OBJECTIVES]
    y = [b['scores'][k] for k in OBJECTIVES]
    return all(i>=j for i,j in zip(x,y)) and any(i>j for i,j in zip(x,y))


def fronts(rows):
    remaining = sorted((r for r in rows if eligible(r)),key=lambda r:r['id'])
    while remaining:
        front = [r for r in remaining if not any(dominates(other,r) for other in remaining)]
        yield front
        ids = {r['id'] for r in front}
        remaining = [r for r in remaining if r['id'] not in ids]


def crowding(rows):
    distances = dict.fromkeys((r['id'] for r in rows),0.0)
    for axis in OBJECTIVES:
        ordered = sorted(rows,key=lambda r:(r['scores'][axis],r['id']))
        lo, hi = (ordered[i]['scores'][axis] for i in (0,-1))
        if hi == lo:
            continue
        distances[ordered[0]['id']] = distances[ordered[-1]['id']] = math.inf
        for before,row,after in zip(ordered,ordered[1:],ordered[2:]):
            distances[row['id']] += (after['scores'][axis]-before['scores'][axis])/(hi-lo)
    return distances


def select(rows, count):
    unique = {}
    for r in rows:
        if r['status'] in ('COMPLETE_DRAFT','UNCERTAIN'):
            unique.setdefault(r['layout_hash'],r)
    ranked = []
    for front in fronts(unique.values()):
        distances = crowding(front)
        ranked.extend(sorted(front,key=lambda r:(-distances[r['id']],r['id'])))
    fallback = sorted((r for r in unique.values() if not eligible(r)),key=lambda r:r['id'])
    return (ranked+fallback)[:count]


def pareto(rows):
    unique = {r['layout_hash']:r for r in rows if eligible(r)}
    return [r['id'] for r in next(fronts(unique.values()),[])]


def plan_round(spec, arm, gen, previous, records, packets):
    for slot in range(spec['population']):
        ident = f'initial-{slot:02}' if not gen else f'{arm}-{gen}-{slot:02}'
        rng = random.Random(f"{spec['optimizer_seed']}:{arm}:{gen}:{slot}")
        row = dict(id=ident, parents=[], operation=None, failures=[], genome=None, layout_hash=None,
                   topology_changed=None, fallback_parent=False)
        packet = None
        try:
            if not gen or arm=='random':
                seed = spec['initial_seeds'][slot] if not gen else rng.randrange(2000,2**31)
                require(seed not in spec['excluded_layout_seeds'], 'heldout seed leaked')
                row.update(seed=seed, operation=['initial' if not gen else 'random_sample',seed])
                row['genome'] = initial(seed)
                packet = realize(row['genome'])
            else:
                survivors = [records[id] for id in previous]
                scored = [r for r in survivors if eligible(r)]
                pool = scored if len(scored)>=2 else survivors
                require(bool(pool), 'no legal parent; genetic trial cannot continue')
                parent = pool[slot % len(pool)]
                p = packets[parent['layout_hash']]['layout']
                child, packet, operation, failures = mutate(parent['genome'],p,rng,spec['max_repairs'],
                                                            prefer_topology=slot%2==0)
                row.update(seed=p['seed'], parents=[parent['id']], genome=child, operation=operation,
                           failures=failures, fallback_parent=len(scored)<2)
                if packet:
                    row['topology_changed'] = not nx.is_isomorphic(graph(p),graph(packet['layout']))
        except ValueError as exc:
            row['failures'].append(dict(issue=str(exc)))
        if packet:
            row['layout_hash'] = packet['layout']['layout_hash']
        yield row, packet


def load_packet(out, key):
    paths = list((out/'packages'/key).glob('*.json'))
    require(len(paths)==1, 'missing saved packet: '+key)
    return read(paths[0])


def evaluate_packet(root, godot, packet, spec, *, depthmap=None, trace=None):
    layout = packet['layout']
    key = layout['layout_hash']
    seed = layout['seed']
    path = root/'packages'/key/f'{seed}.json'
    spatial = root/'space'/key/'comparison.json'
    evdir = root/'evaluation'/str(seed)/key
    proof = evdir/'certificate.json'
    if path.exists():
        require(read(path)['package_hash']==packet['package_hash'], 'packet mismatch in cache')
    else:
        write(path,packet)
    if proof.exists():
        cert = read(proof)
        for file, expected in cert['files'].items():
            artifact = (root/file).resolve()
            require(artifact.is_relative_to(root.resolve()) and file_hash(artifact)==expected,
                    'corrupt evidence: '+file)
        with trace("certificate_hit", layout_hash=key) if trace else nullcontext():
            return read(evdir/'summary.json')
    if not spatial.exists():
        runtime = {"cli": depthmap} if depthmap is not None else {}
        with trace("spatial", layout_hash=key) if trace else nullcontext():
            measure(layout,spatial.parent,grid=spec['grid'],trace=trace,**runtime)
    episodes = evdir/'episodes'/'manifest.json'
    batch_hit = episodes.is_file() and read(episodes)['complete']
    stage = "godot_batch_hit" if batch_hit else "godot_evidence"
    with trace(stage, layout_hash=key, episodes=12) if trace else nullcontext():
        row = evaluate(godot,root,path,spatial,key,spec['combat'],spec['layout_scale'],
                       spec['scenario_seeds'],'evaluation',trace=trace)
    manifest = read(evdir/'episodes'/'manifest.json')
    files = {p.relative_to(root).as_posix():file_hash(p) for p in
             (path,spatial,evdir/'score.json',evdir/'summary.json',evdir/'episodes'/'manifest.json')}
    files.update({(evdir/'episodes'/f'{case}.json').relative_to(root).as_posix():sha
                  for case,sha in manifest['episode_hashes'].items()})
    write(proof,dict(files=files))
    return row


def run(config, out, godot, depthmap, workers, through, verify):
    from combat_pcg.shell_depthmap import analyze

    require(Path(analyze.__globals__['CLI']).resolve()==depthmap.resolve(),
            'registered Depthmap path differs from active evaluator')
    spec, registration = register(config,out,godot,depthmap)
    require(1<=workers<=8 and 0<=through<=spec['reproductions'], 'runner limits exceeded')
    packets, summaries = {}, {}
    history = {arm:{} for arm in ARMS}
    population = {arm:[] for arm in ARMS}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for gen in range(through+1):
            for arm in ARMS:
                path = out/arm/f'generation_{gen:02}.json'
                existing = read(path) if path.exists() else None
                if not existing or verify:
                    futures, rows = {}, []
                    for row, packet in plan_round(spec,arm,gen,population[arm],history[arm],packets):
                        key = row['layout_hash']
                        row['shared_evaluation'] = key is not None and (key in summaries or key in futures)
                        if key and key not in packets:
                            packets[key] = packet
                        if key and key not in summaries and key not in futures:
                            futures[key] = pool.submit(evaluate_packet,out,godot,packet,spec)
                        rows.append(row)
                    for key, task in futures.items():
                        summaries[key] = task.result()
                    for row in rows:
                        summary = summaries.get(row['layout_hash'])
                        if not summary:
                            row['status']='INVALID'
                            continue
                        row.update(scores=summary['scores'], outcomes=summary['outcomes'],
                                   phase2=summary['phase2'], missing=summary['missing'],
                                   violations=summary['violations'])
                        row['status'] = ('INVALID' if summary['violations'] else
                                         'UNCERTAIN' if summary['missing'] or
                                         summary['outcomes'].get('victory',0)<2 else 'COMPLETE_DRAFT')
                    parents = [history[arm][id] for id in population[arm]]
                    combined = parents+rows
                    survivors = select(combined,spec['population'])
                    archive = list(history[arm].values())+rows
                    fresh = dict(generation=gen, arm=arm, requests=rows, survivors=[r['id'] for r in survivors],
                                 current_pareto=pareto(survivors), cumulative_pareto=pareto(archive),
                                 scored_count=sum(eligible(r) for r in survivors),
                                 selection_fallback=any(not eligible(r) for r in survivors))
                    if verify:
                        require(existing is not None and digest(fresh)==digest(existing),
                                f'fixed-seed rebuild differs: {path}')
                    else:
                        write(path,fresh)
                    existing = fresh
                for row in existing['requests']:
                    key = row['layout_hash']
                    if key and key not in packets:
                        packets[key] = load_packet(out,key)
                    if key and key not in summaries:
                        summaries[key] = evaluate_packet(out,godot,packets[key],spec)
                    history[arm][row['id']] = row
                population[arm] = existing['survivors']
                print(arm, gen, 'requests',len(existing['requests']),
                      'complete draft survivors',existing['scored_count'],flush=True)
    if through==spec['reproductions']:
        overview = dict(budget=registration['total_requests'], official_requests=0,
                        evaluated_layouts=len(summaries), battles=sum(r['episodes'] for r in summaries.values()),
                        topology_changes={arm:sum(r['topology_changed'] is True and r['status']!='INVALID'
                                                  for r in history[arm].values()) for arm in ARMS})
        if verify:
            require(read(out/'overview.json')==overview, 'overview differs from rebuilt trial')
            write(out/'reproducibility.json',dict(passed=True, verified_generations=[0,1,2], **overview))
        else:
            write(out/'overview.json',overview)
        print(overview,flush=True)


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ('config','out','godot','depthmap'):
        parser.add_argument(arg,type=lambda value:Path(value).resolve())
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--through',type=int,default=2,help='last generation to commit before stopping')
    parser.add_argument('--verify',action='store_true',help='rebuild from generation 0 and compare to committed data')
    run(**vars(parser.parse_args()))
