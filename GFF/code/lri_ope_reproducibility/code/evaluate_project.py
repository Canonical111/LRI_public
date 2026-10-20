#!/usr/bin/env python3
"""Calculate a2..a6, cross-check the thermal map, and upgrade exact d=2 masters.
Uses fixed master inputs rather than rerunning every graph. The high-precision
arithmetic is not a statement that numerically supplied d=3 masters have that
precision. The full graph and spectral checks are separate run.py tasks.
"""
from __future__ import annotations
import argparse,csv,json,sys
from pathlib import Path
import mpmath as mp
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'code/a6'))
sys.path.insert(0,str(ROOT/'code/relations'))
from calculate_a6 import coefficients,serial,d1_inputs
from relations import from_thermal,omega_two

def thermal(d,inp):
    q=mp.mpf(d)/4;A=mp.digamma(2*q)-2*mp.digamma(q)+mp.digamma(1)
    R=mp.polygamma(1,2*q)-mp.polygamma(1,1);U=mp.polygamma(2,q)
    V=mp.polygamma(2,1)+mp.polygamma(2,2*q);X=mp.polygamma(3,2*q)-mp.polygamma(3,1)
    T,P,P5,K,L,Z=[mp.mpf(inp[k]) for k in ('T','P4','P5','K','L','Z')]
    return {2:A/9,3:(A*A+R)/108-T/81,
            4:(16*P-A**3-mp.mpf(4)/3*A*T-3*A*R+mp.mpf(53)/2*U-3*V)/648,
            5:(-1536*(P5+K)+384*A*P-576*L-48*T*T+120*A*A*T+168*T*R+7152*Z-15*A**4-90*A*A*R+414*A*U-108*A*V-117*R*R-75*X)/46656}

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output-dir',type=Path,default=ROOT/'results');ap.add_argument('--precision',type=int,default=65)
    a=ap.parse_args()
    if a.precision<35:ap.error('precision must be at least 35')
    out=a.output_dir;out.mkdir(parents=True,exist_ok=True);mp.mp.dps=a.precision
    report={'arithmetic_digits':a.precision,'dimensions':{},'qualification':'Formula evaluation, with shared master inputs. Only d=1,2 exact-expression inputs are arbitrarily refinable; d=3 nonprimitive masters have roughly ten stable displayed digits, not certified intervals.'}
    for d in (1,2,3):
        if d==1:
            allinp=d1_inputs();inp={k:allinp[k] for k in ('T','P4','P5','K','L','Z')}
        else:inp={k:mp.mpf(v) for k,v in json.loads((ROOT/f'data/a6/d{d}_inputs.json').read_text()).items()}
        historical=dict(inp)
        if d==2:
            # Updated closed identities in the supplied 2026-10-15 thermal note.
            inp['K']=32*mp.catalan**2-28*mp.zeta(3)*mp.log(2)
            inp['L']=-2*mp.log(2)*inp['P4'];inp['Z']=4*mp.catalan*inp['T']/6
        c=coefficients(d,**inp);th=thermal(d,inp);om=13*inp['Z']-inp['L']-12*inp['K']
        mapped=from_thermal(d,th[3],th[4],th[5],om)
        residual=max(abs(mapped['a_coefficients'][k]-c['coefficients'][k]) for k in range(2,7))
        if residual>mp.mpf('1e-50'):raise AssertionError(('thermal mapping',d,residual))
        row={'masters':inp,'a':c['coefficients'],'h':c['h'],'thermal':th,'log_coefficients':mapped['log_coefficients'],'mapping_max_residual':residual}
        if d==2:
            special=from_thermal(d,th[3],th[4],th[5])
            row['closed_d2_mapping_max_residual']=max(abs(special['a_coefficients'][k]-c['coefficients'][k]) for k in range(2,7))
            row['a6_change_from_historical_master_rounding']=c['coefficients'][6]-coefficients(d,**historical)['coefficients'][6]
        report['dimensions'][str(d)]=row
    (out/'coefficients.json').write_text(json.dumps(serial(report),indent=2)+'\n')
    with (out/'coefficient_table.csv').open('w',newline='') as f:
        wr=csv.writer(f);wr.writerow(['d']+[f'a{k}' for k in range(2,7)])
        for d,r in report['dimensions'].items():wr.writerow([d]+[mp.nstr(r['a'][k],18) for k in range(2,7)])
    assert all(mp.isfinite(r['a'][6]) for r in report['dimensions'].values())
    print(json.dumps({d:{f'a{k}':mp.nstr(r['a'][k],18) for k in range(2,7)} for d,r in report['dimensions'].items()},indent=2))
if __name__=='__main__':main()
