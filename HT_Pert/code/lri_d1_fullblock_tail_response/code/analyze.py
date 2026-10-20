"""Collect complete source responses and exact asymptotic comparisons; no fitting."""
from pathlib import Path
import json,csv,math,sys
ROOT=Path(__file__).resolve().parents[1]

def write(name,rows):
    with (ROOT/'results'/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    rows=[]
    for scheme in ['raw','dconn']:
      for path in sorted((ROOT/'results').glob(f'{scheme}_*_L*_d8.json')):
        a=json.loads(path.read_text())
        r=dict(mu=a['low_cutoff'],scheme=scheme,operator=a['channel'])
        for n,x in enumerate(a['response']):r[f'response_{n}']=x
        r.update(states=a['basis_dimension'],seconds=a['seconds'],file=str(path.relative_to(ROOT)));rows.append(r)
    rows.sort(key=lambda r:(r['scheme'],r['mu'],r['operator']));write('low_response_coefficients.csv',rows)
    ann=json.loads((ROOT/'results/general_bath_annulus.json').read_text());write('general_bath_annulus.csv',ann)
    summary=dict(complete_low_response_records=len(rows),Dconn_low_cutoffs=sorted({r['mu'] for r in rows if r['scheme']=='dconn'}),raw_low_cutoffs=sorted({r['mu'] for r in rows if r['scheme']=='raw'}),phase_shell_cutoffs=[r['cutoff'] for r in json.loads((ROOT/'results/phase_response_shells.json').read_text())],exact_rational_records=len(list((ROOT/'results').glob('exact_*_d8.json'))),annulus_checks=len(ann),scope='New low-block response and overlap asymptotics, not complete physical C6/C7/C8 tail polynomials.')
    (ROOT/'results/SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
    return rows,summary
if __name__=='__main__':main()
