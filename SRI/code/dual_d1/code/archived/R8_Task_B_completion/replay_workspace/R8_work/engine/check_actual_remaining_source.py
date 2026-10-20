"""Real rebuilt weighted source rows: ordinary fixed-letter versus moving letters.
Uses original Fraction endpoint scalars, not the new GMP scalar acceleration.
"""
from pathlib import Path
import json,time,hashlib
import scaled_b as sb
from check_terminal_fibration import ordinary
source=sb.ROOT/'remaining_aggregate/remaining_spec_work/combined_stage4.jsonl'
selected={17,20845,41023,67012,80399};checks=[];st=time.time()
for i,line in enumerate(source.open()):
 if i not in selected:continue
 ww,ll,cs=json.loads(line);assert ll==0
 row=((tuple(tuple(sb.tb.br.rr.rm.parseK(x) for x in w) for w in ww),()),sb.tb.br.rr.rm.parseK(cs))
 a,_,an=sb.last_two_scaled([row],8)
 b,bn,nrows=ordinary([row],8)
 assert a==b and an==bn,(i,a,b,an,bn)
 d={'row':i,'source_line_sha256':hashlib.sha256(line.encode()).hexdigest(),'finite_value':str(a),'negative':list(map(str,an)),'ordinary_rows':nrows,'all_seven_equal':True};checks.append(d);print('EXACT_REAL_SOURCE_ROW',json.dumps(d),flush=True)
 sb.tb.br.rr.clear();sb.mt.clear();sb.tp.clear_caches()
assert {d['row'] for d in checks}==selected
result={'status':'actual_complete_rebuilt_source_endpoint_checks_pass','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'independent_representations':'moving-letter functional versus ordinary-word fibration; original Fraction scalars','checks':checks,'seconds':time.time()-st}
(sb.ROOT/'actual_rebuilt_source_endpoint_checks.json').write_text(json.dumps(result,indent=2));print('ACTUAL_SOURCE_ENDPOINT_ALL_PASS',time.time()-st,flush=True)
