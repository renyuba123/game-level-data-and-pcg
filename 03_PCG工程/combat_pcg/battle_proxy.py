"""Deterministic 2D research agents. Model metres, seconds and independent episode streams."""
from pathlib import Path
import math
import random
import sys
from shapely.geometry import Point,LineString,Polygon
from .arena_nav import ArenaNav,step_to
from .battle_sensing import LocalActions
from .event_order import resolve_step
from .protocol import default_combat
from .contracts import SCHEMA,canonical_hash,validate_episode
from .battle_sensing import RayField
from full_pcg.common import read,write


def angle(a,b):return math.atan2(b[1]-a[1],b[0]-a[0])
def angle_diff(a,b):return (a-b+math.pi)%(2*math.pi)-math.pi


class Actor:
    def __init__(self,nav,pos,name):
        self.name=name; self.nav=nav; self.pos=tuple(pos); self.node=nav.anchor(self.pos,('spawn',name))
        self.queue=[];self.active=None;self.wait=0.;self.action=None

    def plan(self,goal,opened,c):
        if goal is None or self.action=='vault_return':return
        self.queue=self.nav.path(self.active if self.active is not None else self.node,goal,opened,c,self.name)

    def move(self,dt,opened,c,log,speed=None,blocker=None):
        if self.action=='vault_return':
            self.pos=step_to(self.pos,self.nav.xy[self.node],self.return_speed*dt)
            if self.pos==self.nav.xy[self.node]:self.action=None;self.active=None
            return
        if self.active is None:
            if not self.queue:return
            # Look ahead within continuous, eroded free floor only. A shortcut
            # cannot skip even one explicit portal or its action/cost.
            previous=self.node
            furthest=0
            for index, waypoint in enumerate(self.queue[:16]):
                if 'portal' in self.nav.graph[previous][waypoint]:break
                if self.nav.walkable.covers(LineString([self.pos,self.nav.xy[waypoint]])):furthest=index
                previous=waypoint
            self.active=self.queue[furthest]
            self.queue=self.queue[furthest+1:]
            edge=self.nav.graph.get_edge_data(self.node,self.active,{})
            gate=edge.get('portal');kind=edge.get('kind')
            if gate and gate not in opened and kind!='normal':
                if self.nav.role=='boss':
                    self.action='smash';self.wait=c['portals'][kind+'_boss_smash_s']
                elif kind in ('window','through'):
                    self.action='vault' if kind=='window' else 'squeeze'
                    self.wait=c['window']['duration_s'] if kind=='window' else c['portals']['through_player_squeeze_s']
                else:
                    self.active=None;self.queue=[];return
                log(self.action+'_start',id=gate,portal_kind=kind,actor=self.name)
        edge=self.nav.graph.get_edge_data(self.node,self.active,{})
        if self.wait>0:
            self.wait=max(0,self.wait-dt)
            if self.action in ('vault', 'squeeze'):
                duration = c['window']['duration_s'] if self.action=='vault' else c['portals']['through_player_squeeze_s']
                start, end = self.nav.xy[self.node], self.nav.xy[self.active]
                next_pos = tuple(b+(a-b)*self.wait/duration for a,b in zip(start,end))
                if self.action=='vault' and blocker and LineString([self.pos,next_pos]).distance(Point(blocker))<c['player']['radius_m']+c['boss']['radius_m']:
                    log('vault_blocked',id=edge['portal'],role=self.name)
                    self.action='vault_return'; self.wait=0.; self.queue=[]
                    self.return_speed=math.dist(start,end)/duration
                    return
                self.pos = next_pos
            if self.wait>0:return
            if self.action=='smash':
                opened.add(edge['portal']);log('portal_open',id=edge['portal'],by='boss');self.action=None
        target=self.nav.xy[self.active]
        self.pos=step_to(self.pos,target,(speed or c['stalker' if self.name=='stalker' else self.nav.role]['speed_mps'])*dt)
        if self.pos==target:
            self.node=self.active;self.active=None
            if self.action:
                log(self.action+'_end',id=edge['portal']);self.action=None
            if 'portal' in edge:log('crossing',id=edge['portal'],role=self.name)


