"""Variable-length graph operators with explicit lineage and bounded repair."""
import copy,random,math
import networkx as nx
from .topology import graph
from .common import digest

def mutate(parent,seed,config):
    rng=random.Random(seed);g=copy.deepcopy(parent);events=[]
    for _ in range(rng.randint(1,3)):
        topology=rng.random()<.5
        op=rng.choice(['add_room','delete_room','add_edge','delete_edge']) if topology else rng.choice(['shape','move','rotate','door','spawn','obstacle'])
        before=digest(g);event={'op':op,'status':'inapplicable'};net=graph(g)
        if op=='add_room' and len(g['rooms'])<config['room_count'][1]:
            occupied={tuple(r['anchor']) for r in g['rooms']};options=sorted({(x+dx,y+dy) for x,y in occupied for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]}-occupied)
            anchor=rng.choice(options);parent_room=rng.choice([r for r in g['rooms'] if math.dist(r['anchor'],anchor)==1])
            room=copy.deepcopy(parent_room);room.update(id='room_'+digest([seed,len(events),before])[:12],anchor=list(anchor),position=[v*4.7 for v in anchor],role='side',width=2.9,height=2.9,shape='chamfer')
            g['rooms'].append(room);g['edges'].append({'id':'edge_'+digest([room['id'],parent_room['id']])[:12],'a':room['id'],'b':parent_room['id'],'kind':'normal'});event.update(status='applied',added_room=room['id'])
        elif op=='delete_room' and len(g['rooms'])>config['room_count'][0]:
            options=[r for r in g['rooms'] if r['id'] not in (g['spawn'],g['boss'],g['exit']) and r['role']=='side' and r['id'] not in {b['room'] for b in g['obstacles']}]
            rng.shuffle(options)
            for room in options:
                trial=net.copy();trial.remove_node(room['id'])
                if nx.is_connected(trial):
                    g['rooms'].remove(room);g['edges']=[e for e in g['edges'] if room['id'] not in (e['a'],e['b'])];event.update(status='applied',deleted_room=room['id']);break
        elif op=='add_edge':
            options=[(a,b) for i,a in enumerate(g['rooms']) for b in g['rooms'][i+1:] if math.dist(a['anchor'],b['anchor'])==1 and not net.has_edge(a['id'],b['id'])]
            if options:
                a,b=rng.choice(options);edge={'id':'edge_'+digest([a['id'],b['id'],seed])[:12],'a':a['id'],'b':b['id'],'kind':'normal'};g['edges'].append(edge);event.update(status='applied',edge=edge)
        elif op=='delete_edge':
            options=[e for e in g['edges'] if e['kind']=='normal'];rng.shuffle(options)
            for e in options:
                trial=net.copy();trial.remove_edge(e['a'],e['b'])
                if nx.is_connected(trial) and len(nx.cycle_basis(trial))>=2:g['edges'].remove(e);event.update(status='applied',edge=e);break
        elif op in ('shape','move','rotate'):
            r=rng.choice(g['rooms']);old=copy.deepcopy(r)
            if op=='shape':r.update(shape=rng.choice(['rectangle','chamfer','trapezoid','L','notch']),width=max(2.4,min(4.2,r['width']*rng.uniform(.9,1.1))),height=max(2.4,min(4.2,r['height']*rng.uniform(.9,1.1))))
            elif op=='rotate':r['rotation']=(r['rotation']+rng.choice([-45,45,90]))%360
            else:r['position']=[v+rng.uniform(-.3,.3) for v in r['position']]
            event.update(status='applied',before=old,after=copy.deepcopy(r))
        elif op=='door':
            a,b=rng.sample(g['edges'],2);a['kind'],b['kind']=b['kind'],a['kind'];event.update(status='applied',swapped=[a['id'],b['id']])
        elif op=='spawn':
            field=rng.choice(['spawn','boss','exit']);old=g[field];options=[r['id'] for r in g['rooms'] if r['id'] not in [g[k] for k in ['spawn','boss','exit'] if k!=field]]
            g[field]=rng.choice(options);event.update(status='applied',field=field,before=old,after=g[field])
        elif op=='obstacle' and g['obstacles']:
            b=rng.choice(g['obstacles']);old=copy.deepcopy(b);b['offset']=[v+rng.uniform(-.1,.1) for v in b['offset']];event.update(status='applied',before=old,after=copy.deepcopy(b))
        event['before_hash']=before;event['after_hash']=digest(g);events.append(event)
    g['operations']=events;return g,events

def crossover(first,second,seed,config):
    """Exchange connected terminal branches at a single compatible interface.

    Bounded one-interface subset of the planned 1–3 interface operator. Failed
    branch exchange is explicit; no claim that all graph crossover is implemented.
    """
    rng=random.Random(seed)
    def branches(g):
        net=graph(g);protected={g[k] for k in ['spawn','boss','exit']}|{b['room'] for b in g['obstacles']}
        result=[]
        for a,b in nx.bridges(net):
            cut=net.copy();cut.remove_edge(a,b)
            for component in nx.connected_components(cut):
                if not component&protected and len(component)<=4:
                    inside=a if a in component else b;outside=b if inside==a else a;result.append((component,inside,outside))
        return result
    aa,bb=branches(first),branches(second);events=[]
    if aa and bb:
        for attempt in range(config['max_repairs']):
            target=rng.choice(aa);donor=rng.choice(bb);count=len(first['rooms'])-len(target[0])+len(donor[0])
            if not config['room_count'][0]<=count<=config['room_count'][1]:continue
            g=copy.deepcopy(first);old={r['id']:r for r in first['rooms']};src={r['id']:r for r in second['rooms']}
            shift=[old[target[1]]['position'][i]-src[donor[1]]['position'][i] for i in range(2)]
            ashift=[old[target[1]]['anchor'][i]-src[donor[1]]['anchor'][i] for i in range(2)]
            remap={r:'room_'+digest([seed,attempt,r])[:12] for r in donor[0]}
            g['rooms']=[r for r in g['rooms'] if r['id'] not in target[0]];g['edges']=[e for e in g['edges'] if not ({e['a'],e['b']}&target[0])]
            for rid in sorted(donor[0]):
                r=copy.deepcopy(src[rid]);r.update(id=remap[rid],position=[r['position'][i]+shift[i] for i in range(2)],anchor=[r['anchor'][i]+ashift[i] for i in range(2)]);g['rooms'].append(r)
            for e in second['edges']:
                if e['a'] in donor[0] and e['b'] in donor[0]:g['edges'].append({**e,'id':'edge_'+digest([seed,attempt,e['id']])[:12],'a':remap[e['a']],'b':remap[e['b']]})
            g['edges'].append({'id':'edge_'+digest([seed,attempt,'interface'])[:12],'a':target[2],'b':remap[donor[1]],'kind':'normal'})
            anchors=[tuple(r['anchor']) for r in g['rooms']]
            if len(set(anchors))!=len(anchors):events.append({'op':'branch_crossover','attempt':attempt,'status':'rejected_anchor_overlap'});continue
            events.append({'op':'branch_crossover','status':'applied','removed':sorted(target[0]),'donor_ids':remap,'interface':[target[2],remap[donor[1]]]});g['operations']=events;return g,events
    child,mutation=mutate(first,seed,config);return child,[*events,{'op':'branch_crossover','status':'fallback_to_single_parent_mutation'},*mutation]
