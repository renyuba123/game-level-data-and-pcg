"""Resume independent experimental branches without changing genomes or fitness."""
import argparse, os, pickle, subprocess, sys, time
import numpy as np
from pymoo.core.mixed import MixedVariableGA, MixedVariableSampling
from pymoo.operators.survival.rank_and_crowding import RankAndCrowding
from common import WORK, ROOT, read_json, write_json, digest
from evaluator import Evaluator
# Import into __main__ too: old checkpoints refer to __main__.LayoutProblem.
from search import LayoutProblem, checkpoint

BASE=WORK/'runs/search_v1'

def row(seed,method,generation,records):
    valid=[r for r in records if r['valid']]
    return {'seed':seed,'method':method,'generation':generation,'evaluations':len(records),
        'valid':len(valid),'minimum_objectives':np.min([r['objectives'] for r in valid],axis=0).tolist() if valid else None,
        'keys':[r['key'] for r in records]}

def branch(seed,method):
    evaluator=Evaluator(400)
    spec=read_json(BASE/'spec.json')
    if evaluator.recipe!=spec['recipe'] or digest(WORK/'search.py')!=spec['search_implementation']:
        raise RuntimeError('Experimental implementation changed; refusing resume')
    directory=BASE/f'{method}_{seed}'
    directory.mkdir(parents=True,exist_ok=True)
    private=directory/'branch_history.json'
    history=read_json(private) if private.exists() else [h for h in read_json(BASE/'history.json') if h['seed']==seed and h['method']==method]
    completed={h['generation'] for h in history}
    problem=LayoutProblem(evaluator,directory)
    if method=='evolution':
        cp=directory/'checkpoint.pkl'
        if cp.exists():
            with cp.open('rb') as f: algorithm=pickle.load(f)
            problem=algorithm.problem
            if problem.generation not in completed and problem.records:
                history.append(row(seed,method,problem.generation,problem.records)); completed.add(problem.generation)
        else:
            algorithm=MixedVariableGA(pop_size=spec['population'],survival=RankAndCrowding())
            algorithm.setup(problem,termination=('n_gen',spec['generations']),seed=seed,verbose=False)
    for generation in range(1,spec['generations']+1):
        if generation in completed: continue
        if (BASE/'STOP').exists(): return
        problem.generation=generation
        write_json(directory/'branch_status.json',{'state':'running','seed':seed,'method':method,'generation':generation})
        if method=='evolution':
            algorithm.next(); checkpoint(cp,algorithm); records=problem.records
        else:
            population=MixedVariableSampling().do(problem,spec['population'],random_state=np.random.default_rng(seed*100000+generation))
            records=evaluator.batch(population.get('X'),directory/f'generation_{generation:03d}',generation)
        history.append(row(seed,method,generation,records)); write_json(private,history)
    write_json(directory/'branch_status.json',{'state':'complete','seed':seed,'method':method,'generation':spec['generations']})

def parent():
    if (BASE/'STOP').exists(): raise RuntimeError('Remove STOP after original launcher exits')
    evaluator=Evaluator(400)
    assert evaluator.recipe==read_json(BASE/'spec.json')['recipe']
    write_json(WORK/'process.json',{'pid':os.getpid(),'mode':'parallel_resume'})
    jobs=[]
    history=read_json(BASE/'history.json')
    for seed in [11,29,47]:
        for method in ['evolution','random']:
            if len([h for h in history if h['seed']==seed and h['method']==method])<20:
                jobs.append((seed,method))
    active={}; attempts={j:0 for j in jobs}; failures=[]
    while jobs or active:
        while jobs and len(active)<3:
            job=jobs.pop(0); seed,method=job
            directory=BASE/f'{method}_{seed}'; directory.mkdir(parents=True,exist_ok=True)
            log=(directory/'parallel_console.log').open('a',encoding='utf-8')
            env=dict(os.environ); env['RATKING_WORKERS']='4' if attempts[job]==0 else '2'
            p=subprocess.Popen([sys.executable,__file__,'--branch',str(seed),method],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            active[job]=(p,log); attempts[job]+=1
        for job,(p,log) in list(active.items()):
            if p.poll() is None: continue
            log.close(); del active[job]
            if p.returncode and attempts[job]<3: jobs.append(job)
            elif p.returncode: failures.append({'branch':list(job),'exit_code':p.returncode})
        # Only this parent merges the global ledger; workers own separate files.
        merged={(h['seed'],h['method'],h['generation']):h for h in history}
        for private in BASE.glob('*/branch_history.json'):
            for h in read_json(private): merged[h['seed'],h['method'],h['generation']]=h
        history=sorted(merged.values(),key=lambda h:(h['seed'],h['method'],h['generation']))
        write_json(BASE/'history.json',history)
        states=[]
        for job in active:
            path=BASE/f'{job[1]}_{job[0]}'/'branch_status.json'
            if path.exists(): states.append(read_json(path))
        write_json(WORK/'status.json',{'state':'running_parallel','run':'search_v1','completed_batches':len(history),'total_batches':120,'active':states,'failures':failures})
        if (BASE/'STOP').exists():
            jobs=[]
        time.sleep(5)
    write_json(BASE/'parallel_execution.json',{'driver_sha256':digest(WORK/'parallel_resume.py'),'attempts':{str(k):v for k,v in attempts.items()},'failures':failures,
        'note':'Scheduling only; original spec, fitness, seeds, RNG and per-branch evaluation budgets unchanged'})
    state='search_complete' if len(history)==120 and not failures else 'stopped_or_failed'
    write_json(WORK/'status.json',{'state':state,'run':'search_v1','completed_batches':len(history),'total_batches':120,'failures':failures})
    if state!='search_complete': raise RuntimeError(state)

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--branch',nargs=2); args=parser.parse_args()
    if args.branch: branch(int(args.branch[0]),args.branch[1])
    else: parent()
