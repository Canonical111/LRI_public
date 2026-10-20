"""Check `make smoke`: one small critical search with the production solver and with the independent solver.

Usage  python verify/smoke_check.py SMOKE_DIR
       SMOKE_DIR/production/result.json      written by  python -m lri_spin critical ... (code/lri_spin_boson_hpc)
       SMOKE_DIR/independent/toy40.json      written by  python independent_check/run_config.py toy40
Compares both with verify/smoke_expected.json and with each other; prints a table and exits 1 on any failure.
The configuration (Lambda = 3, s = 0.8, K = 16, n_b = 6, N = 40) is far from converged: it tests the code path, not physics.
"""
import json,sys
from pathlib import Path

HERE=Path(__file__).resolve().parent


def main():
    d=Path(sys.argv[1]);E=json.loads((HERE/'smoke_expected.json').read_text())
    p=json.loads((d/'production'/'result.json').read_text())['payload']
    i=json.loads((d/'independent'/'toy40.json').read_text())
    pa=p['critical_flow']['alpha'];pr=p['analysis']['quality_window_range'];pn=p['analysis']['number_of_quality_windows']
    h=i['window_audit'][E['independent_h']]['summary']
    ia=i['critical_search']['alpha_c'];ir=[h['delta_E_min'],h['delta_E_max']];inq=h['n_quality']
    rows=[]
    def chk(name,got,ref,tol,rel=False):
        diff=abs(got/ref-1) if rel else abs(got-ref)
        rows.append((name,got,ref,diff,tol,diff<=tol))
    chk('production alpha_c',pa,E['alpha_c'],E['alpha_rtol'],rel=True)
    chk('production quality range, low',pr[0],E['quality_range'][0],E['range_atol'])
    chk('production quality range, high',pr[1],E['quality_range'][1],E['range_atol'])
    chk('production quality windows',pn,E['n_quality'],0)
    chk('independent alpha_c vs production',ia,pa,E['alpha_rtol'],rel=True)
    chk('independent quality range, low vs production',ir[0],pr[0],E['range_atol'])
    chk('independent quality range, high vs production',ir[1],pr[1],E['range_atol'])
    chk('independent quality windows vs production',inq,pn,0)
    w=max(len(r[0]) for r in rows)
    for n,g,r,df,t,ok in rows:print(f'{n:<{w}}  {g!r:<22} expected {r!r:<22} |diff| {df:.1e} (tol {t:g})  {"PASS" if ok else "FAIL"}')
    bad=[r for r in rows if not r[5]]
    print('SMOKE','FAIL' if bad else 'PASS',f'({len(rows)-len(bad)}/{len(rows)} checks)')
    sys.exit(1 if bad else 0)


if __name__=='__main__':
    main()
