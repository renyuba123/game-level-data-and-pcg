import argparse,collections
from .common import ROOT,read,write,digest
from .topology import sample,classify
from .geometry import generate
from .visualize import preview
from .validation import validate
def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['generate']);p.add_argument('--config',default='configs/full_pcg_v2.json');p.add_argument('--seeds',default='1:100');args=p.parse_args()
    config=read(ROOT/args.config);a,b=map(int,args.seeds.split(':'))
    implementation={p.name:digest(p.read_text(encoding='utf-8')) for p in (ROOT/'full_pcg').glob('*.py')}
    revision=digest({'config':config,'implementation':implementation})[:12]
    out=ROOT/'full_pcg_output/generation_audit'/revision;rows=[];valid=[]
    write(out/'manifest.json',{'config':config,'implementation':implementation,'seeds':[a,b]})
    for seed in range(a,b+1):
        genome=sample(seed,config);layout,qa=generate(genome,config)
        if qa['ok']:
            physical=validate(layout,config);qa['physical']=physical;qa['ok']=physical['ok'];qa['issues']+=physical['issues']
        row={'seed':seed,'validation':qa,'rooms':len(genome['rooms']),'genome':genome,'layout':layout}
        write(out/f'seed_{seed:04d}.json',row);rows.append(row)
        if qa['ok']:valid.append(genome)
        if seed<=12:preview(layout,out/f'seed_{seed:04d}.png',f'Seed {seed} | rooms {len(genome["rooms"])} | valid {qa["ok"]}',config['canvas'])
        print(seed,qa['ok'],qa['issues'],flush=True)
    types=classify(valid);summary={'count':len(rows),'valid':len(valid),'room_counts':sorted(set(len(g['rooms']) for g in valid)),
        'exact_unlabelled_topologies':len(set(types)),'cycles':sorted(set(r['layout']['topology']['cycles'] for r in rows if r['validation']['ok'])),
        'failures':dict(collections.Counter(x for r in rows for x in r['validation']['issues'])),'note':'Development audit; baseline escape-time calibration, obstacle placement and Godot validation still pending'}
    write(out/'summary.json',summary);write(ROOT/'full_pcg_output/latest_audit.json',{'path':str(out),'summary':summary});print(summary)
if __name__=='__main__':main()
