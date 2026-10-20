"""Reintegrate a complete A9 boundary block in ordinary fixed-letter words.
Uses the original Fraction endpoint functional, not the production moving-letter
or extended vacuum functional. Earlier exact ordered stages are shared inputs.
"""
import scaled_b as sb
from hyperlog_core import *
from pathlib import Path
from fractions import Fraction as F
import json,time,hashlib,sys
root=sb.ROOT;name=sys.argv[1] if len(sys.argv)>1 else 'n9_f1_b01';n=9;N=7
path=root/'tail_blocks/A_base'/name/'stage5.jsonl';st=time.time()
items=sb.tb.br.rr.load(path);value=F(0);expanded=0
for j,row in enumerate(items):
 out=sb.tb.one_stage([row],N-1,N)
 for (words,logs),co in out.items():
  assert not logs and not any(words[:-1]);word=tuple(F(str(a)) for a in words[-1]);num,den=sb.rparts(co,N)
  value+=sb.tp.normalized_functional(num,den,word,0,n-1,0,0)
  value-=(n-1)*sb.tp.normalized_functional(num,den,word,1,n-1,0,0)
  value-=sb.tp.normalized_functional((F(0),)+num,den,word,1,n-1,0,0)
 expanded+=len(out);items[j]=None
 if j%40==0:
  print('FIXED_A9',name,j,len(items),expanded,value,time.time()-st,flush=True)
  sb.tb.br.rr.clear();sb.mt.clear();sb.tp.clear_caches()
ref=json.loads((path.parent/'result.json').read_text());assert value==F(ref['value'])
report={'status':'complete_A9_boundary_block_independently_checked','id':name,
 'source':str(path.relative_to(root)),'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
 'source_rows':len(items),'ordinary_expanded_rows':expanded,
 'ordinary_fixed_word_value':str(value),'production_moving_letter_value':ref['value'],
 'exact_equal':True,'seconds':time.time()-st,'scope':'reintegrates the last two coordinates of one complete A9 source block with a different endpoint representation; earlier ordered stages shared'}
(root/f'fixed_A9_{name}.json').write_text(json.dumps(report,indent=2));print('FULL_FIXED_A9_PASS',report,flush=True)
