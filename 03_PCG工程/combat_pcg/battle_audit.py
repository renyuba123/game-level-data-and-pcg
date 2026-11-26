"""Reconcile recorded battle events with layout, ammunition and portal states."""
import math

from shapely.geometry import LineString, Point
from .battle_sensing import RayField


def audit(packet, records, combat):
    layout=packet['layout']
    field=RayField(layout,packet['window'])
    gates={p['id']:p['kind'] for p in layout['portals']}
    supplies={p['id']:p['position'] for p in layout['supplies']}
    spec=combat['supplies']
    weapon=combat['weapon']
    issues=[]
    for record in records:
        episode=record['episode']
        loaded=min(weapon['magazine'],spec['initial_rounds_including_magazine'])
        reserve=spec['initial_rounds_including_magazine']-loaded
        consumed=set()
        opened=set()
        active_smashes={}
        open_action=None
        last_shot=None
        win_hp=combat['boss']['hp']
        phase2_tick=None
        for event in episode['events']:
            d=event['data']; kind=event['kind']; t=event['t']; step=event['step']
            error=None
            if kind=='smash_start':
                id=d['id']
                if d['actor']!='b' or gates.get(id) not in ('break','through') or id in opened:
                    error='illegal_smash'
                active_smashes[id]=t
            elif kind=='portal_open':
                id=d['id']; portal=gates.get(id)
                if portal not in ('through','break') or d['by']!='boss' or id in opened or id not in active_smashes:
                    error='illegal_open'
                elif t-active_smashes[id]+combat['simulation']['tick_s']+1e-8<combat['portals'][portal+'_boss_smash_s']:
                    error='early_open'
                opened.add(id)
            elif kind=='crossing':
                id=d['id']; portal=gates.get(id)
                if portal=='window' and d['role']!='p':
                    error='enemy_window_crossing'
                if portal=='break' and id not in opened:
                    error='closed_break_crossing'
                if portal=='through' and id not in opened and d['role']!='p':
                    error='enemy_closed_through_crossing'
            elif kind=='pickup_start':
                open_action=(d['id'],t)
            elif kind=='pickup_end':
                id=d['id']; pos=supplies.get(id)
                if pos is None or id in consumed or not open_action or open_action[0]!=id:
                    error='illegal_pickup'
                elif (math.dist(pos,d['player_position'])>spec['pickup_radius_m']
                      or not field.clear(pos,d['player_position'],opened,contact=True)
                      or t-open_action[1]+1e-8<spec['pickup_s']):
                    error='pickup_without_access'
                consumed.add(id);reserve+=spec['rounds_per_pack']
                if d['reserve']!=reserve:error='pickup_budget'
                open_action=None
            elif kind=='reload_end':
                amount=min(reserve,weapon['magazine']-loaded)
                reserve-=amount;loaded+=amount
                if (loaded,reserve)!=(d['loaded'],d['reserve']):error='reload_budget'
            elif kind=='shot':
                loaded-=1
                if loaded<0 or d['loaded']!=loaded or d['reserve']!=reserve:error='shot_budget'
                last_shot=event
            elif kind=='hit':
                arc=last_shot['data'] if last_shot and last_shot['step']==step else None
                if arc is None:error='hit_without_shot'
                else:
                    start=arc['muzzle'];angle=arc['bearing']
                    end=(start[0]+weapon['range_m']*math.cos(angle),start[1]+weapon['range_m']*math.sin(angle))
                    target=Point(d['boss_position']).buffer(combat['boss']['radius_m'])
                    hit=LineString([start,end]).intersection(target)
                    if hit.is_empty or not field.clear(start,hit.coords[0],opened):error='blocked_hit'
                threshold=combat['boss']['hp']*combat['stalker']['split_hp_fraction']
                win_hp=max(threshold if phase2_tick is None else 0,win_hp-weapon['damage'])
                if d['hp']!=win_hp:error='damage_mismatch'
            elif kind=='split':
                if phase2_tick is not None or win_hp!=combat['boss']['hp']*combat['stalker']['split_hp_fraction']:
                    error='invalid_split'
                phase2_tick=step
            elif kind=='victory':
                if phase2_tick is None or step<=phase2_tick or win_hp!=0:error='early_victory'
            if error:issues.append(dict(episode=episode['episode_id'],event=event['id'],reason=error))
    return issues
