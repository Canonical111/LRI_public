"""Run tests/test_pipeline.py parts of a tree (argv[1]) with every Stage-6 fix-round-4 (G3) test function wrapped: its
failure is recorded (FAIL name: exception) and the part continues, so each new test is seen to fail or pass on that
tree's code independently."""
import json,sys
from pathlib import Path
root=Path(sys.argv[1]);out=Path(sys.argv[2]);parts=sys.argv[3].split(',')
sys.path.insert(0,str(root/'tests'))
sys.argv=[str(root/'tests/test_pipeline.py')]
import test_pipeline as tp
rec=[]
def wrap(name):
    fn=getattr(tp,name)
    def w(*a,**k):
        try:
            r=fn(*a,**k);rec.append(dict(test=name,passed=True));print('NEW PASS',name,flush=True);return r
        except Exception as e:
            rec.append(dict(test=name,passed=False,error=f'{type(e).__name__}: {str(e)[:600]}'));print('NEW FAIL',name,f'{type(e).__name__}: {str(e)[:300]}',flush=True)
            return None
    setattr(tp,name,w)
for n in ('w12_batches','route_b_synthetic','w10_calibration_checkpoints','w20_sweep_seed','w11_rates_calibration','route_b_cli_test_only',
          'pilot_exact_gated_nontest','route_b_nontest'):wrap(n)
import tempfile
with tempfile.TemporaryDirectory(prefix='c8d2_before_')as td:
    X=tp.Pkg(Path(td))
    for name,fn in tp.PARTS:
        if name in parts:
            try:fn(X)
            except Exception as e:print('PART ABORTED',name,f'{type(e).__name__}: {str(e)[:300]}',flush=True);rec.append(dict(test=f'{name} (rest of the part)',passed=False,error=f'{type(e).__name__}: {str(e)[:600]}'))
out.write_text(json.dumps(dict(tree=str(root),new_tests=rec,other_tests=[t['test']for t in tp.RESULTS]),indent=1)+'\n')
print(json.dumps({'new':{r['test']:r['passed']for r in rec},'other_passed':len(tp.RESULTS)}))
