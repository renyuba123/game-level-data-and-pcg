from common import *
python=WORK/'.venv/Scripts/python.exe'
steps=[('fine_review',[python,WORK/'refine.py','search_v1']),
       ('gates',[GODOT,'--headless','--path',ROOT,'--script','res://scripts/evolution_acceptance.gd']),
       ('navigation',[GODOT,'--headless','--path',ROOT,'--script','res://scripts/candidate_navigation_test.gd']),
       ('states',[python,WORK/'states_review.py']),('regressions',[python,WORK/'test_pipeline.py'])]
try:
    for name,args in steps:
        write_json(WORK/'status.json',{'state':'finalizing','phase':name,'run':'search_v1'})
        print(name,command(args,WORK/f'final_{name}.log',1800),flush=True)
    reviews={}
    for label in ('balanced','exploration','pressure'):
        path=ROOT/f'data/evolution/{label}.json'; c=read_json(path); e=c['evaluation']
        ok=e['fine_review']['valid'] and e['fine_review']['constraint']<=0 and e['heldout']['fairness_loss']<=0
        reviews[label]=ok
        e['status']='Final search: fine-grid, heldout, gates and navigation passed' if ok else 'Final review failed; not recommended'
        write_json(path,c)
    write_json(WORK/'status.json',{'state':'complete' if all(reviews.values()) else 'complete_with_review_failures','run':'search_v1','reviews':reviews})
except Exception as error:
    write_json(WORK/'status.json',{'state':'validation_failed','run':'search_v1','error':str(error)})
    raise
