#!/usr/bin/env python3
"""Compare optimized and larger original local spaces at the same finite regulator.

This audits numerical local convergence only. No thermal CFT/NRG value enters.
Missing references fail the audit rather than receiving a made-up error bar.
"""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from lri_dressed.io import atomic_json,read_envelope,validate_result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input-dirs',nargs='+',required=True);p.add_argument('--output',required=True)
    p.add_argument('--thermal-tol',type=float,default=1e-6);p.add_argument('--gap-tol',type=float,default=1e-5)
    a=p.parse_args();groups={};errors=[];comparisons=[]
    for directory in a.input_dirs:
        for path in sorted(Path(directory).glob('*.json')):
            try:
                rec=read_envelope(path,'result');cfg=rec['config'];row=rec['payload'];validate_result(row,cfg)
                key=tuple(cfg.get(k) for k in ('delta','bath_cut','osc','window','window_mode','zero_scale'))
                groups.setdefault(key,[]).append((path,rec))
            except (OSError,ValueError,TypeError,KeyError) as exc:errors.append({'path':str(path),'error':str(exc)})
    for key,items in groups.items():
        originals=[r for r in items if r[1]['config'].get('local_basis') is None]
        for path,rec in items:
            if rec['config'].get('local_basis') is None:continue
            refs=[r for r in originals if r[1]['config']['nz']>rec['config']['nz']]
            if not refs:
                errors.append({'path':str(path),'error':'No larger original local-space reference at the same regulator/osc/scale'})
                continue
            rpath,reference=max(refs,key=lambda r:r[1]['config']['nz'])
            x,y=rec['payload'],reference['payload']
            thermal=x['Delta_thermal']-y['Delta_thermal']
            gap=max(abs(u-v) for name in ('even_gaps','odd_gaps') for u,v in zip(x[name],y[name]))
            passed=abs(thermal)<=a.thermal_tol and gap<=a.gap_tol
            comparisons.append({'delta':x['delta'],'bath_cut':x['bath_cut'],'keep':rec['config']['nz'],
                'reference_nz':reference['config']['nz'],'result':str(path),'reference':str(rpath),
                'basis_sha256':rec['config']['local_basis']['sha256'],
                'thermal_difference':thermal,'max_common_low_gap_difference':gap,'passed':passed})
    passed=bool(comparisons) and not errors and all(r['passed'] for r in comparisons)
    atomic_json(a.output,{'passed':passed,'comparisons':comparisons,'errors':errors,
                'thermal_tolerance':a.thermal_tol,'gap_tolerance':a.gap_tol,
                'scope':'Local convergence against a specified finite reference; no claim that the reference or physical continuum is converged.'})
    print(f'{len(comparisons)} comparisons; {len(errors)} missing/invalid inputs; passed={passed}')
    return 0 if passed else 1
if __name__=='__main__':raise SystemExit(main())
