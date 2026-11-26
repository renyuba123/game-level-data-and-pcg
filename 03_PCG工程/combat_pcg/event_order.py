"""Phase 1 deterministic boundary contract, not a full combat simulator."""
from .contracts import require,number

PRIORITY={'grab':0,'portal_open':1,'reload_end':2,'pickup_end':3,'shot':4,'hit':5,'timeout':6}

def resolve_step(state,events,combat):
    """Resolve validated simultaneous proposals; later systems must supply LOS and legal actions.

    All proposals share the same logical time. A valid grab wins exact ties.
    First-phase damage is clamped at the split threshold, discarding overflow.
    The large Boss can die only on a later logical step in phase 2.
    """
    current=dict(state);out=[];terminal=None
    require(current['boss_hp']>0 and current['player_alive'],'step requires live actors')
    require(sum(e['kind']=='hit' for e in events)<=1,'at most one damage hit per logical step')
    for event in sorted(events,key=lambda e:(PRIORITY[e['kind']],e.get('sequence',0))):
        kind=event['kind']
        if terminal:break
        if kind=='grab':
            require(type(event.get('valid')) is bool,'grab validation required')
            if event['valid']:current['player_alive']=False;terminal='death';out.extend(['grab','death'])
        elif kind=='portal_open':
            require(event.get('by')=='boss','only boss can open a break/through by damage')
            current.setdefault('open_portals',set()).add(event['id']);out.append('portal_open')
        elif kind=='reload_end':
            current['loaded']=number(event['loaded'],'loaded rounds',0);out.append('reload_end')
        elif kind=='pickup_end':
            current['reserve']+=number(event['rounds'],'pickup rounds',0);out.append('pickup_end')
        elif kind=='shot':
            require(current['loaded']>0,'shot without loaded round');current['loaded']-=1;out.append('shot')
        elif kind=='hit':
            require(type(event.get('line_of_sight')) is bool,'post-door LOS validation required')
            if not event['line_of_sight']:continue
            damage=number(event['damage'],'damage',0);before=current['boss_hp'];threshold=combat['boss']['hp']*combat['stalker']['split_hp_fraction']
            if not current.get('split',False) and before-damage<=threshold:
                current['boss_hp']=threshold;current['split']=True;out.extend(['hit','split'])
            else:
                current['boss_hp']=max(0,before-damage);out.append('hit')
                if current['boss_hp']==0:terminal='victory';out.append('victory')
        elif kind=='timeout':terminal='timeout';out.append('timeout')
        else:raise ValueError('unsupported event: '+kind)
    return current,out,terminal
