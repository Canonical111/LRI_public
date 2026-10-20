"""Exact independent scalar assembly. Missing inputs are never zero."""
from pathlib import Path
from fractions import Fraction as Q
import json,sys,hashlib

from period_polynomial import parse,add
ROOT=Path(__file__).resolve().parent.parent

def write_poly(poly):
 out=[]
 for mon,c in sorted(poly.items()):
  atoms='*'.join(a if n==1 else f'({a})**{n}' for a,n in mon)
  term=str(abs(c))+('*'+atoms if atoms else '')
  out.append((' - ' if c<0 else ' + ') +term)
 return ''.join(out).lstrip(' +') or '0'

def assemble(name):
 if name=='Xvv':
  manifest=json.loads((ROOT/'Q6_vv/manifest.json').read_text())
  assert len(manifest['blocks'])==6
  inputs=[]
  for rec in manifest['blocks']:
   folder=ROOT/'Q6_vv'/rec['block']; assert (folder/'result.json').is_file(),folder
   assert hashlib.sha256((folder/'stage1.jsonl').read_bytes()).hexdigest()==rec.get('source_sha256',rec.get('sha256'))
   inputs.append(folder/'coefficient_0.expr')
  expected=Q(-167099)
 elif name=='XE':
  f=ROOT/'SEQ6_combined/b00';assert (f/'result.json').is_file()
  inputs=[f/'finite.expr'];expected=Q(3729,2)
 else:raise ValueError(name)
 out={};reports=[]
 for f in inputs:
  p=parse(f.read_text());add(out,p);reports.append({'path':str(f),'terms':len(p),'rational':str(p.get((),0)),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
  print('INPUT',name,f,len(p),flush=True)
 assert out.get((),Q(0))==expected,(name,out.get(()),expected)
 target=ROOT/'data'/f'{name}.expr';target.write_text(write_poly(out))
 report={'name':name,'complete_period_expression':True,'new_terms':len(out),'rational_projection':str(out.get((),0)),'rational_value_used_only_after_integrations':True,'inputs':reports,'output_sha256':hashlib.sha256(target.read_bytes()).hexdigest()}
 (ROOT/'data'/f'{name}_assembly.json').write_text(json.dumps(report,indent=2));print('ASSEMBLED',name,len(out),expected,flush=True)
if __name__=='__main__':assemble(sys.argv[1])
