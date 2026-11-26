"""Phase 1 commands. No pretend experiment/generate implementation."""
import argparse,io,json,sys,unittest
from pathlib import Path
from .scoring import score,default_config
from .fixtures import example_measurements
from .protocol import default_combat,validate_combat,formal_preflight
from .counterexamples import run

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['check','example','score','preflight']);p.add_argument('--input',type=Path);p.add_argument('--output',type=Path);a=p.parse_args();exit_code=0
    if a.command=='check':
        names=['combat_pcg.test_contracts','combat_pcg.test_scoring','combat_pcg.test_spatial','combat_pcg.test_protocol','combat_pcg.test_event_order','combat_pcg.test_boundary_score']
        output=io.StringIO();result=unittest.TextTestRunner(stream=output,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(names))
        data={'phase':'1','tests_run':result.testsRun,'success':result.wasSuccessful(),'test_log':output.getvalue(),
              'counterexamples':run(),'protocol':validate_combat(default_combat()),'formal_preflight':formal_preflight(default_combat(),default_config())}
        exit_code=0 if result.wasSuccessful() else 1
    elif a.command=='preflight':
        data=formal_preflight(default_combat(),default_config());exit_code=0 if data['allowed'] else 2
    else:
        if a.command=='score' and a.input is None:p.error('score requires --input')
        data=score(example_measurements() if a.command=='example' else json.loads(a.input.read_text(encoding='utf-8-sig')))
        exit_code=1 if data['status']=='ERROR' else 0
    if a.output:
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
        print(json.dumps({'output':str(a.output),'status':data.get('status'),'success':data.get('success'),'tests':data.get('tests_run'),'allowed':data.get('allowed')},ensure_ascii=False))
    else:print(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False))
    raise SystemExit(exit_code)
if __name__=='__main__':main()
