
import sys,json,time
import sympy as s
from pathlib import Path
from asymptotic_gpl import extract_rows,ell
ROOT=Path(__file__).resolve().parent
for tag in sys.argv[1:]:
 st=time.time()
 rows=json.loads((ROOT/(tag+'_negative.json')).read_text())
 ans=extract_rows(rows,3,0,None)
 (ROOT/'series'/(tag+'_p0.expr')).write_text(s.sstr(ans,order="none"))
 fi=s.expand(ans).coeff(ell,0)
 mapping={x:s.S.Zero for x in fi.free_symbols if str(x).startswith(('R_','Z'))}
 mapping.update({x:s.S.Zero for x in fi.atoms(s.log,s.polylog,s.zeta)})
 print('EXTRACTED',tag,'p0terms',len(s.Add.make_args(ans)),'finite',len(s.Add.make_args(fi)),
       'pi0',s.expand(fi.xreplace(mapping).subs(s.pi,0)),'seconds',time.time()-st,flush=True)
