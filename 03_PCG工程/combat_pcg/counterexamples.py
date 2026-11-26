"""Scoring-layer counterexamples; geometry/battle scenes are Phase 2 deliverables."""
from .fixtures import example_measurements
from .scoring import score

def run():
    cases=[]
    for name in ['permanent_safe_fire','no_firing_windows','supply_deadlock','zero_damage_loop','wall_shot','room_relabel','early_death','missing_second_stage']:
        m=example_measurements();expect={}
        if name in ['permanent_safe_fire','supply_deadlock','wall_shot']:
            m['checks']['combat_rules']='INVALID';expect={'status':'INVALID'}
        elif name=='no_firing_windows':
            for p in m['phases'].values():p['shooting_window_fraction']['value']=0.
            expect={'P_below':70}
        elif name=='zero_damage_loop':
            for e in m['episodes']:e['outcome']='timeout';e['events'][-1]['kind']='timeout'
            expect={'status':'UNCERTAIN','selection':False}
        elif name=='room_relabel':
            # Extra decorative labels are not consumed by the scoring kernel.
            m['decorative_room_labels']=['R05']*100;expect={'S_equals':80}
        else:
            for e in m['episodes']:
                duration=1 if name=='early_death' else 60
                e.update(outcome='death',phase2_reached=False,duration_s=duration,phase_durations_s={'phase1':duration,'phase2':0})
                e['events']=[e['events'][0],{'id':'end','t':duration,'kind':'death','data':{}}]
            m['phases']['phase2']={};expect={'status':'UNCERTAIN','P_below':2 if name=='early_death' else 49}
        r=score(m);passed=True
        for key,value in expect.items():
            if key=='status':passed &= r['status']==value
            elif key=='selection':passed &= r['formal_selection_allowed']==value
            elif key=='P_below':passed &= r['scores'] is not None and r['scores']['P']<value
            elif key=='S_equals':passed &= r['scores'] is not None and r['scores']['S']==value
        cases.append({'case':name,'passed':bool(passed),'expected':expect,'status':r['status'],'scores':r['scores'],
            'evidence':'synthetic calculator input; hard-rule flags are injected, NOT automatically discovered from geometry'})
    return cases
