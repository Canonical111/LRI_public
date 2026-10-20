from pathlib import Path
from fractions import Fraction as F
import sys,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'code'))
from annulus import run

def main():
    count=0
    for L in [16,32]:
      for N in range(9):
       for P in range(13):
        for nu in [0,1]:
            sigma=(nu-N)%2
            cutoff=F(L-N)-F(P+3,4)
            first=sigma+2*((cutoff-sigma)//2+1)
            d=2+nu-2*((P+3+4*nu+7)//8)
            assert first==L-N+d
            count+=1
    rows=[]
    for a in [.49,.5,.51]:rows.extend(run(alpha=a))
    for nu in [0,1]:
      for a in [.49,.5,.51]:
        rr=[r for r in rows if r['reflection']==nu and r['alpha']==a]
        assert all(rr[i+1]['error']<rr[i]['error'] for i in range(len(rr)-1))
        # Independent numerical test of the predicted next power, not a fitted amplitude.
        assert .95<rr[-1]['rescaled_next_error']/rr[-2]['rescaled_next_error']<1.05
        assert rr[-1]['phase_only_error']>100*rr[-1]['error']
    (ROOT/'results/general_bath_annulus.json').write_text(json.dumps(rows,indent=2)+'\n')
    (ROOT/'results/annulus_validation.json').write_text(json.dumps(dict(exact_threshold_checks=count,annulus_comparisons=len(rows),passed=True),indent=2)+'\n')
    print(count,'exact thresholds;',len(rows),'direct finite-annulus comparisons passed')
if __name__=='__main__':main()
