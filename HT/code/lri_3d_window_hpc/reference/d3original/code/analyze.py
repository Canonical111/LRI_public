from pathlib import Path
import json,csv,re,hashlib,sys
ROOT=Path(__file__).resolve().parents[1]

def main():
    fingerprint=hashlib.sha256(b''.join(f.read_bytes() for f in sorted((ROOT/'code/d3dressed').glob('*.py')))).hexdigest()
    rows=[]
    for folder in sorted((ROOT/'results').iterdir()):
        if not folder.is_dir() or not(re.fullmatch(r'L\d+',folder.name) or folder.name.startswith('refine_L')):continue
        for f in sorted(folder.glob('*.json')):
            if f.name.startswith('FAILED'):continue
            r=json.loads(f.read_text())
            if r['source_fingerprint']!=fingerprint:raise RuntimeError(f'Stale numerical source fingerprint: {f}')
            if r['tuning_residual']>1e-8 or r['max_eigenvector_residual']>2e-7:raise RuntimeError(f'Failed gate: {f}')
            r['group']=folder.name;r['file']=str(f.relative_to(ROOT));rows.append(r)
    mainrows=[r for r in rows if r['group'].startswith('L')]
    fields=['group','bath_cut','nz_per_parity','auxiliary_oscillator_size','Delta_sigma_input','s','epsilon','Delta_thermal','Delta_sigma_measured','Delta_shadow_measured','r','g','dimension','bath_singlets','full_bath_dimension','tuning_residual','max_eigenvector_residual','point_seconds_including_operators','file']
    rows.sort(key=lambda r:(r['bath_cut'],r['nz_per_parity'],r['delta']))
    with (ROOT/'results/curve_points.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
    refs=[]
    for r in rows:
        if not r['group'].startswith('refine'):continue
        b=next(a for a in mainrows if a['bath_cut']==r['bath_cut'] and a['delta']==r['delta'])
        refs.append({'L':r['bath_cut'],'x':r['delta'],'main':b['Delta_thermal'],'refined':r['Delta_thermal'],'change':r['Delta_thermal']-b['Delta_thermal'],'caps_main':[b['nz_per_parity'],b['auxiliary_oscillator_size']],'caps_refined':[r['nz_per_parity'],r['auxiliary_oscillator_size']]})
    summary={'main_curve_points':len(mainrows),'refinement_points':len(refs),'all_curve_points':len(rows),'x_min':min(r['delta'] for r in rows),'x_max':max(r['delta'] for r in rows),'cutoffs':sorted(set(r['bath_cut'] for r in mainrows)),
             'max_tuning_residual':max(r['tuning_residual'] for r in rows),'max_eigenvector_residual':max(r['max_eigenvector_residual'] for r in rows),'max_orthogonality_residual':max(r['max_orthogonality_residual'] for r in rows),
             'max_dimension_both_field_sectors':max(r['dimension'] for r in rows),'max_local_refinement_change':max(abs(a['change']) for a in refs),'source_fingerprint':fingerprint,'refinements':refs,'scope':'Raw finite product-cutoff gaps, no continuum extrapolation or physical confidence band'}
    (ROOT/'results/SUMMARY.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))
    with (ROOT/'results/table.md').open('w') as f:
        f.write('| x | L=4 | L=6 | L=8 | L=10 | L=12 |\n|---:|---:|---:|---:|---:|---:|\n')
        for x in sorted(set(r['delta'] for r in mainrows),reverse=True):
            vals=[next(r['Delta_thermal'] for r in mainrows if r['delta']==x and r['bath_cut']==L) for L in [4,6,8,10,12]]
            f.write('| '+f'{x:.7g}'+' | '+' | '.join(f'{v:.12f}' for v in vals)+' |\n')
if __name__=='__main__':main()
