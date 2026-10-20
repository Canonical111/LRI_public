"""Default preserves legacy primal arithmetic; reordered path is explicit opt-in."""
import warnings
from .compat import run_reference_order
from .solver import run as _packed

def run(alpha,cfg,*,tangent=False,backend='ordered',sector_workers=1,**kwargs):
    if backend=='ordered':
        if sector_workers!=1:raise ValueError('Default ordered kernel uses BLAS threading, sector_workers must be 1')
        r=run_reference_order(alpha,cfg,tangent=tangent,**kwargs)
        r['backend']='ordered';r['sector_workers']=1
        return r
    warnings.warn('Experimental reordered backend: late critical flows can drift under rounding; retune and compare interior windows. No speed advantage is guaranteed.', RuntimeWarning, stacklevel=2)
    return _packed(alpha,cfg,tangent=tangent,backend=backend,sector_workers=sector_workers,**kwargs)

def run_tangent(alpha,cfg,**kwargs):return run(alpha,cfg,tangent=True,**kwargs)
