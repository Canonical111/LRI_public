"""Rebuild tables from complete saved spectra; never fit a continuum intercept."""
from pathlib import Path
import json,csv,sys
import numpy as np
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'code'))
from ht3d.hpc import validate_record

def read(p):return json.loads(p.read_text())
def files(folder):return sorted((R/f'results/{folder}').glob('*.json'))
def rows(folder):
    for p in files(folder):
        if p.name.endswith('.checkpoint.json'):continue
        d=read(p);validate_record(d,d['request_digest']);yield p,d

def write(name,data):
    target=R/'results/tables'/name;target.parent.mkdir(exist_ok=True)
    fields=list(dict.fromkeys(k for row in data for k in row))
    with target.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(data)

def main():
    allrows=[(p,d) for folder in ['curve','raw','local'] for p,d in rows(folder)]
    curve=[];ward=[]
    for p,d in allrows:
        item=dict(x=d['delta'],s=d['s'],epsilon=d['epsilon'],L=d['bath_cut'],window=d['window'],
            nz=d['nz_per_parity'],osc=d['auxiliary_oscillator_size'],local_basis=d.get('local_basis_mode','moving_local_energy'),
            Delta_thermal=d['Delta_thermal'],tuning_residual=d['tuning_residual'],
            eigenvector_residual=d['max_eigenvector_residual'],sector_dimension=d['dimension']//2,
            source=str(p.relative_to(R)))
        if p.parent.name in ['curve','raw']:curve.append(item)
        for w in d.get('diagnostics',{}).get('records',[]):ward.append(dict(item,**w))
    curve.sort(key=lambda d:(d['x'],d['window'],d['L']));write('curve.csv',curve);write('all_ward_candidates.csv',ward)
    xs=sorted({d['x'] for d in curve});comparison=[];first=[];local=[];rawdiff=[]
    for x in xs:
        raw=next(d for p,d in allrows if p.parent.name=='raw' and d['delta']==x)
        old=read(next((R/'reference/d3original/results/L10').glob(f'*_x{x:.8f}.json')))
        rawdiff.append(dict(x=x,thermal_difference=raw['Delta_thermal']-old['Delta_thermal'],
            max_ten_gap_difference=float(np.max(abs(np.r_[raw['even_gaps'],raw['odd_gaps']]-np.r_[old['even_gaps'],old['odd_gaps']])))))
        out=dict(x=x,raw_L10=raw['Delta_thermal'])
        for L in [6,8,10,12]:
            pair=[(p,d) for p,d in allrows if p.parent.name=='curve' and d['delta']==x and d['bath_cut']==L]
            if not pair:continue
            p,d=pair[0];out[f'window_L{L}']=d['Delta_thermal']
            if L==10:
                for fam in ['sigma','thermal','chi']:
                    a=next(w for w in raw['diagnostics']['records'] if w['family']==fam and w['branch']=='P')
                    b=next(w for w in d['diagnostics']['records'] if w['family']==fam and w['branch']=='P')
                    first.append(dict(x=x,family=fam,raw_error=a['spacing_error'],window_error=b['spacing_error'],
                       raw_probability=a['overlap_probability'],window_probability=b['overlap_probability'],
                       raw_ambiguous=a['ambiguous'],window_ambiguous=b['ambiguous']))
        comparison.append(out)
    for p,d in allrows:
        if p.parent.name!='local':continue
        base=read(R/f'results/curve/window_L{d["bath_cut"]}_x{d["delta"]}.json')
        local.append(dict(x=d['delta'],L=d['bath_cut'],test_nz=d['nz_per_parity'],test_osc=d['auxiliary_oscillator_size'],
            test_basis=d.get('local_basis_mode','moving_local_energy'),reference='density16 from teacher L6 z24/osc192',
            thermal_difference=d['Delta_thermal']-base['Delta_thermal'],
            max_ten_gap_difference=float(np.max(abs(np.r_[d['even_gaps'],d['odd_gaps']]-np.r_[base['even_gaps'],base['odd_gaps']]))),
            source=str(p.relative_to(R))))
    write('comparison.csv',comparison);write('first_descendant_comparison.csv',first)
    write('local_convergence.csv',local);write('raw_replays.csv',rawdiff)
    bench=[read(p) for p in sorted((R/'results/benchmarks').glob('L*.json'))]
    write('performance.csv',[{k:v for k,v in b.items() if k not in ['sample','apply_seconds','scope']} for b in bench])
    scalar=max(d['max_eigenvector_residual'] for _,d in allrows)
    angular=max([v['residual'] for _,d in allrows for v in d.get('diagnostics',{}).get('checks',{}).values()]+[0.])
    window=max([v for _,d in allrows if d['window']=='vacuum' for v in
        [d['window_correction']['top_fixed_point_residual'],*d['window_correction']['sublevel_fixed_point_residuals'].values()]]+[0.])
    summary=dict(main_grid_x_count=len(xs),window_curve_records=sum(p.parent.name=='curve' for p,_ in allrows),
        raw_comparisons=15,local_checks=len(local),accepted_primary_records=len(allrows),
        max_tuning=max(d['tuning_residual'] for _,d in allrows),max_scalar_residual=scalar,max_angular_residual=angular,
        max_window_residual=window,max_orthogonality=max(d['max_orthogonality_residual'] for _,d in allrows),
        raw_replay_max_thermal=max(abs(r['thermal_difference']) for r in rawdiff),
        raw_replay_max_ten_gap=max(r['max_ten_gap_difference'] for r in rawdiff),
        local_nested_max_thermal=max(abs(r['thermal_difference']) for r in local if r['test_basis']=='density'),
        local_independent_max_thermal=max(abs(r['thermal_difference']) for r in local if r['test_basis']!='density'),
        max_scalar_sector_dimension=max(d['dimension']//2 for _,d in allrows),
        benchmark_records=len(bench),claim='Finite-cutoff spectra. No continuum extrapolation or new thermal coefficient fit.')
    (R/'results/SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
