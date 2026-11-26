"""Small dependency-free runtime contracts, separate from Legacy's JSON format."""
import hashlib
import json
import math
import re
from enum import Enum

SCHEMA = 'combat-pcg/3'
class ContractError(ValueError): pass
class Status(str, Enum):
    VALID='VALID'; INVALID='INVALID'; UNCERTAIN='UNCERTAIN'; ERROR='ERROR'

def require(condition, message):
    if not condition: raise ContractError(message)

def number(value, field, low=None, high=None):
    require(isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value), f'{field}: finite number required')
    require(low is None or value>=low, f'{field}: below {low}')
    require(high is None or value<=high, f'{field}: above {high}')
    return value

def canonical_hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()

def hash_field(value, field):
    require(isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value) is not None, f'{field}: SHA256 required')

def identifier(value,field):
    require(isinstance(value,str) and bool(value.strip()), f'{field}: nonempty ID required')

def point(value,field):
    require(isinstance(value,(list,tuple)) and len(value)==2,f'{field}: [x,z] model metres required')
    for v in value:number(v,field)

def validate_genome(g):
    shell = g.get('schema_version') == 'combat-shell-genome/1'
    require(shell or g.get('schema_version')==SCHEMA,'genome schema mismatch')
    require(g.get('units')=='model_m','genome units must be model_m')
    require(isinstance(g.get('seed'),int) and not isinstance(g['seed'],bool),'seed must be integer')
    require(isinstance(g.get('rooms'),list) and len(g['rooms'])>=2,'rooms required')
    ids=[]
    for r in g['rooms']:
        identifier(r.get('id'),'room.id');ids.append(r['id']);point(r.get('position'),'room.position')
        number(r.get('rotation_deg'),'room.rotation');require(isinstance(r.get('outline_local'),list) and len(r['outline_local'])>=3,'room outline required')
        for p in r['outline_local']:point(p,'outline')
    require(len(ids)==len(set(ids)),'duplicate room ID')
    edge_ids=[];pairs=[]
    for e in g.get('connections',[]):
        identifier(e.get('id'),'portal.id');edge_ids.append(e['id'])
        require(e.get('a') in ids and e.get('b') in ids and e['a']!=e['b'],'dangling/self portal')
        require(e.get('kind') in (('normal','through','break','window') if shell else ('normal','through','break')),'unknown portal kind')
        if shell:
            segment=e.get('segment')
            require(isinstance(segment,(tuple,list)) and len(segment)==2,'portal endpoints required')
            for pt in segment: point(pt,'portal endpoint')
            width=number(e.get('width'),'portal width',1e-6)
            require(math.isclose(width,math.dist(*segment),abs_tol=1e-5),'portal width disagrees with endpoints')
        pairs.append(tuple(sorted((e['a'],e['b']))))
    require(len(edge_ids)==len(set(edge_ids)),'duplicate portal ID')
    if shell:
        geometry=[(pair,tuple(sorted(map(tuple,e['segment'])))) for pair,e in zip(pairs,g['connections'])]
        require(len(geometry)==len(set(geometry)),'coincident portal geometry')
    else: require(len(pairs)==len(set(pairs)),'duplicate adjacency: multiple portal geometry requires a future multigraph schema')
    spawn=g.get('spawn',{})
    for role in ['player','boss']:
        actor=spawn.get(role,{})
        require(actor.get('room_id') in ids,'spawn room missing');point(actor.get('position'),'spawn.position');number(actor.get('heading_rad'),'heading')
    require(spawn['player']['room_id']==spawn['boss']['room_id'],'combat actors must start in same room')
    require(spawn['player']['position']!=spawn['boss']['position'],'coincident spawn')
    for name in ['obstacles','supplies']:
        item_ids=[]
        for item in g.get(name,[]):
            identifier(item.get('id'),name+'.id');item_ids.append(item['id'])
            require(item.get('room_id') in ids,name+': unknown room');point(item.get('position'),name+'.position')
            if name=='supplies':require('amount' not in item and 'damage' not in item,'supply quantity belongs to fixed protocol, not Genome')
        require(len(item_ids)==len(set(item_ids)),name+': duplicate ID')
    require(not any(k in g for k in ['weapon','damage','boss_hp','player_speed','combat_config']),'combat capabilities are not genes')
    return g

EVENTS={'spawn','perception','shot','hit','reload_start','reload_end','pickup_start','pickup_end',
        'squeeze_start','squeeze_end','smash_start','portal_open','split','attack_warning','grab','death','victory','timeout'}

def validate_episode(e):
    require(e.get('schema_version')==SCHEMA,'episode schema mismatch')
    for field in ['episode_id','individual_id','policy']:identifier(e.get(field),field)
    for field in ['layout_hash','combat_config_hash']:hash_field(e.get(field),field)
    require(isinstance(e.get('scenario_seed'),int) and not isinstance(e['scenario_seed'],bool),'scenario seed required')
    number(e.get('duration_s'),'duration',0)
    require(e.get('outcome') in ['victory','death','timeout','error'],'unknown outcome')
    require(e.get('phase2_reached') in [True,False] and type(e['phase2_reached']) is bool,'phase2 flag required')
    previous=-1.;event_ids=[]
    for event in e.get('events',[]):
        identifier(event.get('id'),'event.id');event_ids.append(event['id'])
        t=number(event.get('t'),'event.t',0,e['duration_s']);require(t>=previous,'events out of chronological order');previous=t
        allowed=EVENTS | {'vault_start','vault_end','vault_blocked'} if e.get('layout_schema_version')==5 else EVENTS
        if e.get('event_protocol') == 'shell-battle/1':
            require(e.get('layout_schema_version') == 5, 'shell battle requires current layout')
            allowed = allowed | {'crossing', 'stalker_spawn_blocked', 'retreat', 'resource_empty', 'resource_restored', 'stalker_warning'}
        require(event.get('kind') in allowed,'unknown event kind')
        require(isinstance(event.get('data'),dict),'event data required')
    require(len(event_ids)==len(set(event_ids)),'duplicate event ID')
    kinds=[v['kind'] for v in e.get('events',[])]
    if e['outcome']!='error':
        require(bool(kinds) and kinds[-1]==e['outcome'],'terminal event must match outcome')
        require(sum(k in ['victory','death','timeout'] for k in kinds)==1,'multiple terminal events')
        require(('split' in kinds)==e['phase2_reached'],'split/phase2 mismatch')
    return e

def validate_individual(record):
    require(record.get('schema_version')==SCHEMA,'individual schema mismatch')
    identifier(record.get('id'),'individual.id')
    require(isinstance(record.get('generation'),int) and record['generation']>=0,'generation must include zero')
    for k in ['genome_hash','generation_config_hash']:hash_field(record.get(k),k)
    require(isinstance(record.get('parent_ids'),list),'parent_ids required')
    require(record['id'] not in record['parent_ids'],'self ancestry')
    for p in record['parent_ids']:identifier(p,'parent')
    require(isinstance(record.get('operations'),list),'operations required')
    require(record.get('status') in [s.value for s in Status],'unknown status')
    require(isinstance(record.get('reasons'),list),'reasons required')
    if record['status']!='VALID':require(bool(record['reasons']),'non-VALID must explain reasons')
    return record
