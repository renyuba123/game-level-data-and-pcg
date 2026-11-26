"""Synthetic calculator fixtures only. These are NOT simulated battle results."""
from .contracts import SCHEMA
from .scoring import default_config

def example_measurements():
    cfg=default_config()
    def observation(value,name):
        return {'value':value,'unit':cfg['metrics'][name]['unit'],'sample_count':12,'state':'measured','evidence':['synthetic://hand-calculation']}
    d={'schema_version':SCHEMA,'evidence_kind':'synthetic_test','layout_hash':'a'*64,'combat_config_hash':'b'*64,
       'checks':dict.fromkeys(['geometry','topology','combat_rules'],'VALID'),'space':{},'phases':{},'episodes':[]}
    for name in cfg['weights']['S']:d['space'][name]=observation(.2,name)
    for phase in ['phase1','phase2']:
        d['phases'][phase]={}
        for group in ['F','P','D']:
            for name in cfg['weights'][group]:
                if name=='win_fraction':continue
                spec=cfg['metrics'][name];v=sum(spec['target'])/2 if spec['curve']=='band' else .8
                d['phases'][phase][name]=observation(v,name)
    for i in range(12):
        outcome='victory' if i<8 else 'death'
        d['episodes'].append({'schema_version':SCHEMA,'episode_id':f'ep{i}','individual_id':'g0_i0',
          'policy':['output','occlusion','supply'][i//4],'scenario_seed':i%4,'layout_hash':'a'*64,'combat_config_hash':'b'*64,
          'duration_s':60,'phase_durations_s':{'phase1':30,'phase2':30},'outcome':outcome,'phase2_reached':True,
          'events':[{'id':'0','t':0,'kind':'spawn','data':{}},{'id':'1','t':30,'kind':'split','data':{}},{'id':'2','t':60,'kind':outcome,'data':{}}]})
    return d
