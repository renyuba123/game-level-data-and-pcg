"""Paired Phase 3 mechanism calibration. Outputs stay outside formal search runs."""
import argparse
from pathlib import Path

from full_pcg.common import read, write
from .godot_batch import TUNING, batch, file_hash, read_result
from .godot_measurements import audit_resources


def summarize(raw, cfg, packet):
    audit_resources(raw, cfg, packet)
    if raw['combat'] != cfg:
        raise ValueError('recorded combat configuration differs from requested profile')
    events = raw['events']
    def first(kind, **fields):
        return next((e for e in events if e['kind'] == kind and
                     all(e['data'].get(k) == v for k,v in fields.items())), None)

    def at(event):
        return event['t'] if event is not None else None

    start = first('squeeze_start')
    end = first('squeeze_end', id=start['data']['id']) if start else None
    # Count the actual consecutive pressed inputs beginning at the first squeeze.
    held = 0
    if start:
        for command in raw['inputs'][start['step']-1:]:
            if not command['interact']:
                break
            held += 1
    return dict(case=raw['case_id'], outcome=raw['result'], seconds=raw['duration_s'],
                warning_s=at(first('attack_warning',by='large_boss')), death_s=at(first('death')),
                hit_s=at(first('hit',target='large_boss')), split_s=at(first('split')),
                phase2_hits=sum(e['kind']=='hit' and e['data'].get('phase')==2 and
                                e['data'].get('target')=='large_boss' for e in events),
                first_supply_s=at(first('pickup_end')),
                pickups=sum(e['kind']=='pickup_end' for e in events),
                final_hp=raw['frames'][-1]['hp'], squeeze_id=start['data']['id'] if start else None,
                squeeze_start_s=at(start), squeeze_end_s=at(end), first_hold_frames=held,
                physics_hz=raw['physics_hz'])


def experiment(godot, packages, out):
    ledger = {}
    for tier in TUNING:
        for seed in (6,84):
            package = packages / f'{seed}.json'
            packet = read(package)
            folder = out/tier/str(seed)
            manifest = batch(godot, package, folder, capture_controls=True, tuning=tier)
            cases = []
            for case_id in manifest['outcomes']:
                episode = read_result(folder/f'{case_id}.json', {'id':case_id},packet)
                cases.append(summarize(episode, manifest['recipe']['combat'], packet))
            ledger[f'{tier}/{seed}'] = dict(manifest_sha256=file_hash(folder/'manifest.json'),cases=cases)
    write(out/'comparison.json', ledger)
    return ledger


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('godot','packages','out'):
        parser.add_argument(name,type=Path)
    args = parser.parse_args()
    experiment(args.godot,args.packages,args.out)
