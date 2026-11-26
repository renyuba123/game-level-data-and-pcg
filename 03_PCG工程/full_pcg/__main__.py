import argparse,collections
import json
from pathlib import Path

from .common import ROOT,read,write,digest
from .topology import sample,classify
from .geometry import generate
from .visualize import preview
from .validation import validate
def main():
    parser = argparse.ArgumentParser(description="Generate or evaluate Rat King PCG layouts")
    commands = parser.add_subparsers(dest="command", required=True)
    geometry = commands.add_parser("generate", help="Run the existing anchor-layout generation audit")
    geometry.add_argument("--config", default="configs/full_pcg_v2.json")
    geometry.add_argument("--seeds", default="1:100")
    local = commands.add_parser("experiment", help="Run a local single-parent engineering experiment")
    local.add_argument("--config", type=Path, required=True)
    local.add_argument("--resume", action="store_true")
    local.add_argument("--through", type=int, help="Stop after committing this generation")
    local.add_argument("--workers", type=int, help="Override parallel evaluation workers")
    check = commands.add_parser("verify", help="Rebuild and verify the committed single-parent archive")
    check.add_argument("--run", type=Path, required=True)
    check.add_argument("--compare", type=Path, help="Verify a second archive and compare deterministic results")
    check.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()

    if args.command == "generate":
        generate_audit(args.config, args.seeds)
        return
    from .single_parent.experiment import experiment, verify_run

    try:
        if args.command == "experiment":
            result = experiment(args.config, args.resume, args.through, args.workers)
        else:
            result = verify_run(args.run, args.workers)
            if args.compare:
                other = verify_run(args.compare, args.workers)
                differences = [key for key, value in result.items()
                               if key not in ("run_id", "workers") and other.get(key) != value]
                result["comparison"] = {"run_id": other["run_id"], "matches": not differences,
                                        "differing_fields": differences}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if args.command == "verify" and args.compare and differences:
            raise SystemExit(1)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"full_pcg {args.command}: {exc}\n")


def generate_audit(config_path, seeds):
    config=read(ROOT/config_path);a,b=map(int,seeds.split(':'))
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
