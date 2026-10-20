#!/usr/bin/env python3
"""Tabulate complete accepted direct runs only. No continuum fits are made."""
from pathlib import Path
import csv,json,math
import numpy as np
from run import atomic_json
ROOT=Path(__file__).resolve().parents[1]
def save(name,rows):
    if not rows:return
    out=ROOT/'results/tables'/name;out.parent.mkdir(exist_ok=True)
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with out.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
def get(name):
    p=ROOT/'results'/name
    return json.loads(p.read_text()) if p.exists() else None

def main():
    allrows=[];wards=[];records=[]
    for p in sorted((ROOT/'results').glob('*.json')):
        r=json.loads(p.read_text())
        if not isinstance(r,dict) or not r.get('accepted'):continue
        records.append((p.name,r))
        row=dict(file=p.name,x=r['delta'],epsilon=r['epsilon'],s=r['s'],L=r['bath_cut'],nz=r['nz_per_parity'],osc=r['auxiliary_oscillator_size'],
                 window=r['window'],basis='density' if 'basis_provenance' in r else 'moving_energy',Delta_thermal=r['Delta_thermal'],
                 tuning_residual=r['tuning_residual'],eigen_residual=r['max_eigenvector_residual'],seconds=r['elapsed_total_seconds'])
        allrows.append(row)
        for d in r.get('diagnostics',{}).get('records',[]):wards.append({**{k:row[k] for k in ('file','x','L','nz','window','basis')},**d})
    save('all_runs.csv',allrows);save('all_ward_candidates.csv',wards)
    curve=[];comp=[];local=[]
    for x in [.126,.15,.2,.25,.3,.35,.4,.45,.475,.495]:
        tag=f'{x:.3f}';raw=get(f'raw_L10_x{tag}.json');r8=get(f'window_L8_z16_x{tag}.json');r10=get(f'window_L10_z16_x{tag}.json');r12=get(f'window_L12_z16_x{tag}.json');r6=get(f'teacher_L6_x{tag}.json')
        q=dict(x=x,s=2-2*x,epsilon=2-4*x)
        for label,r in [('raw_L10',raw),('window_L6',r6),('window_L8',r8),('window_L10',r10),('window_L12',r12)]:
            if r:q[label]=r['Delta_thermal']
        curve.append(q)
        for fam in ['sigma','thermal','chi']:
            c=dict(x=x,family=fam)
            for label,r in [('raw',raw),('window',r10)]:
                if r:
                    d=next(t for t in r['diagnostics']['records'] if t['family']==fam and t['branch']=='A')
                    for key in ('spacing_error','overlap_probability','ambiguous','rank'):c[f'{label}_{key}']=d[key]
            comp.append(c)
        small=get(f'window_L10_z12_x{tag}.json')
        if small and r10:
            local.append(dict(x=x,L=10,comparison='nested density 12 versus 16',thermal_difference=small['Delta_thermal']-r10['Delta_thermal'],max_low_gap_difference=max(np.max(abs(np.array(small[k])-r10[k])) for k in ('even_gaps','odd_gaps'))))
        large=get(f'refine_L10_z32_x{tag}.json')
        if large and r10:
            local.append(dict(x=x,L=10,comparison='transferred density16 versus independent moving32/256',thermal_difference=r10['Delta_thermal']-large['Delta_thermal'],max_low_gap_difference=max(np.max(abs(np.array(r10[k])-large[k])) for k in ('even_gaps','odd_gaps'))))
        for name in (f'window_L12_z20_x{tag}.json',f'refine_L12_z32_x{tag}.json'):
            large=get(name)
            if large and r12:
                local.append(dict(x=x,L=12,comparison=f'density16 versus {name}',thermal_difference=r12['Delta_thermal']-large['Delta_thermal'],max_low_gap_difference=max(np.max(abs(np.array(r12[k])-large[k])) for k in ('even_gaps','odd_gaps'))))
    save('curve.csv',curve);save('first_descendant_comparison.csv',comp);save('local_convergence.csv',local)
    old=json.loads((ROOT/'inputs/prior_2d_points.json').read_text());replays=[]
    for name,r in records:
        if not name.startswith('raw_L10'):continue
        matches=[o for o in old if abs(o['delta']-r['delta'])<1e-12 and o['bath_cut']==r['bath_cut'] and o['nz_per_parity']==r['nz_per_parity'] and o['auxiliary_oscillator_size']==r['auxiliary_oscillator_size']]
        if matches:
            o=matches[0];replays.append(dict(x=r['delta'],L=r['bath_cut'],new=r['Delta_thermal'],prior=o['Delta_thermal'],difference=r['Delta_thermal']-o['Delta_thermal']))
    save('raw_replays.csv',replays)
    stats=dict(accepted_complete_runs=len(records),main_scan_runs=sum(n.startswith(('teacher_L6','window_L8','window_L10','raw_L10')) for n,r in records),
               max_primary_tuning_residual=max(r['tuning_residual'] for n,r in records),max_scalar_eigen_residual=max(r['max_eigenvector_residual'] for n,r in records),
               max_window_fixedpoint_residual=max([0.]+[max(w['top_fixed_point_residual'],*w['sublevel_fixed_point_residuals'].values()) for n,r in records if (w:=r.get('window_correction'))]),
               max_raw_replay_difference=max([0.]+[abs(r['difference']) for r in replays]),raw_replay_count=len(replays),
               curves=curve,local_convergence=local,scope='Finite-cutoff outputs. No continuum fit or certified physical error bar.')
    atomic_json(ROOT/'results/SUMMARY.json',stats);print(json.dumps({k:v for k,v in stats.items() if k not in ('curves','local_convergence')},indent=2))
if __name__=='__main__':main()