def simulate(packet,policy,seed,ability=None):
    c=default_combat();c['window']=packet['window']
    if policy not in c['sampling']['policies']:raise ValueError('Unknown combat policy')
    ability=ability or {}
    rng=random.Random(f'aim:{seed}'); decisions=random.Random(f'decision:{seed}')
    l=packet['layout'];dt=c['simulation']['tick_s']; opened=set()
    pnav=ArenaNav(packet,'player'); bnav=ArenaNav(packet,'boss')
    def start(role, nav):
        origin=tuple(l[role]['position'])
        rng_spawn=random.Random(f'spawn:{role}:{seed}')
        region=Polygon(next(r['polygon'] for r in l['rooms'] if r['id']==l[role]['room']))
        for _ in range(12):
            candidate=tuple(x+rng_spawn.uniform(-.20,.20) for x in origin)
            if nav.face(candidate) is not None and region.contains(Point(candidate)):
                return candidate
        return origin
    player=Actor(pnav,start('spawn',pnav),'p')
    boss=Actor(bnav,start('boss',bnav),'b')
    heading=l['spawn']['heading_rad']+decisions.uniform(-.20,.20)
    events=[];frames=[];seen={};collected=set();last=None;heard=None
    w=c['weapon'];b=c['boss'];s=c['supplies'];loaded=min(w['magazine'],s['initial_rounds_including_magazine']);reserve=s['initial_rounds_including_magazine']-loaded
    actions=LocalActions(l,c)
    rays=RayField(l,c['window'])
    def clear(a,b,contact=False):
        return rays.clear(a,b,opened,contact=contact)
    def log(kind,**data):
        data.update(player_position=player.pos,boss_position=boss.pos,phase=phase)
        events.append(dict(id=str(len(events)),t=t,sequence=len(events),step=i,kind=kind,data=data))
    def in_view(pt):
        return (math.dist(player.pos,pt)<=c['player']['vision_range_m']
                and abs(angle_diff(angle(player.pos,pt),heading))<=math.radians(c['player']['fov_deg']/2)
                and clear(player.pos,pt))

    def destination(nav,pos):
        face=nav.face(pos)
        if face is not None:return face
        # Target may walk closer to a wall than the larger boss can. Move
        # to the nearest reachable observation point; this never moves an actor by snapping.
        near=sorted(((math.dist(nav.xy[i],pos),i) for i in range(len(nav.faces))))
        return next((i for dist,i in near if clear(nav.xy[i],pos,True)),None)
    def escape_goal():
        if last is None:return None
        choices=[]
        for r in l['rooms']:
            pt=tuple(r['center']);k=destination(pnav,pt)
            if k is None:continue

            sight=clear(pt,last)
            value=min(math.dist(pt,last),10)-.4*math.dist(pt,player.pos)
            if policy=='occlusion':value+=4*(not sight)
            if policy=='output':value+=2*sight
            choices.append((value,k))
        return max(choices,default=(0,None))[1]
    shots=reload_until=pickup_until=aim=warning=0.;pickup=None;hp=b['hp'];phase=1;split=None
    stalk=None;stalk_warn=control=retreat=0.;last_seen_t=-1e6;outcome='timeout'
    attack_reaction=c['player']['reaction_s']*ability.get('reaction_scale',1)
    visible_before=False;next_plan=0.
    patrol=None; patrol_until=0.; boss_patrol=None; boss_until=0.; last_contact=-100.
    previous_threats=set()
    was_empty=False
    for i in range(round(c['simulation']['time_limit_s']/dt)+1):
        t=round(i*dt,6)
        if i==0:log('spawn',player=player.pos,boss=boss.pos,room_id=l['spawn']['room'])
        if t>=c['simulation']['time_limit_s']:break
        gap=math.dist(player.pos,boss.pos)
        seen_boss=clear(player.pos,boss.pos) and gap<=c['player']['vision_range_m'] and abs(angle_diff(angle(player.pos,boss.pos),heading))<=math.radians(c['player']['fov_deg']/2)
        if seen_boss:last=boss.pos;last_seen_t=t
        if seen_boss!=visible_before or i==0:log('perception',visible=seen_boss,position=player.pos)
        visible_before=seen_boss
        for item in l['supplies']:
            pt=tuple(item['position'])
            if item['id'] not in seen and math.dist(player.pos,pt)<=c['player']['vision_range_m'] and abs(angle_diff(angle(player.pos,pt),heading))<math.radians(c['player']['fov_deg']/2) and clear(player.pos,pt):
                seen[item['id']]=pt
        if clear(boss.pos,player.pos):heard=player.pos;last_contact=t
        if t>=next_plan:
            next_plan=t+.4
            if heard and t-last_contact<2.0:
                boss.plan(destination(bnav,heard),opened,c)
            else:
                if t>=boss_until or boss.node==boss_patrol:
                    boss_patrol=destination(bnav,decisions.choice(l['rooms'])['center']);boss_until=t+4.
                boss.plan(boss_patrol,opened,c)
            need=loaded+reserve < (12 if policy=='supply' else 5)
            known=[k for k in seen if k not in collected]
            if known and need:
                target=seen[min(known,key=lambda k:math.dist(player.pos,seen[k]))]
                if pnav.face(target) is not None:
                    marker=('pack',target)
                    if marker not in pnav.xy:pnav.anchor(target,marker)
                    player.plan(marker,opened,c)
            elif last and t-last_seen_t<1.5 and math.dist(last,player.pos)<(5.4 if policy=='occlusion' else 3.2):player.plan(escape_goal(),opened,c)
            elif not seen_boss or need:
                if patrol is None or t>=patrol_until or player.node==patrol:
                    patrol=destination(pnav,decisions.choice(l['rooms'])['center']);patrol_until=t+4.
                player.plan(patrol,opened,c)
            elif player.active is None:player.queue=[]
        boss.move(dt,opened,c,log)
        if not pickup and t>=control:player.move(dt,opened,c,log,c['player']['aim_speed_mps'] if aim>0 and (last is None or math.dist(last,player.pos)>4.5) else None,blocker=boss.pos)
        gap=math.dist(player.pos,boss.pos)
        melee=clear(boss.pos,player.pos,True)
        budget=attack_reaction+w['aim_s']+w['fire_interval_s']+c['score_sampling']['threat_margin_s']
        eta=actions.attack_eta(boss,player.pos,opened,b['grab_range_m'],max(0.,b['attack_warning_s']-warning),budget,clear)
        stalk_eta=None
        if stalk is not None and t>=retreat:
            stalk_eta=actions.attack_eta(stalk,player.pos,opened,.9,max(0.,c['stalker']['warning_s']-stalk_warn),budget,clear)
        danger=eta is not None or stalk_eta is not None
        seen_boss=in_view(boss.pos)
        seen_stalk=stalk is not None and in_view(stalk.pos)
        dodge=actions.escape_time(player,[boss.pos]+([stalk.pos] if stalk is not None and t>=retreat else []),opened)
        delay=max(0.,control-t)+player.wait if player.action else max(0.,control-t)
        margins={name:time-attack_reaction-delay-dodge if dodge is not None else None
                 for name,time in [('boss',eta),('stalker',stalk_eta)] if time is not None}
        now={key for key in margins if (seen_boss if key=='boss' else seen_stalk)}
        for key in sorted(now-previous_threats):
            log('attack_warning',by=key,margin_s=margins[key],perceived=True)
        previous_threats=now
        warning=warning+dt if melee and gap<=b['grab_range_m'] else 0.
        if warning>=b['attack_warning_s']:
            outcome='death';log('grab',by='large_boss');break
        if stalk is not None and t>=retreat:
            if i%8==0 and clear(stalk.pos,player.pos): stalk.plan(destination(stalk.nav,player.pos),opened,c)
            stalk.move(dt,opened,c,log)
            if math.dist(stalk.pos,player.pos)<.9 and clear(stalk.pos,player.pos,True):
                stalk_warn+=dt
                if stalk_warn>=c['stalker']['warning_s']:
                    control=t+c['stalker']['control_s'];retreat=t+c['stalker']['cooldown_s'];stalk_warn=0;log('grab',by='stalker')
            else:stalk_warn=0
        if loaded+reserve<5 and player.active is not None:
            desired=angle(player.pos,player.nav.xy[player.active])
        else:desired=angle(player.pos,last) if last and t-last_seen_t<1.2 else heading+.6
        turn=math.radians(c['player']['turn_deg_per_s'])*dt
        heading+=max(-turn,min(turn,angle_diff(desired,heading)))
        if pickup and t>=pickup_until:
            if math.dist(player.pos,seen[pickup])<=s['pickup_radius_m'] and clear(player.pos,seen[pickup],True):
                reserve+=s['rounds_per_pack'];collected.add(pickup);log('pickup_end',id=pickup,reserve=reserve,loaded=loaded)
                if was_empty:was_empty=False;log('resource_restored')
            pickup=None
        if not pickup and loaded+reserve<12 and t>=control and not player.action:
            for k,pt in seen.items():
                if k not in collected and math.dist(pt,player.pos)<=s['pickup_radius_m'] and clear(player.pos,pt,True):
                    pickup=k;pickup_until=t+s['pickup_s'];log('pickup_start',id=k);break
        if reload_until and t>=reload_until:
            rounds=min(reserve,w['magazine']-loaded);reserve-=rounds;loaded+=rounds;reload_until=0;log('reload_end',loaded=loaded,reserve=reserve)
        if loaded==0 and reserve and not reload_until and not pickup:
            reload_until=t+w['reload_s'];log('reload_start')
        muzzle=(player.pos[0]+.12*math.cos(heading),player.pos[1]+.12*math.sin(heading))
        window=seen_boss and gap<=w['range_m'] and clear(player.pos,muzzle) and clear(muzzle,boss.pos) and abs(angle_diff(angle(muzzle,boss.pos),heading))<math.radians(c['player']['aim_fov_deg']/2)
        sprinting=player.active is not None and last is not None and math.dist(last,player.pos)<=4.5
        ready=window and not sprinting and not pickup and not reload_until and not player.action and t>=control and loaded>0
        aim=aim+dt if ready else 0.
        frames.append(dict(t=t,phase=phase,p=player.pos,b=boss.pos,heading=heading,hp=hp,loaded=loaded,reserve=reserve,
              detected=seen_boss,stalker_position=stalk.pos if stalk else None,visible=seen_boss,threat=danger,window=bool(window),ready=bool(ready),can_relocate=dodge is not None,reactable={key:value is not None and value>=0 for key,value in margins.items()},stalker_visible=bool(seen_stalk),etas=dict(boss=eta,stalker=stalk_eta),action_risk=bool(pickup or reload_until),opened=sorted(opened),known_supplies=sorted(seen)))
        if aim+1e-9>=max(w['aim_s'],attack_reaction) and t>=shots:
            loaded-=1;shots=t+w['fire_interval_s'];heard=player.pos;last_contact=t
            if loaded+reserve==0:was_empty=True;log('resource_empty')
            bearing=heading+math.radians(rng.gauss(0,w['angular_error_sd_deg']*ability.get('error_scale',1)))
            ray=LineString([muzzle,(muzzle[0]+w['range_m']*math.cos(bearing),muzzle[1]+w['range_m']*math.sin(bearing))])
            hit=ray.intersection(Point(boss.pos).buffer(b['radius_m']))
            log('shot',position=player.pos,loaded=loaded,reserve=reserve,bearing=bearing,muzzle=muzzle)
            stalk_hit=ray.intersection(Point(stalk.pos).buffer(c['stalker']['radius_m'])) if stalk else None
            if stalk_hit is not None and not stalk_hit.is_empty and (hit.is_empty or ray.project(Point(stalk_hit.coords[0]))<ray.project(Point(hit.coords[0]))) and clear(muzzle,stalk_hit.coords[0]):
                retreat=t+3.;stalk_warn=0.;log('retreat',by='stalker',reason='shot')
            elif not hit.is_empty and clear(muzzle,hit.coords[0]):
                state,transitions,terminal=resolve_step({'boss_hp':hp,'player_alive':True,'split':phase==2},
                    [dict(kind='hit',damage=w['damage'],line_of_sight=True)],c)
                hp=state['boss_hp']
                log('hit',hp=hp,phase=phase,position=player.pos)
                if 'split' in transitions:
                    phase=2;split=t;log('split')
                    pts=[(math.dist(pt,boss.pos),pt) for k,pt in pnav.xy.items() if isinstance(k,int) and .85<=math.dist(pt,boss.pos)<=1.6 and clear(boss.pos,pt,True)]
                    if pts:
                        stalk=Actor(pnav,min(pts)[1],'stalker');retreat=t+.5
                    else:log('stalker_spawn_blocked')
                elif terminal=='victory':outcome='victory';break
    log(outcome)
    episode=dict(ability=ability,schema_version=SCHEMA,layout_schema_version=5,event_protocol='shell-battle/1',episode_id=f'{policy}_{seed}',individual_id=l['layout_hash'][:16],
        layout_hash=l['layout_hash'],combat_config_hash=canonical_hash({'combat':c,'ability':ability}),policy=policy,scenario_seed=seed,outcome=outcome,
        duration_s=t,phase2_reached=split is not None,phase_durations_s=dict(phase1=t if split is None else split,phase2=0 if split is None else t-split),events=events)
    episode['package_hash']=packet['package_hash']
    episode['window_config_hash']=packet['window_config_hash']
    validate_episode(episode)
    return episode,frames


