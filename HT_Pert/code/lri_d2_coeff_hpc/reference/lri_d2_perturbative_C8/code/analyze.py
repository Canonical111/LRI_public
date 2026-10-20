"""Publish direct coefficients and validation statistics; no continuum fitting."""
from pathlib import Path
import csv,json,math
import numpy as np
ROOT=Path(__file__).resolve().parents[1]

def write(name,rows):
    with (ROOT/'results'/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    records=[];by={}
    for f in sorted((ROOT/'results/coefficients').glob('*_d8.json')):
        a=json.loads(f.read_text());by[a['scheme'],a['cutoff']]=a
        row=dict(scheme=a['scheme'],L=a['cutoff'])
        row.update({f'C{k}':v for k,v in enumerate(a['C'])})
        row.update(auxiliary_states=a['auxiliary_states'],scalar_even_states=a['scalar_reference_dimensions'][0],scalar_odd_states=a['scalar_reference_dimensions'][1],seconds=a['seconds'],peak_rss_GiB=a['maxrss_kib']/2**20,angular_envelope=a.get('exact_angular_envelope',False),source=str(f.relative_to(ROOT)))
        records.append(row)
    records.sort(key=lambda a:(a['scheme'],a['L']));write('coefficients_C0_C8.csv',records)
    shifts=[]
    for L in range(0,21,2):
        a=by['consistent',L];b=by['raw',L];row=dict(L=L)
        row.update({f'delta_C{k}':a['C'][k]-b['C'][k] for k in range(9)});shifts.append(row)
    write('window_shifts.csv',shifts)
    degrees=[]
    for f in (ROOT/'results/coefficients').glob('*_d7.json'):
        a=json.loads(f.read_text());b=by[a['scheme'],a['cutoff']]
        err=np.array(a['C'])-b['C'][:8]
        degrees.append(dict(L=a['cutoff'],max_absolute=float(np.max(abs(err))),max_scaled=float(np.max(abs(err)/np.maximum(1,abs(np.array(b['C'][:8]))))),degree7_states=a['auxiliary_states'],degree8_states=b['auxiliary_states']))
    assert degrees and all(r['max_scaled']<5e-12 for r in degrees)
    write('degree_support_checks.csv',sorted(degrees,key=lambda r:r['L']))
    a=by['consistent',20];b=by['raw',20]
    out=dict(main_orders=list(range(9)),main_cutoffs=list(range(0,21,2)),raw_records=11,consistent_records=11,literal_control_cutoffs=[2,4,8,12],exact_rational_cutoffs=[0,2,4,6],largest_C=a['C'],largest_raw_C=b['C'],largest_auxiliary_states=a['auxiliary_states'],largest_scalar_even=a['scalar_reference_dimensions'][0],largest_scalar_odd=a['scalar_reference_dimensions'][1],largest_seconds=a['seconds'],largest_peak_rss_GiB=a['maxrss_kib']/2**20,largest_tuning_residual=a['tuning_residual'],degree_overlap_checks=degrees,
        continuum_C2=4*math.log(2)/9,highest_cutoff_C2_defect=a['C'][2]-4*math.log(2)/9,
        physical_C3_C8_continuum_determined=False,full_matching_completed=False,source='uploaded total-bath-mode cutoff Hamiltonian; no thermal value is tuned',algorithm='exact symmetry-reduced Taylor recursion with stationary quotient; no epsilon fit')
    (ROOT/'results/SUMMARY.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
    return records,shifts,out
if __name__=='__main__':main()
