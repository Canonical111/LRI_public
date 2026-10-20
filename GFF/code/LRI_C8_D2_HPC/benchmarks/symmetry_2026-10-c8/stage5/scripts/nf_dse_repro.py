# Diagnosis of the final J-VAL-1 test_numerics_flags failure (f2_profile, case dse): recompute() returns numpy.float64,
# and repr() of a numpy>=2 scalar is "np.float64(...)", which tests/fake_worker.py cannot parse as C8_FAKE_PROFILE_DELTA.
# Usage: python3 -B nf_dse_repro.py PACKAGE  (fake workers only; seconds)
import sys,json,math,tempfile,os
from pathlib import Path
pkg=Path(sys.argv[1]);sys.path.insert(0,str(pkg/'tests'));os.chdir(pkg)
import test_numerics_flags as T
with tempfile.TemporaryDirectory(prefix='c8d2_nfdbg_')as td:
    td=Path(td);x=T.fakes(td);args=['--profile','dd','--profile-exe',x['c8d2_gmp_dd'],'--exact',x['c8d2_gmp'],*T.SMALL,'--parts','F2']
    cp,r=T.flags(td,'d12',*args,env={'C8_FAKE_PROFILE_DELTA':'1e-12'});print('d12',cp.returncode)
    ind=T.recompute(td,'d12',4);mu,se=ind['total'];delta=1e-12*0.062/(abs(mu)+1.5*se);print('mu',mu,'se',se,'delta',delta)
    cp,r=T.flags(td,'dse',*args,'--f2-max-doublings','1',env={'C8_FAKE_PROFILE_DELTA':repr(delta)})
    print('dse rc',cp.returncode);print('STDOUT',cp.stdout[-2500:]);print('STDERR',cp.stderr[-2500:]);print('rec keys',None if r is None else {k:(type(v).__name__) for k,v in r.items()})
    if r:print(json.dumps({k:r.get(k) for k in ('status','F2')},default=str)[:2000])