def batch(package,out,policies=None,seeds=None,ability=None):
    packet=read(package);out.mkdir(parents=True,exist_ok=True)
    sampling=default_combat()['sampling']
    import hashlib
    files=('battle_proxy.py','arena_nav.py','battle_sensing.py','shell_depthmap.py','event_order.py','contracts.py')
    implementation={name:hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in files}
    actual_seeds=list(seeds if seeds is not None else sampling['scenario_seeds'])
    actual_policies=list(policies or sampling['policies'])
    recipe=dict(package_hash=packet['package_hash'],implementation=implementation,policies=actual_policies,
                scenario_seeds=actual_seeds,ability=ability or {},combat=default_combat(),window=packet['window'])
    manifest=out/'manifest.json'
    if manifest.exists() and read(manifest)['recipe']!=recipe:
        raise ValueError('Use a fresh episode directory for a changed implementation/configuration')
    if not manifest.exists() and list(out.glob('*.json')):
        raise ValueError('Existing episodes have no provenance manifest')
    write(manifest,dict(recipe=recipe,complete=False))
    for policy in actual_policies:
        for seed in actual_seeds:
            episode,frames=simulate(packet,policy,seed,ability)
            write(out/(episode['episode_id']+'.json'),dict(episode=episode,frames=frames,ability=ability or {}))
            print(policy,seed,episode['outcome'],episode['duration_s'],flush=True)
    write(manifest,dict(recipe=recipe,complete=True))


if __name__=='__main__':batch(Path(sys.argv[1]),Path(sys.argv[2]))
