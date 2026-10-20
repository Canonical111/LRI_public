"""Compare freshly computed coefficient records with the archived records of the same scheme, cutoff and degree.
Used by the cluster validation job and, independently, by the production gate (check_validation.py), which
recomputes the comparison itself at the fixed tolerance. Exit 0 only if every compared array agrees."""
from pathlib import Path
import argparse, json, sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
RTOL=1e-10
ARRAYS=('C','r','g','energies','vacuum_grid_coefficients')
COUNTS=('basis_dimension','ladder_edges','stored_wavefunction_entries','particle_cap','nonzero_particle_cap')
def compare(new,old,rtol=RTOL):
    """Max relative difference per array (relative to max(1,|old|)); counts must match exactly (inf otherwise)."""
    worst={}
    for k in ARRAYS:
        x,y=np.asarray(new[k],float),np.asarray(old[k],float)
        worst[k]=float('inf') if x.shape!=y.shape else (float(np.max(np.abs(x-y)/np.maximum(1,np.abs(y)))) if y.size else 0.)
    for k in COUNTS:
        if new[k]!=old[k]:worst[k]=float('inf')
    for k in ('cutoff','degree','scheme'):
        if new[k]!=old[k]:worst[k]=float('inf')
    return all(v<=rtol for v in worst.values()),worst
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--new-dir',type=Path,required=True);p.add_argument('--archive-dir',type=Path,default=ROOT/'results/new_coefficients')
    p.add_argument('--rtol',type=float,default=RTOL,help='max |new-old|/max(1,|old|) per entry');p.add_argument('--out',type=Path)
    a=p.parse_args();rows=[];ok=True
    files=sorted(a.new_dir.glob('*_L*_d*.json'))
    if not files:sys.exit(f'no records in {a.new_dir}')
    for f in files:
        ref=a.archive_dir/f.name
        if not ref.exists():rows.append(dict(file=f.name,status='no archived counterpart'));ok=False;continue
        n,o=json.loads(f.read_text()),json.loads(ref.read_text())
        passed,worst=compare(n,o,a.rtol);ok&=passed
        rows.append(dict(file=f.name,status='pass' if passed else 'FAIL',max_rel=worst,seconds_new=n['seconds'],seconds_archived=o['seconds'],
                         maxrss_gib_new=n['maxrss_kib']/2**20,maxrss_gib_archived=o['maxrss_kib']/2**20))
        print(f.name,rows[-1]['status'],{k:f'{v:.1e}' for k,v in worst.items()},flush=True)
    summary=dict(rtol=a.rtol,passed=ok,records=rows)
    if a.out:a.out.write_text(json.dumps(summary,indent=2)+'\n')
    sys.exit(0 if ok else 1)
