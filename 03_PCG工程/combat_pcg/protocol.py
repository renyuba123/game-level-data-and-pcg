import json
import math
from pathlib import Path
from .contracts import SCHEMA,require,number

def default_combat():
    return json.loads(Path(__file__).with_name('combat_config.json').read_text(encoding='utf-8'))

def validate_combat(c):
    require(c['schema_version']==SCHEMA and c['units']=='model_m','combat version/units mismatch')
    for role in ['player','boss']:
        for name in ['radius_m','height_m','speed_mps']:number(c[role][name],role+'.'+name,1e-9)
    number(c['player']['hp'],'player.hp',1e-9)
    number(c['stalker']['speed_mps'],'stalker.speed_mps',0)
    number(c['stalker']['damage'],'stalker.damage',0)
    for name in ['damage','fire_interval_s','aim_s','reload_s','magazine','range_m']:number(c['weapon'][name],name,1e-9)
    s=c['supplies'];total=s['initial_rounds_including_magazine']+s['pack_count']*s['rounds_per_pack']
    for key in ['initial_rounds_including_magazine','pack_count','rounds_per_pack']:
        require(type(s[key]) is int and s[key]>0,'positive integer ammo required')
    hp=number(c['boss']['hp'],'boss.hp',1e-9)
    split=number(c['stalker']['split_hp_fraction'],'split',1e-6,1-1e-6)
    threshold=hp*split
    # The threshold-crossing hit loses its excess damage, so a simple
    # total-damage check can approve a budget that cannot finish phase 2.
    required_rounds=math.ceil((hp-threshold)/c['weapon']['damage'])+math.ceil(threshold/c['weapon']['damage'])
    require(total>=required_rounds,'theoretical ammo cannot defeat both phases')
    require(c['weapon']['magazine']<=s['initial_rounds_including_magazine'],'loaded ammo exceeds initial budget')
    require(not s['respawn'],'finite budget cannot respawn')
    require(not c['portals']['player_can_break'],'player cannot break walls')
    require(c['portals']['after_boss_smash']=='both_roles_open','post-smash roles mismatch')
    require(c['termination']['success']=='large_boss_hp_zero' and not c['termination']['exit_is_victory'],'escape objective is forbidden')
    require(c['termination']['death']=='valid_large_boss_grab_or_player_hp_zero','player death contract mismatch')
    require(c['stalker']['crossing_hit_overflow']=='discard_and_clamp_to_threshold','split damage contract mismatch')
    require(c['stalker']['boss_kill_only_after_split_in_later_tick'] is True,'two-stage kill required')
    sampling=c['sampling']
    require(len(set(sampling['scenario_seeds']))==len(sampling['scenario_seeds']),'duplicate search scenario')
    require(not set(sampling['scenario_seeds'])&set(sampling['heldout_seeds']),'heldout leakage')
    require(len(sampling['policies'])*len(sampling['scenario_seeds'])==sampling['episodes_per_candidate']==12,'search must have 12 scenarios')
    budget=c['search_budget'];requests=len(budget['arms'])*len(budget['seeds'])*budget['population']*(budget['reproductions']+1)
    require(requests==budget['candidate_requests']==6048,'candidate request budget mismatch')
    require(requests*12==budget['counterfactual_full_simulation_count'],'simulation accounting mismatch')
    require(c['provenance']['official_numeric_parameters'] is False,'draft values are not official measurements')
    return {'total_rounds':total,'theoretical_damage':total*c['weapon']['damage'],'minimum_rounds_for_two_phase_kill':required_rounds,'candidate_requests':requests,'episodes_per_candidate':12}

def formal_preflight(combat,scoring):
    from .scoring import validate_config
    validate_combat(combat);validate_config(scoring)
    reasons=[]
    if not combat['frozen']:reasons.append('combat_protocol_not_frozen')
    if not scoring['frozen']:reasons.append('scoring_protocol_not_frozen')
    if not combat['provenance']['physical_scale_calibrated']:reasons.append('physical_scale_not_calibrated')
    # This release contains no search engine. Never fall through to a fake success.
    reasons.append('phase4_automatic_experiment_engine_not_implemented')
    return {'allowed':False,'reasons':reasons}
