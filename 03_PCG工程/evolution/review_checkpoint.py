import os
import numpy as np
from pymoo.util.nds.non_dominated_sorting import NonDominatedSorting
from common import ROOT, WORK, GODOT, read_json, write_json, command
from evaluator import Evaluator
from simulation import run

def main():
    out=WORK/'runs/search_v1/seed11_review'
    out.mkdir(parents=True,exist_ok=True)
    history=[h for h in read_json(WORK/'runs/search_v1/history.json') if h['seed']==11 and h['method']=='evolution']
    assert len(history)==20
    records=[read_json(WORK/'cache'/key/'evaluation.json') for h in history for key in h['keys']]
    feasible=[r for r in records if r['valid'] and r['constraint']<=0]
    values=np.array([r['objectives'] for r in feasible])
    front=NonDominatedSorting().do(values,only_non_dominated_front=True)
    scores=values[front]
    normalized=(scores-scores.min(axis=0))/np.maximum(np.ptp(scores,axis=0),1e-9)
    chosen=feasible[front[np.argmin(normalized.mean(axis=1))]]
    generation=next(h['generation'] for h in history if chosen['key'] in h['keys'])
    write_json(out/'selection.json',{'key':chosen['key'],'generation':generation,'coarse_objectives':chosen['objectives'],
        'selection':'Equal-weight normalized objectives within feasible first-seed Pareto front; does not alter fitness.'})
    print('Selected',chosen['key'],chosen['objectives'],flush=True)
    os.environ['RATKING_WORKERS']='1'
    fine=Evaluator(200).batch([chosen['genes']],out/'fine',generation)[0]
    if not fine['valid'] or fine['constraint']>0:
        write_json(out/'result.json',{'passed':False,'stage':'fine_review','evaluation':fine}); return
    heldout=run(read_json(WORK/'cache'/fine['key']/'layout.json'),heldout=True)
    candidate={'seed':chosen['seed'],'genes':chosen['genes'],'generation':generation,'evaluation':{
        'key':chosen['key'],'grid':400,'objectives':chosen['objectives'],
        'fine_review':{'key':fine['key'],'grid':200,'valid':fine['valid'],'constraint':fine['constraint'],'objectives':fine['objectives']},
        'heldout':heldout,'status':'Interim seed 11 candidate; acceptance pending; full search ongoing'}}
    path=ROOT/'data/evolution/reviewed_seed11.json'
    write_json(path,candidate)
    if heldout['early_catch_fraction']>0 or heldout['escape_fraction']==0 or heldout['stuck_fraction']>0:
        write_json(out/'result.json',{'passed':False,'stage':'heldout','heldout':heldout}); return
    try:
        command([GODOT,'--headless','--path',ROOT,'--script','res://scripts/review_candidate.gd','--','res://data/evolution/reviewed_seed11.json'],out/'godot.log',180)
    except RuntimeError as error:
        write_json(out/'result.json',{'passed':False,'stage':'godot','error':str(error)}); return
    candidate['evaluation']['status']='Interim seed 11: 200-unit, heldout proxy and 9 actual gates passed; full search ongoing'
    write_json(path,candidate)
    write_json(out/'result.json',{'passed':True,'candidate':str(path),'fine_objectives':fine['objectives'],
        'heldout':heldout,'scope':'One completed seed; provisional preview, not final search conclusion'})
    print('REVIEW PASSED',fine['objectives'],flush=True)

if __name__=='__main__': main()
