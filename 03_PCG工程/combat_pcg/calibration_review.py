"""Recompute diagnostics under predeclared perturbations of the draft score only."""
import argparse
from copy import deepcopy
from pathlib import Path
from .scoring import default_config, score
from .counterexamples import run as calculator_counterexamples
from full_pcg.common import read, write


def perturbations():
    draft=default_config()
    variants={'nominal':draft}
    for factor in (.8,1.2):
        timing=deepcopy(draft)
        for phase in timing['failure_exposure_reference_s']:
            timing['failure_exposure_reference_s'][phase]*=factor
        variants[f'exposure_{factor}']=timing
        tolerance=deepcopy(draft)
        for item in tolerance['metrics'].values():
            if 'tolerance' in item:item['tolerance']*=factor
        variants[f'tolerance_{factor}']=tolerance
        for goal in draft['weights']:
            for metric in draft['weights'][goal]:
                weights=deepcopy(draft)
                group=weights['weights'][goal]
                group[metric]*=factor
                total=sum(group.values())
                weights['weights'][goal]={k:v/total for k,v in group.items()}
                variants[f'{metric}_weight_{factor}']=weights
    return variants


def dimensions(row, config):
    return {g:sum(row['subscores'][name]*w for name,w in weights.items())
              if all(row.get('subscores',{}).get(name) is not None for name in weights) else None
              for g,weights in config['weights'].items()}


def review(paths, out):
    variants=perturbations()
    evidence=[]
    for path in paths:
        source=read(path)
        inputs=source['raw']
        rows={}
        for test,config in variants.items():
            row=score(inputs,config)
            if row['status']=='ERROR':raise ValueError(row['reasons'])
            rows[test]=dimensions(row,config)
        if rows['nominal']!=source['available_scores']:raise ValueError('Nominal replay drift: '+str(path))
        ranges={}
        for goal in source['available_scores']:
            numbers=[r[goal] for r in rows.values() if r[goal] is not None]
            ranges[goal]=[min(numbers),max(numbers)] if numbers else None
        outcomes={}
        for event in inputs['episodes']:
            key=event['policy']
            counts=outcomes.setdefault(key,dict(victory=0,death=0,timeout=0,phase2=0))
            counts[event['outcome']]+=1
            counts['phase2']+=int(event['phase2_reached'])
        evidence.append(dict(source=str(path),cohort=source['cohort'],measurement_hash=source['measurement_hash'],
                             outcomes=outcomes,ranges=ranges,variants=rows,status=source['status']))
    simulations=[e for e in evidence if e['cohort']=='training']
    flips={}
    for goal in 'SFPD':
        flips[goal]=[]
        for i,a in enumerate(simulations):
            for b in simulations[i+1:]:
                x,y=a['variants']['nominal'][goal],b['variants']['nominal'][goal]
                if x is None or y is None or x==y:continue
                for name in variants:
                    u,v=a['variants'][name][goal],b['variants'][name][goal]
                    if (x-y)*(u-v)<0:flips[goal].append(dict(a=a['source'],b=b['source'],variant=name))
    write(out,dict(perturbation='One factor at a time, score-only +/-20%; no changes to persisted config',
                   comparisons=evidence,ranking_reversals=flips,calculator_counterexamples=calculator_counterexamples()))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('out',type=Path)
    p.add_argument('paths',type=Path,nargs='+')
    a=p.parse_args()
    review(a.paths,a.out)
