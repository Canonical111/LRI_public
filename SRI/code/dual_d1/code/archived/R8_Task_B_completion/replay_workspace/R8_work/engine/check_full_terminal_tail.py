"""Independent complete production tail via ordinary fixed-letter fibration.
Streaming one source row at a time bounds memory; default is a 16-row complete linear subproblem. Uses original Fraction scalars.
This does not read a candidate residue or a desired C8 coefficient.
"""
from pathlib import Path
from fractions import Fraction as F
import hashlib,json,time,itertools
import scaled_b as sb
from check_terminal_fibration import ordinary
root=sb.ROOT;work=root/'remaining_aggregate/remaining_spec_work';source=work/'combined_stage4.jsonl'
with source.open() as inp:
 for _ in range(80000):next(inp)
 lines=list(itertools.islice(inp,16))
assert len(lines)==16
value=F(0);negative=[F(0)]*6;expanded=0;st=time.time()
for i,line in enumerate(lines):
 ww,ll,cs=json.loads(line);assert ll==0
 row=((tuple(tuple(sb.tb.br.rr.rm.parseK(a) for a in w) for w in ww),()),sb.tb.br.rr.rm.parseK(cs))
 v,n,num=ordinary([row],8);value+=v;negative=[x+y for x,y in zip(negative,n)];expanded+=num
 if (i+1)%10==0:
  sb.tb.br.rr.clear();sb.mt.clear();sb.tp.clear_caches()
  print('ORDINARY_TAIL',i+1,len(lines),'value',value,'seconds',time.time()-st,flush=True)
report={'status':'independent_complete_terminal_slice_evaluated','method':'ordinary fixed-letter fibration and original Fraction cutoff functionals','source_start':80000,'source_rows':16,'source_sha256':hashlib.sha256(''.join(lines).encode()).hexdigest(),'value':str(value),'negative':list(map(str,negative)),'ordinary_intermediate_rows':expanded,'seconds':time.time()-st}
(root/'independent_terminal_tail_value.json').write_text(json.dumps(report,indent=2));print('INDEPENDENT_FULL_TAIL',json.dumps(report),flush=True)
