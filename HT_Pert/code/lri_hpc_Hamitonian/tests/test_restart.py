import os,sys,json,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np,numba
numba.set_num_threads(2)
from lri_hpc.solver import compute,atomic_json
with tempfile.TemporaryDirectory() as tmp:
 t=Path(tmp);cp=t/'checkpoint.json';cache=t/'basis'
 a=compute(12,'thermal',7,checkpoint=cp,basis_cache=cache)
 b=compute(12,'thermal',7,checkpoint=cp,basis_cache=cache)
 assert a==b
 # Simulate interruption after tuning and the first reference quotient.
 saved=json.loads(cp.read_text());saved.pop('result');saved['components']={k:v for k,v in saved['components'].items() if k=='0'}
 atomic_json(cp,saved)
 c=compute(12,'thermal',7,checkpoint=cp,basis_cache=cache)
 for k in ['C','r','g']:np.testing.assert_allclose(a[k],c[k],atol=1e-7,rtol=2e-11)
 try:compute(14,'thermal',7,checkpoint=cp)
 except ValueError:pass
 else:raise AssertionError('Mismatched checkpoint was accepted')
 try:compute(100,'thermal',7,memory_limit_gib=.01)
 except MemoryError:pass
 else:raise AssertionError('Unsafe allocation not refused')
 print('cache, partial restart, configuration mismatch, and preflight checks PASS')
