#!/usr/bin/env python3
"""Generate sensitivity CSV/TeX tables from review reruns, optionally embedding them.
The note stays standalone: --update-note copies table text between named markers.
"""
from pathlib import Path
import argparse,csv,json,re
ROOT=Path(__file__).resolve().parents[2]
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--update-note',action='store_true');args=ap.parse_args()
    out=ROOT/'outputs/tables';out.mkdir(exist_ok=True)
    gaps=json.loads((ROOT/'outputs/review_validation/gaps/summary.json').read_text())['cases']
    boxes=json.loads((ROOT/'outputs/review_validation/boxes/summary.json').read_text())['cases']
    nominal=next(c for c in gaps if c['even_gap']==8 and c['odd_gap']==7 and c['padding']==1)
    boxrows=sorted(boxes+[nominal],key=lambda c:c['multiplier'])
    sections={}
    def interval(c):
        return f"$[{c['interval'][0]:.8f},\\;{c['interval'][1]:.8f}]$" if c['status']=='completed' else r'\textbf{Infeasible}'
    def wrap(header,rows,caption):
        return '\\begin{center}\n\\begin{tabular}{@{}rrl@{}}\\toprule\n'+header+r'\\\midrule'+'\n'+'\n'.join(rows)+'\n\\bottomrule\n\\end{tabular}\n\\end{center}\n'+caption
    rows=[f"{c['multiplier']:g} & $\\pm{2*c['multiplier']:g}$ & {interval(c)} \\\\" for c in boxrows]
    sections['BOX']=wrap('$m$ & Box radius (quoted errors) & Ten-update numerical interval',rows,
        r'The physical $h_{\eps\prime}$ window remains fixed. The displayed ranges are sensitivities under chosen numerical allowances, not additional certified bounds.')
    grow=[c for c in gaps if c['padding']==1]
    rows=[f"{c['even_gap']:g} & {c['odd_gap']:g} & {interval(c)} \\\\" for c in grow]
    sections['GAP']=wrap('$G_{\\rm even}$ & $G_{\\rm odd}$ & Ten-update numerical interval',rows,
        'All rows keep the nominal twice-quoted-error box and standard crossing padding.')
    prows=[c for c in gaps if c['even_gap']==8 and c['odd_gap']==7]
    rows=[f"{c['padding']:g} & {c['iterations']} & {interval(c)} \\\\" for c in prows]
    sections['PADDING']=wrap('Crossing-padding multiplier & Updates & Numerical interval',rows,
        'Matching the iteration count isolates padding changes. The original eight-update doubled-padding interval remains in the archival result table.')
    for key,data in [('box',boxrows),('gap',grow),('padding',prows)]:
        keys=['multiplier','even_gap','odd_gap','padding','iterations','status','lower','upper']
        with (out/f'review_{key}_sensitivity.csv').open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader()
            for c in data:
                row={k:c[k] for k in keys[:-2]};row.update(lower=c.get('interval',[None,None])[0],upper=c.get('interval',[None,None])[1]);writer.writerow(row)
        (out/f'review_{key}_sensitivity.tex').write_text(sections[key.upper()]+'\n')
    if args.update_note:
        p=ROOT/'note/ising3d_C1_note.tex';text=p.read_text()
        for key,value in sections.items():
            pattern=rf'(% BEGIN REVIEW {key} TABLE\n).*?(\n% END REVIEW {key} TABLE)'
            text,n=re.subn(pattern,lambda m:m[1]+value+m[2],text,flags=re.S)
            if n!=1:raise ValueError('Missing or duplicate table marker: '+key)
        p.write_text(text)
    print('Generated review tables from',len(boxrows),'box,',len(grow),'gap and',len(prows),'padding cases.')
if __name__=='__main__':main()
