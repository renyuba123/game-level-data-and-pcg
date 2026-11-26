"""Short-horizon legal attack and relocation witnesses for calibration.

The target is stationary during an ETA calculation. Off-axis approaches use
the same portal roadmap as the agents, including time spent breaking a gate.
"""
import math
from functools import lru_cache

from shapely.geometry import LineString, Point
from shapely.prepared import prep
from shapely.ops import unary_union


class LocalActions:
    def __init__(self, layout, config):
        from shapely.geometry import shape
        self.floor = shape(layout['floor'])
        self.obstacles = shape(layout['base_obstacles'])
        self.gates = {p['id']: LineString(p['segment']).buffer(.09, cap_style='flat')
                      for p in layout['portals'] if p['kind'] != 'normal'}
        self.config = config

    @lru_cache(maxsize=128)
    def free(self, state, radius):
        solids = unary_union([self.obstacles, *(v for k,v in self.gates.items() if k not in state)])
        return prep(self.floor.difference(solids).buffer(-radius))

    def escape_time(self, actor, enemies, opened):
        player = self.config['player']
        radius = player['radius_m']
        free = self.free(frozenset(opened), radius)
        # A relocation must move at least one diameter and increase clearance
        # from the closest active threat. No crossing a window by raycast.
        for i in range(16):
            ang = i*math.tau/16
            end = tuple(x + 2*radius*u for x,u in zip(actor.pos,(math.cos(ang),math.sin(ang))))
            if enemies and min(math.dist(end,e) for e in enemies) <= min(math.dist(actor.pos,e) for e in enemies):
                continue
            if free.covers(LineString([actor.pos,end])):
                return 2*radius/player['speed_mps']
        return None

    def attack_eta(self, actor, target, opened, reach, warning, budget, contact):
        config = self.config
        role = 'stalker' if actor.name=='stalker' else 'boss'
        spec = config[role]
        gap = math.dist(actor.pos,target)
        delay = actor.wait if actor.action=='smash' else 0.
        travel = max(0.,gap-reach)
        straight_time = delay+travel/spec['speed_mps']+warning
        if straight_time > budget:
            return None
        if gap <= reach and contact(actor.pos,target,True):
            return delay+warning
        free = self.free(frozenset(opened),spec['radius_m'])
        end = tuple(a+(b-a)*travel/gap for a,b in zip(actor.pos,target)) if gap else actor.pos
        if free.covers(LineString([actor.pos,end])) and contact(end,target,True):
            return straight_time
        # Search physically realizable approaches within the short time horizon.
        # An unopened break/through already costs more than the default threat horizon.
        import heapq
        from itertools import count
        nav = actor.nav
        start_nodes = (actor.active,actor.node) if actor.active is not None else (actor.node,)
        serial=count()
        q=[]; best={}
        for node in start_nodes:
            pt=nav.xy[node]
            if not free.covers(LineString([actor.pos,pt])) and math.dist(pt,actor.pos)>1e-8:
                continue
            dist=math.dist(actor.pos,pt)/spec['speed_mps']+delay
            best[node]=dist
            heapq.heappush(q,(dist,next(serial),node))
        while q:
            t,_,node=heapq.heappop(q)
            if t>best[node] or t+warning>budget:continue
            if math.dist(nav.xy[node],target)<=reach and contact(nav.xy[node],target,True):
                return t+warning
            for dest,edge in nav.graph[node].items():
                extra=0.
                if edge.get('portal') and edge['portal'] not in opened:
                    kind=edge['kind']
                    if kind=='window' or (role=='stalker' and kind!='normal'):continue
                    if kind in ('through','break'):extra=config['portals'][kind+'_boss_smash_s']
                cost=t+edge['length']/spec['speed_mps']+extra
                if cost+warning<=budget and cost<best.get(dest,math.inf):
                    best[dest]=cost
                    heapq.heappush(q,(cost,next(serial),dest))
        return None



class RayField:
    """Horizontal rays through the same wall, sill, lintel and leaf as Godot."""
    def __init__(self, layout, window):
        from shapely.geometry import shape
        self.walls = shape(layout['walls'])
        self.blocks = shape(layout['base_obstacles']).difference(self.walls)
        self.gates = [p for p in layout['portals'] if p['kind']!='normal']
        self.window = window

    @lru_cache(maxsize=128)
    def surface(self, opened, height, contact):
        from .shell_depthmap import aperture
        parts = [self.walls] if 0 < height < 2.4 else []
        if 0 < height < 1.4:
            parts.append(self.blocks)
        for gate in self.gates:
            if gate['id'] in opened and gate['kind']!='window':
                continue
            if not 0 < height < 2.4:
                continue
            ends = gate['segment']
            window_solid = gate['kind']=='window' and not self.window['sill_m'] < height < self.window['lintel_m']
            line = LineString(ends) if contact or window_solid else aperture(*ends,gate['kind'])
            parts.append(line.buffer(.09,cap_style='flat'))
        return prep(unary_union(parts))

    def clear(self, start, end, opened, height=1.15, contact=False):
        segment = LineString([start,end]) if tuple(start)!=tuple(end) else Point(start)
        return not self.surface(frozenset(opened),height,contact).intersects(segment)
