"""Reconstruct replay controls from a verified Python calibration trace."""
import argparse
from collections import Counter
from hashlib import sha256
import math
import os
import subprocess
from pathlib import Path

from full_pcg.common import read, write
from .battle_proxy import simulate
from .contracts import canonical_hash
from .protocol import default_combat


def file_hash(path):
    return sha256(path.read_bytes()).hexdigest()


def command_stream(record, dt):
    episode, frames = record['episode'], record['frames']
    spawn = episode['events'][0]['data']
    p, b = spawn['player'], spawn['boss']
    by_step = {}
    for event in episode['events']:
        by_step.setdefault(event['step'], []).append(event)
    held = set()
    reload = False
    inputs = []
    for i, frame in enumerate(frames):
        if abs(frame['t'] - i * dt) > 1e-7:
            raise ValueError('Replay requires a frame at each fixed Python tick')
        interact = False
        bearing = frame['heading']
        ends = set()
        for event in by_step.get(i, []):
            kind = event['kind']
            if kind in ('pickup_start', 'squeeze_start'):
                held.add(kind.removesuffix('_start'))
            if kind in ('pickup_end', 'squeeze_end'):
                ends.add(kind.removesuffix('_end'))
            if kind == 'reload_start':
                reload = True
            if kind == 'reload_end':
                reload = False
            if kind == 'vault_start':
                interact = True
            if kind == 'shot':
                bearing = event['data']['bearing']
        inputs.append(dict(player_velocity=[(v-u)/dt for u,v in zip(p,frame['p'])],
                           boss_velocity=[(v-u)/dt for u,v in zip(b,frame['b'])],
                           heading=frame['heading'],bearing=bearing, fire=frame['ready'],
                           interact=bool(held) or interact,reload=reload))
        held.difference_update(ends)
        p,b=frame['p'],frame['b']
    terminal = episode['events'][-1]
    if terminal['kind']=='death' and terminal['step']==len(inputs):
        # Python checks the terminal grab after movement and before writing the frame.
        inputs.append(dict(player_velocity=[(v-u)/dt for u,v in zip(p,terminal['data']['player_position'])],
                           boss_velocity=[(v-u)/dt for u,v in zip(b,terminal['data']['boss_position'])],
                           heading=frames[-1]['heading'],bearing=frames[-1]['heading'],
                           fire=False,interact=False,reload=False))
    return spawn, inputs


def prepare(package, reference, out):
    packet, doc = read(package), read(reference)
    e=doc['episode']
    episode, frames=simulate(packet,e['policy'],e['scenario_seed'],doc['ability'])
    replayed=dict(episode=episode,frames=frames,ability=doc['ability'])
    if canonical_hash(replayed) != canonical_hash(doc):
        raise ValueError('Current Python replay differs from archived reference')
    dt=default_combat()['simulation']['tick_s']
    spawn,inputs=command_stream(doc,dt)
    provenance=dict(package=str(package.resolve()),package_hash=packet['package_hash'],
                    reference=str(reference.resolve()),source_sha256=file_hash(reference),
                    python_replay_sha256=canonical_hash(replayed),dt=dt,frame_count=len(inputs))
    for mode in ('paired','native'):
        write(out/f'{mode}_case.json',dict(schema='combat-replay/1',**provenance,native_boss=mode=='native',
              start_player=spawn['player'],start_boss=spawn['boss'],inputs=inputs,
              output=str((out/f'{mode}_godot.json').resolve())))


def run_godot(godot, case, log_path):
    from full_pcg.common import ROOT

    appdata = case.parent / 'appdata'
    env = dict(os.environ, RATKING_REPLAY_CASE=str(case.resolve()),
               APPDATA=str(appdata.resolve()), XDG_DATA_HOME=str(appdata.resolve()))
    hz = round(1/read(case)['dt'])
    with log_path.open('w', encoding='utf8') as log:
        subprocess.run([str(godot.resolve()), '--headless', '--fixed-fps', str(hz),
                        '--script', 'res://full_pcg/godot/replay_combat.gd'],
                       cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                       env=env, timeout=60, check=True)


def first_motion(expected, actual, who, dt):
    tolerance=.01
    for i,(a,b) in enumerate(zip(expected,actual)):
        error=math.dist(a[who],b[who])
        if error>tolerance:
            return dict(t=round(i*dt,6),delta_m=error,python=a[who],godot=b[who])
    return None


def first_state(expected, actual, dt):
    for i,(a,b) in enumerate(zip(expected,actual)):
        diff={k:[a[k],b[k]] for k in ('hp','loaded','reserve','opened','phase','visible') if a[k]!=b[k]}
        if diff:
            return dict(t=round(i*dt,6),values=diff)
    return None


