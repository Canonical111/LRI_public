from pathlib import Path
import json,mpmath as mp
from evaluate_periods_decimal import evaluate as dec
from evaluate_periods import evaluate as old
ROOT=Path(__file__).resolve().parent
words={(0,1),(2,1),(2,1,1),(2,1,1,1),(2,1,1,1,1),(2,1,1,1,1,1),(0,0,0,0,0,1),(2,4,1,3,6,1),(0,1,2,0,3,2),(7,5,3,2,1,4)}
a=dec(words,dps=75,R=120,ntaylor=250,nasym=130,stepfrac='.35')
b=old(words,dps=65,R=100,ntaylor=230,nasym=120,stepfrac='.37')
mp.mp.dps=80
err=max(abs(mp.mpf(str(a[w]))-b[w]) for w in words);assert err<mp.mpf('1e-56'),err
known={(0,1):mp.zeta(2),(2,1):-mp.zeta(2)/2,(2,1,1):-3*mp.zeta(3)/4,(2,1,1,1):-7*mp.zeta(4)/8,(2,1,1,1,1):-15*mp.zeta(5)/16,(2,1,1,1,1,1):-31*mp.zeta(6)/32,(0,0,0,0,0,1):31*mp.zeta(6)/16}
ek=max(abs(mp.mpf(str(a[w]))-v) for w,v in known.items());assert ek<mp.mpf('1e-65'),ek
out={'tested_words':len(words),'cross_backend_max_difference':str(err),'closed_period_max_difference':str(ek),'different_radii_steps_precisions':True}
(ROOT/'decimal_backend_checks.json').write_text(json.dumps(out,indent=2));print(out,flush=True)
