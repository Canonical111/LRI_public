"""Complete endpoint-response source block using ordinary fixed-letter GPLs.
The production path instead keeps moving letters to the final functional.
This check uses the original Fraction endpoint implementation.
"""
import scaled_b as sb
from hyperlog_core import *
from pathlib import Path
from fractions import Fraction as F
import json,time,hashlib
root=sb.ROOT;name='EA7_b01';n=7;N=7;path=root/'endpoint_odd'/name/'stage5.jsonl';st=time.time()
items=sb.tb.br.rr.load(path);value=F(0);expanded=0
for j,row in enumerate(items):
 out=sb.tb.one_stage([row],N-1,N)
 for (words,logs),co in out.items():
  assert not logs and not any(words[:-1]);word=tuple(F(str(a)) for a in words[-1]);num,den=sb.rparts(co,N)
  value+=sb.tp.normalized_functional(num,den,word,1,n-1,0,0)
 expanded+=len(out);items[j]=None
 if j%40==0:
  print('FIXED_ENDPOINT',j,len(items),expanded,value,time.time()-st,flush=True)
  sb.tb.br.rr.clear();sb.mt.clear();sb.tp.clear_caches()
ref=json.loads((path.parent/'result.json').read_text());assert value==F(ref['finite_rational_constant'])
report={'status':'complete_new_endpoint_block_independently_checked','id':name,
 'source':str(path.relative_to(root)),'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
 'source_rows':len(items),'ordinary_expanded_rows':expanded,
 'ordinary_fixed_word_value':str(value),'production_moving_letter_value':ref['finite_rational_constant'],
 'exact_equal':True,'seconds':time.time()-st,'scope':'reintegrates the last two coordinates of one complete source block, not the entire EA7 integral'}
(root/'endpoint_fixed_word_check.json').write_text(json.dumps(report,indent=2));print('FULL_FIXED_ENDPOINT_PASS',report,flush=True)