def first_events(events, dt, godot=False):
    wanted={'shot','reload_start','reload_end','vault_start','vault_end','vault_blocked','squeeze_start','squeeze_end',
            'smash_start','portal_open','pickup_start','pickup_end','split','grab','death','victory','timeout'}
    return {kind:round((next(e['step'] for e in events if e['kind']==kind)-int(godot))*dt,6)
            for kind in sorted(wanted & {e['kind'] for e in events})}


def windows(frames, episode, dt, grab_range):
    # Streaks with both visibility and the proxy's action gate open.
    streaks=[]; start=None
    for i,f in enumerate(frames):
        if f['ready'] and start is None:
            start=i
        if not f['ready'] and start is not None:
            streaks.append((start,i));start=None
    if start is not None:streaks.append((start,len(frames)))
    first_pressure=next((f['t'] for f in frames if f['threat']),None)
    release=None
    if first_pressure is not None:
        release=next((f['t'] for f in frames if f['t']>first_pressure and not f['threat']
                      and not f['visible']),None)
    reloads=[]
    for event in episode['events']:
        if event['kind']=='reload_start':
            i=event['step']
            f=frames[i]
            gap=math.dist(f['p'],f['b'])
            reloads.append(dict(t=f['t'],gap_m=gap,inside_grab_range=gap<=grab_range,
                                threat=f['threat'],visible=f['visible']))
    hit_frames=Counter(e['data'].get('phase') for e in episode['events'] if e['kind']=='hit')
    return dict(initial_gap_m=math.dist(episode['events'][0]['data']['player'],episode['events'][0]['data']['boss']),
                threat_start_s=first_pressure,first_hidden_and_clear_s=release,reload_starts=reloads,
                ready_streaks_at_least_aim=sum((b-a)*dt+1e-9>=.35 for a,b in streaks),
                ready_streaks_after_release=sum((b-a)*dt+1e-9>=.35 and release is not None and a*dt>release for a,b in streaks),
                hits_by_phase=dict(hit_frames))


def after_shots(frames, events):
    """Match Godot's post-command snapshots to Python's pre-shot frames."""
    values = [dict(f) for f in frames]
    for e in events:
        step, kind, data = e['step'],e['kind'],e['data']
        if step>=len(values):
            continue
        if kind=='shot':
            values[step]['loaded']=data['loaded']
        elif kind=='hit':
            values[step]['hp']=data['hp']
        elif kind=='split':
            values[step]['phase']=2
    return values


def compare(out):
    case=read(out/'paired_case.json')
    path=Path(case['reference'])
    if case['source_sha256']!=file_hash(path):
        raise ValueError('Reference changed during replay')
    dt=case['dt']
    doc=read(path)
    episode,frames=doc['episode'],doc['frames']
    result=dict(source_sha256=case['source_sha256'],python_replay_sha256=case['python_replay_sha256'],
                package_hash=case['package_hash'],python_outcome=episode['outcome'],python_duration_s=episode['duration_s'],
                python_counts=dict(Counter(e['kind'] for e in episode['events'])),
                python_windows=windows(frames,episode,dt,default_combat()['boss']['grab_range_m']),
                python_first_events=first_events(episode['events'],dt))
    measured=after_shots(frames,episode['events'])
    for mode in ('paired','native'):
        path=out/f'{mode}_godot.json'
        data=read(path)
        if data['package_hash']!=case['package_hash'] or data['physics_hz']!=round(1/dt) or data['native_boss']!=(mode=='native'):
            raise ValueError('Replay result configuration changed')
        actual=data['frames']
        result[mode]=dict(result=data['result'],duration_s=len(actual)*dt,source_sha256=file_hash(path),
                          player=first_motion(frames,actual,'p',dt),boss=first_motion(frames,actual,'b',dt),
                          state=first_state(measured,actual,dt),last_frame=actual[-1],
                          counts=dict(Counter(e['kind'] for e in data['events'])),
                          first_events=first_events(data['events'],dt,godot=True))
    write(out/'comparison.json',result)
    print(out.name,result['python_outcome'],[(mode,result[mode]['result'],result[mode]['player'],result[mode]['boss'],result[mode]['state']) for mode in ('paired','native')])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    p=commands.add_parser('prepare')
    for label in ('package','reference','out'):p.add_argument(label,type=Path)
    p=commands.add_parser('run')
    for label in ('godot','package','reference','out'):p.add_argument(label,type=Path)
    p=commands.add_parser('compare')
    p.add_argument('out',type=Path)
    args=parser.parse_args()
    if args.command=='prepare':prepare(args.package,args.reference,args.out)
    elif args.command=='run':
        prepare(args.package,args.reference,args.out)
        for mode in ('paired','native'):
            run_godot(args.godot,args.out/f'{mode}_case.json',args.out/f'{mode}_engine.log')
        compare(args.out)
    else:compare(args.out)
