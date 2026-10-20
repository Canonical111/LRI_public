from pathlib import Path
import sys,json,hashlib,time
from fractions import Fraction as F
sys.path.insert(0,'/mnt/data/P8_final_run');import period_algebra as pa
base=Path('/mnt/data/P8_final_run/old_C7/C7_completion/engine');R=Path('/mnt/data/P8_final_run/F3_six_kink_completion');dest=R/'C8_assembly';dest.mkdir(exist_ok=True)
trace=json.loads(Path('/mnt/data/C8_full_work/full_trace.json').read_text());formal=pa.parse_expr(trace['old_part'])
mapping={'a':'a_check','p':'p_check','A':'A_check','E':'E_check','c':'c_check','f':'f_check','q':'q_check','b':'b_check','G':'G_check','k':'k_check','Q':'Qnew','P':'Pnew','K':'Knew'}
inputs={};polys={};out={};st=time.time()
for mon,c in formal.items():
 val={():c}
 for atom,power in mon:
  if atom not in polys:
   fp=base/(mapping.get(atom,atom)+'_symbolic.expr');polys[atom]=pa.parse_expr(fp.read_text());inputs[atom]={'file':str(fp),'sha256':hashlib.sha256(fp.read_bytes()).hexdigest()}
  val=pa.mul(val,pa.powp(polys[atom],power))
 pa.add(out,val)
 print('BOLD_ASSEMBLE',mon,len(out),time.time()-st,flush=True)
assert out.get(())==F(1153,6),out.get(())
fp=dest/'B_old_full.expr';fp.write_text(pa.dump(out));(dest/'B_old_assembly.json').write_text(json.dumps({'source_formula':trace['old_part'],'input_count':len(inputs),'inputs':inputs,'full_expression_terms':len(out),'rational_projection':str(out.get(())),'sha256':hashlib.sha256(fp.read_bytes()).hexdigest(),'seconds':time.time()-st},indent=2))
print('BOLD_FULL_DONE',len(out),flush=True)
