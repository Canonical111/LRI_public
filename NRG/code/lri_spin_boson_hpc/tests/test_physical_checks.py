"""Extra consistency tests; no physical coefficients used as solver targets."""
import contextlib,io
from pathlib import Path
import numpy as np
from lri_spin import Config,run,run_tangent
from lri_spin.workflow import critical
from lri_spin.validation import audit_tangent
from critical import find_critical
from nrg_tangent import run_tangent as ref_tangent


def test_complete_critical_workflow(tmp_path):
    cfg=Config(s=.8,Lambda=3,keep=16,nb=6,nsites=32)
    with contextlib.redirect_stdout(io.StringIO()):
        old=find_critical(cfg,tmp_path/'old',atol=2e-12)
    new=critical(cfg,tmp_path/'new',atol=2e-12)
    assert abs(old['alpha']-new['critical_flow']['alpha'])<2e-12
    ref=ref_tangent(old['alpha'],cfg);got=new['tangent']
    e0=audit_tangent(ref)['selected']['Delta_E'];e1=audit_tangent(got)['selected']['Delta_E']
    assert abs(e0-e1)<1e-8
    for a,b in zip(ref['records'],got['records']):
        np.testing.assert_allclose(a['odd_gap'],b['odd_gap'],atol=1e-8,rtol=2e-10)
        np.testing.assert_allclose(a['d_alpha_odd_gap'],b['d_alpha_odd_gap'],atol=1e-8,rtol=2e-8)
