"""Walk the same role-specific triangles and portal links consumed by Godot."""
import math
import networkx as nx
from shapely.geometry import Polygon,Point,LineString
from shapely.strtree import STRtree
from shapely.prepared import prep
from shapely.ops import unary_union


class ArenaNav:
    def __init__(self,packet,role):
        self.graph=nx.Graph()
        self.faces=[Polygon(t) for t in packet['navigation'][role]]
        self.tree=STRtree(self.faces)
        self.walkable=prep(unary_union(self.faces))
        self.xy={}
        for i,face in enumerate(self.faces):
            c=face.centroid
            self.xy[i]=(c.x,c.y)
            pts=list(face.exterior.coords)
            for a,b in zip(pts,pts[1:]):
                edge=tuple(sorted((a,b)))
                self.xy[edge]=((a[0]+b[0])/2,(a[1]+b[1])/2)
                self.connect(i,edge)
        for link in packet['links']:
            if link['role']!=role: continue
            if role=='boss' and link['kind']=='window': continue
            a,b=link['points']
            u=self.anchor(tuple(a),('gate',link['portal'],0))
            v=self.anchor(tuple(b),('gate',link['portal'],1))
            self.connect(u,v,portal=link['portal'],kind=link['kind'])
        self.role=role

    def connect(self,a,b,**fields):
        self.graph.add_edge(a,b,length=math.dist(self.xy[a],self.xy[b]),**fields)

    def face(self,pos):
        point=Point(pos)
        ids=self.tree.query(point,predicate='intersects')
        if len(ids): return int(min(ids))
        return None

    def anchor(self,pos,key):
        i=self.face(pos)
        if i is None: raise ValueError('anchor outside role navigation: '+str(key))
        self.xy[key]=pos
        self.connect(key,i)
        return key

    def path(self,start,goal,opened,combat,actor=None):
        def cost(a,b,e):
            action=0
            if 'portal' in e and e['portal'] not in opened:
                kind=e['kind']
                if actor=='stalker' and kind!='normal':return None
                if self.role=='player':
                    if kind=='break':return None
                    if kind=='window':action=combat['window']['duration_s']
                    if kind=='through':action=combat['portals']['through_player_squeeze_s']
                elif kind!='normal':
                    action=combat['portals'][kind+'_boss_smash_s']
            return e['length']+action*combat[self.role]['speed_mps']
        try:return nx.shortest_path(self.graph,start,goal,weight=cost)[1:]
        except nx.NetworkXNoPath:return []


def step_to(a,b,amount):
    d=math.dist(a,b)
    if d<=amount:return b
    return tuple(x+(y-x)*amount/d for x,y in zip(a,b))
