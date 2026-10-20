import sympy as s,json,time,sys
from pathlib import Path
import ct_engine as ce,analytic_core as ac,series_engine as se
ROOT=Path(__file__).parent
L=int(sys.argv[1]);lo=int(sys.argv[2]);hi=int(sys.argv[3]);rows=[];t=time.time()
for i in range(lo,min(hi,len(ac.CC[str(L)]))):
 c=ac.CC[str(L)][i];w4=s.Rational(*c['w4']);w2=s.Rational(*c['w2']);au=c['aut']
 if L==4 and i==26:continue
 if L==5 and(i in[51,78,99,113,124,128,123,125,126] or 3*w2==w4):continue
 r=ce.residue(L,i)
 rows.append(dict(i=i,word=c['word'],r=str(r),wb=str(L*(-1)**L*w4/au),wc=str(L*(-1)**L*w2/au)))
 print('RES',L,i,r,'time',round(time.time()-t,2),flush=True)
 (ROOT/f'rows_{L}_{lo}_{hi}.json').write_text(json.dumps(rows,indent=2))
