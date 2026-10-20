"""Verify the delivered exact finite-part expressions and their recorded checks.
Default requires only Python's standard library and does not reintegrate kernels.
"""
from pathlib import Path
from fractions import Fraction as Q
from decimal import Decimal,localcontext
import argparse,json,hashlib,subprocess,sys,os,time
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'engine'))
from period_polynomial import parse,add

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def rebased(p):
 p=Path(p)
 if p.is_absolute():
  try:return ROOT/p.relative_to('/mnt/data/F3_continuation/full_exact')
  except ValueError:raise ValueError(('unrecognized input path',str(p)))
 return ROOT/p

def main():
 pa=argparse.ArgumentParser();pa.add_argument('--numerical',action='store_true');pa.add_argument('--analytic',action='store_true');pa.add_argument('--skip-hashes',action='store_true');a=pa.parse_args();st=time.time();checks={}
 outdir=ROOT/'verification/replay';outdir.mkdir(parents=True,exist_ok=True)
 os.environ['F3_REPORT_DIRECTORY']=str(outdir)
 if not a.skip_hashes:
  m=json.loads((ROOT/'MANIFEST.json').read_text())
  for name,r in m['files'].items():
   p=ROOT/name;assert p.stat().st_size==r['bytes'] and sha(p)==r['sha256'],name
  checks['distributed_files_hashed']=len(m['files'])
 # Exact full coefficient-polynomial sum of six complete Xvv blocks.
 manifest=json.loads((ROOT/'Q6_vv/manifest.json').read_text());assert len(manifest['blocks'])==6
 summed={}
 for r in manifest['blocks']:
  p=ROOT/'Q6_vv'/r['block'];assert sha(p/'stage1.jsonl')==r.get('source_sha256',r.get('sha256'));assert json.loads((p/'result.json').read_text())['complete'];add(summed,parse((p/'coefficient_0.expr').read_text()))
 target=parse((ROOT/'data/Xvv.expr').read_text());diff=summed.copy();add(diff,target,-1);assert not diff and target.get(())==Q(-167099)
 checks['Xvv_six_block_full_expression_sum_exact']=True
 # Byte-exact disjoint-range source coverage of the endpoint finite calculation.
 subprocess.run([sys.executable,str(ROOT/'engine/check_XE_source_coverage.py'),str(outdir/'XE_source_coverage.json')],check=True)
 checks['XE_full_source_range_coverage']=json.loads((outdir/'XE_source_coverage.json').read_text())
 # Source links before the terminal partition, including all six original blocks.
 mm=json.loads((ROOT/'SEQ6_v/manifest.json').read_text());assert len(mm['blocks'])==6
 for r in mm['blocks']:assert sha(ROOT/'SEQ6_v'/r['block']/'stage1.jsonl')==r.get('source_sha256',r.get('sha256'))
 sm=json.loads((ROOT/'SEQ6_combined/b00/stage3.assembly.json').read_text());assert len(sm['inputs'])==6
 for r in sm['inputs']:assert sha(ROOT/r['path'])==r['sha256']
 assert sha(ROOT/'SEQ6_combined/b00/stage3.jsonl')==sm['output_sha256']
 xe_report=json.loads((ROOT/'data/XE_assembly.json').read_text());assert sha(ROOT/'data/XE.expr')==xe_report['output_sha256'];assert sha(ROOT/'XE_growth_total/stage5.jsonl')==xe_report['input_sha256']
 xe=parse((ROOT/'data/XE.expr').read_text());assert xe.get(())==Q(3729,2)
 checks['XE_source_links_and_rational_projection_exact']=True
 # Full known F3 correction, without assigning P8.
 ss=parse((ROOT/'inherited/F3_lower_shift.expr').read_text());known={};add(known,target,16);add(known,xe,-8);add(known,ss)
 diff=known.copy();add(diff,parse((ROOT/'data/F3_known_with_six_kinks.expr').read_text()),-1);assert not diff and known.get(())==Q(-9017996,3)
 checks['F3_known_part_full_expression_sum_exact']=True
 # Numeric precision comparison, explicitly not an interval enclosure.
 first=json.loads((ROOT/'data/XE_first60.json').read_text());second=json.loads((ROOT/'data/XE_second90.json').read_text())
 differences={}
 with localcontext() as ctx:
  ctx.prec=100
  for name in ('Xvv','XE','F3_lower_shift'):
   path=ROOT/('inherited/F3_lower_shift.expr' if name=='F3_lower_shift' else 'data/'+name+'.expr')
   assert sha(path)==first['input_sha256'][name]==second['input_sha256'][name]
   differences[name]=str(abs(Decimal(first['values'][name])-Decimal(second['values'][name])))
   assert Decimal(differences[name])<Decimal('1e-40')
 checks['fresh_run_comparison_differences']=differences
 if a.analytic:
  for script in ['test_growth_elementary.py','check_growth_linear_general.py','check_scaled_unscaled.py']:
   p=ROOT/'engine'/script
   if not p.exists():raise FileNotFoundError(p)
   with (outdir/(p.stem+'.log')).open('w') as f:subprocess.run([sys.executable,str(p)],cwd=ROOT/'engine',stdout=f,stderr=subprocess.STDOUT,check=True)
  checks['fresh_analytic_regressions']=True
 if a.numerical:
  env=os.environ.copy();env['OMP_NUM_THREADS']='1';env['OPENBLAS_NUM_THREADS']='1'
  for label,dps,rad,nt,na,step in [('fresh60',60,90,210,130,'.3'),('fresh90',90,130,280,175,'.25')]:
   path=outdir/(label+'.json')
   cmd=[sys.executable,str(ROOT/'numerical/evaluate_set.py'),'--manifest',str(ROOT/'data/XE_evaluation_manifest.json'),'--out',str(path),'--dps',str(dps),'--radius',str(rad),'--taylor',str(nt),'--asymptotic',str(na),'--step',step,'--backend','gmp']
   with (outdir/(label+'.log')).open('w') as f:subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
   vals=json.loads(path.read_text())['values']
   with localcontext() as ctx:
    ctx.prec=100
    for name,v in vals.items():assert abs(Decimal(v)-Decimal(second['values'][name]))<Decimal('1e-40')
  subprocess.run([sys.executable,str(ROOT/'numerical/check_new_period_subset.py')],env=env,check=True)
  checks['complete_fresh_period_evaluations_and_Decimal_subset']=True
 checks.update({'all_requested_checks_passed':True,'seconds':time.time()-st,'not_a_fresh_reintegration_of_all_kernels':True,'not_an_interval_certificate':True,'P8_full_value_not_evaluated':True,'F3_complete':False,'C8_complete':False})
 (outdir/'summary.json').write_text(json.dumps(checks,indent=2));print(json.dumps(checks,indent=2))
if __name__=='__main__':main()
