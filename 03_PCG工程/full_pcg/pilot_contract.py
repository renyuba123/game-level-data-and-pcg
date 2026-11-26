"""Preregister the draft shell pilot. Formal experiment admission is separate."""
import argparse
from importlib.metadata import version
from pathlib import Path
import platform
import subprocess

from combat_pcg.contracts import require
from combat_pcg.godot_batch import file_hash
from combat_pcg.protocol import formal_preflight, validate_combat
from combat_pcg.scoring import default_config
from full_pcg.common import ROOT, digest, read, write


def register(config, output, godot, depthmap):
    spec = read(config)
    require(spec['schema']=='shell-layout-pilot/1' and spec['purpose']=='development_only',
            'draft pilot configuration required')
    combat = spec['combat']
    validate_combat(combat)
    scoring = default_config()
    gate = formal_preflight(combat, scoring)
    require(not combat['frozen'] and not scoring['frozen'] and not gate['allowed'],
            'pilot requires the draft protocol')
    require((spec['layout_scale'], spec['population'], spec['reproductions'], spec['grid'],
             spec['max_repairs'])==(1.5,8,2,400,8), 'wrong approved pilot scope')
    seeds = spec['initial_seeds']
    require(len(set(seeds))==len(seeds)==spec['population'] and
            not set(seeds) & set(spec['excluded_layout_seeds']), 'initial cohort overlaps heldout layouts')
    require(spec['policies']==combat['sampling']['policies'] and
            spec['scenario_seeds']==combat['sampling']['scenario_seeds'] and
            spec['decision_variant']=='paced', 'wrong pilot scenario protocol')
    files = ('data/shell_source_v2.json', 'data/reviewed_shell_partitions.json',
             'configs/full_pcg_v2.json', 'project.godot')
    sources = [ROOT/f for f in files]
    for folder, glob in (('full_pcg','*.py'), ('combat_pcg','*.py'), ('full_pcg/godot','*.gd')):
        sources.extend(f for f in (ROOT/folder).glob(glob) if not f.name.startswith('test_'))
    registration = dict(
        run_id=spec['run_id'], config_sha256=file_hash(config), combat_hash=digest(combat),
        scoring_hash=digest(scoring), official_requests=0, requests_per_arm=24, total_requests=48,
        maximum_episodes=576, initial_seeds=seeds, formal_preflight=gate,
        tools=dict(godot=file_hash(godot), depthmap=file_hash(depthmap), python=platform.python_version(),
                   packages={lib:version(lib) for lib in ('numpy','shapely','networkx','scipy','ezdxf')}),
        implementation={f.relative_to(ROOT).as_posix():file_hash(f) for f in sorted(set(sources))},
    )
    path = output/'registration.json'
    if path.exists():
        require(read(path)==registration, 'pilot inputs changed, use a new run directory')
    else:
        write(path, registration)
        write(output/'config_snapshot.json', spec)
    require(read(output/'config_snapshot.json')==spec, 'pilot snapshot mismatch')
    return spec, registration


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ('config','output','godot','depthmap'):
        parser.add_argument(arg, type=lambda value:Path(value).resolve())
    _, record = register(**vars(parser.parse_args()))
    print('Registered', record['run_id'], record['total_requests'], 'draft requests')
