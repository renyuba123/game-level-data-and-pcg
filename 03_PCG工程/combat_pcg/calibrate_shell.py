"""Run a reproducible shell battle calibration cohort without evolutionary selection."""
import argparse
from pathlib import Path

from full_pcg.common import read
from .battle_proxy import batch
from .battle_report import report
from . import godot_batch
from .protocol import default_combat
from .shell_depthmap import measure


ABILITIES = {'standard':{},'delayed':{'reaction_scale':1.2,'error_scale':1.2},
             'fast':{'reaction_scale':.8,'error_scale':.8}}
COHORT_MAPS = {'training': (1,2,6,84), 'heldout': (1001,1002), 'heldout_extension': (1003,1004)}


def run(package, out, cohort, ability, *, godot=None, legacy_proxy=False):
    if not legacy_proxy and godot is None:
        raise ValueError("Godot executable required for live calibration")
    layout=read(package)['layout']
    if layout['seed'] not in COHORT_MAPS[cohort] or (cohort=='training' and ability!='standard'):
        raise ValueError('Map or ability outside the registered calibration cohort')
    sampling=default_combat()['sampling']
    seeds=sampling['scenario_seeds' if cohort=='training' else 'heldout_seeds']
    from full_pcg.common import write
    write(out/'cohort.json',{'cohort':cohort,'seed':layout['seed'],'episode_seeds':seeds,
                           'layout_hash':layout['layout_hash'],'purpose':'development calibration'})
    spatial=out/'space'
    measure(layout,spatial)
    if not legacy_proxy:
        engine = out/ability/'godot'
        episodes = engine/'episodes'
        godot_batch.batch(godot, package, episodes, seeds=seeds, ability=ABILITIES[ability])
        return godot_batch.godot_report(package,spatial/'comparison.json',episodes,engine/'report.json')
    episodes=out/ability/'episodes'
    batch(package,episodes,seeds=seeds,ability=ABILITIES[ability])
    return report(package,spatial/'comparison.json',episodes,out/ability/'report.json','training' if cohort=='training' else 'heldout')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package',type=Path)
    parser.add_argument('out',type=Path)
    parser.add_argument('--cohort',choices=COHORT_MAPS,default='training')
    parser.add_argument('--ability',choices=ABILITIES,default='standard')
    parser.add_argument('--godot',type=Path,default=godot_batch.default_godot())
    parser.add_argument('--legacy-proxy',action='store_true')
    args=parser.parse_args()
    if args.godot is None and not args.legacy_proxy:
        parser.error('provide --godot or RATKING_GODOT_EXE')
    r=run(**vars(args))
    print(r['status'], r.get('available_scores',r.get('subscores')))
    if r['status']=='ERROR':raise SystemExit(2)
