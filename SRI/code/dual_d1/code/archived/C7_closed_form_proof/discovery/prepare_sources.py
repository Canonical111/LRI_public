#!/usr/bin/env python3
"""Regenerate exact confluence endpoint rows, binary rows, and the initial target."""
from pathlib import Path
from collections import defaultdict
from fractions import Fraction
from itertools import product
import json
from analytic_sources import convergent,convergent_zeta_polynomial,NATURAL,multiplier,source
r=Path(__file__).resolve().parent
lines=[]
for n in range(2,7):
 for bits in convergent(n):
  bs=sum(b<<(n-i-1) for i,b in enumerate(bits));row=defaultdict(Fraction)
  for powers,c in convergent_zeta_polynomial(bits).items():
   ff=sum(((NATURAL[i],)*k for i,k in enumerate(powers)),())
   for w,a in multiplier(ff).items():row[w]+=c*a
  for w,c in sorted(row.items()):
   if c:lines.append(f'{n} {bs} {c} '+' '.join(map(str,w))+'\n')
(r/'D_endpoints.terms').write_text(''.join(lines))
with (r/'binary.rows').open('w') as f:
 for n in range(4,7):
  for w in product((0,1),repeat=n):
   if not all(w<w[j:] for j in range(1,n)):continue
   label=('I',n,0,0,*w);row=source(label)
   if not row:continue
   f.write('0 '+' '.join(map(str,label))+'\n'+str(len(row))+'\n')
   for v,c in sorted(row.items()):
    raw=0
    for a in v:raw=16*raw+a
    code=(n<<24)|raw;f.write(f'{code} {c}\n')
with (r/'after12.words').open('w') as f:
 for w,c in json.loads((r.parent/'proof/C7_linear_words.json').read_text()):
  if len(w)==6:f.write(f'{c} 6 '+' '.join(map(str,w))+'\n')
print('Exact source rows and initial weight-six target regenerated.')
