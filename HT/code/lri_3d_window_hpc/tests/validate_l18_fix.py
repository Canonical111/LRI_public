"""Fresh low-cutoff spectrum and forced-fallback validation, no stale pass flags."""
from pathlib import Path
import sys,json,importlib.util,time,os,tempfile
_numba_cache=tempfile.TemporaryDirectory(prefix="ht3d-fix-validation-")
os.environ["NUMBA_CACHE_DIR"]=_numba_cache.name
if sys.flags.optimize:raise RuntimeError('Validation requires Python assertions enabled')
ROOT=Path(__file__).resolve().parents[1]
for k in ('OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS'):os.environ[k]='1'
sys.path.insert(0,str(ROOT/'code'))
import numpy as np
from threadpoolctl import threadpool_limits
from unittest.mock import patch
from ht3d.hpc import atomic_json,source_hash
from ht3d import basis
from ht3d.operators import ProductOperator
from ht3d.density import DensitySolver
from ht3d.projector_preflight import census
spec=importlib.util.spec_from_file_location('fix_baseline',ROOT/'reference/performance_0_2_0/code/ht3d/__init__.py',
    submodule_search_locations=[str(ROOT/'reference/performance_0_2_0/code/ht3d')])
m=importlib.util.module_from_spec(spec);sys.modules['fix_baseline']=m;spec.loader.exec_module(m)
from fix_baseline.basis import SphereBathBasis as OriginalBasis
from fix_baseline.operators import ProductOperator as OriginalOperator
from fix_baseline.density import DensitySolver as OriginalSolver
out=ROOT/'validation/l18_fix/current_checks.json'
r={'passed':False,'source_sha256':source_hash(),'status':'running','scope':'fresh finite-matrix regression and fallback; not an L18/L20 full solve'}
atomic_json(out,r);t=time.perf_counter()
try:
 with threadpool_limits(limits=1,user_api='blas'):
    controls=[]
    for J in (0,1,2):
        b=basis.SphereBathBasis.build(6);old=OriginalBasis.build(6)
        a=ProductOperator(b,.6,4,J);c=OriginalOperator(old,.6,4,J)
        for key in ('data','indices','indptr'):
            np.testing.assert_array_equal(getattr(a.S,key),getattr(c.S,key))
        for W,V in zip(a.W,c.W):
            for key in ('data','indices','indptr'):np.testing.assert_array_equal(getattr(W,key),getattr(V,key))
        bf=basis.SphereBathBasis.build(6)
        with patch.object(basis,'null_space',side_effect=np.linalg.LinAlgError('injected fallback')):
            f=ProductOperator(bf,.6,4,J)
        R=a.S.T@f.S
        err=max(float(np.max(abs((R.T@W@R-V).data),initial=0.)) for W,V in zip(a.W,f.W))
        assert err<3e-12
        controls.append(dict(L=6,spin=J,default_projector_bit_equal=True,default_vertices_bit_equal=True,
                             fallback_vertices_max_abs=err,fallback_blocks=f.projection_tests['svd_statistics']['gesvd_fallbacks']))
    spectra=[]
    for x in (.6,.5182):
        teacher=json.loads((ROOT/f'reference/baseline/results/curve/teacher_L6_x{x:g}.json').read_text())
        art=teacher['basis_artifact'];u=np.asarray(art['isometry']);k=u.shape[1]//2
        u=u[:,[*range(16),*range(k,k+16)]]
        for window in ('none','vacuum'):
            vals=[]
            for cls in (OriginalSolver,DensitySolver):
                s=cls(8,u,art['scale'],window=window,backend='tensor',eig_tol=1e-12,ncv=40,residual_tol=1e-8)
                s.set_delta(x);row=s.solve(teacher['theta'],tol=3e-11,maxiter=50)
                vals.append(row)
            a=np.r_[vals[0]['even_gaps'],vals[0]['odd_gaps']]
            b=np.r_[vals[1]['even_gaps'],vals[1]['odd_gaps']]
            err=float(np.max(abs(a-b)))
            assert err<1e-10
            spectra.append(dict(L=8,x=x,window=window,maximum_gap_difference=err,
                bit_equal=np.array_equal(a,b),reference=vals[0],patched=vals[1]))
    r.update(passed=True,status='complete',operator_checks=controls,spectral_checks=spectra,
        exact_large_counts=[census(L,spins=(0,1,2)) for L in (18,20)])
except Exception as exc:
    r.update(status='failed',error=f'{type(exc).__name__}: {exc}');raise
finally:
    r['elapsed_seconds']=time.perf_counter()-t
    atomic_json(out,r)
print(json.dumps({'passed':r['passed'],'seconds':r['elapsed_seconds'],
     'spectrum_max':max(s['maximum_gap_difference'] for s in r.get('spectral_checks',[]))}))
