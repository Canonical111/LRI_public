"""Portable checks of the numerical C8 completion.
Default: saved exact-expression maps and input-based full Jacobian.
Optional raw source archives and fresh numerical evaluation are explicit.
"""
from pathlib import Path
from decimal import Decimal
import argparse,hashlib,json,subprocess,sys,os,zipfile,shutil
ROOT=Path(__file__).resolve().parent

def check_hashes():
 path=ROOT/'MANIFEST.json'
 if not path.exists():raise RuntimeError('Missing distribution manifest')
 for name,meta in json.loads(path.read_text()).items():
  p=ROOT/name;assert p.is_file(),p
  assert hashlib.sha256(p.read_bytes()).hexdigest()==meta['sha256'],p
 print('Distribution hashes: exact',flush=True)
def sources(where):
 archive=json.loads((ROOT/'archives/sources_manifest.json').read_text());work=ROOT/'replay_workspace';work.mkdir(exist_ok=True);seen=set()
 for record in archive['parts']:
  path=Path(where)/record['file'];assert hashlib.sha256(path.read_bytes()).hexdigest()==record['sha256'],path
  with zipfile.ZipFile(path) as z:
   assert z.testzip() is None
   meta=json.loads(z.read('PART_MANIFEST.json'))
   for name,info in meta.items():
    rel=Path(name);assert not rel.is_absolute() and '..' not in rel.parts and name not in seen;seen.add(name)
    data=z.read(name);assert hashlib.sha256(data).hexdigest()==info['sha256'];dest=work/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
 assert len(seen)==archive['total_original_source_files'];print('All raw source parts extracted and hashed:',len(seen),flush=True)
 if (ROOT/'replay_support').exists():shutil.copytree(ROOT/'replay_support',work,dirs_exist_ok=True)
 # Preserve original text; create relocated working copies in place only for code.
 for path in work.rglob('*.py'):
  txt=path.read_text();new=txt.replace('/mnt/data/',str(work)+'/')
  if txt!=new:path.write_text(new)
 return work

def numerics(small=False):
 names=['P8_positive_divergence_actual','P8_positive_divergence_predicted','P8_positive_divergence_difference'] if small else ['P8','Kv','J9','A9_log','Z8_log','EA7_finite','EZ6_finite','J9_lower_shift','B_old_full','F3_known','F1_known','U']
 folder=ROOT/'verification/replay';folder.mkdir(exist_ok=True);manifest=folder/'numeric_manifest.json';manifest.write_text(json.dumps({name:str(ROOT/'data'/(name+'.expr')) for name in names},indent=2))
 env=os.environ.copy();env.update(OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='1')
 args=[sys.executable,str(ROOT/'code/numerical/evaluate_set.py'),'--manifest',str(manifest),'--out',str(folder/'fresh_periods.json'),'--dps','90' if small else '100','--radius','140' if small else '160','--taylor','280' if small else '320','--asymptotic','175' if small else '200','--step','.25' if small else '.23']
 subprocess.run(args,check=True,env=env)
 fresh=json.loads((folder/'fresh_periods.json').read_text())['values']
 if small:assert abs(Decimal(fresh[names[-1]]))<Decimal('1e-65')
 else:
  reference={};reference.update(json.loads((ROOT/'data/F3_final_100.json').read_text())['values']);reference.update(json.loads((ROOT/'data/F4_data_100.json').read_text())['values'])
  for name in ('P8','Kv','J9'):assert abs(Decimal(fresh[name])-Decimal(reference[name]))<Decimal('1e-65')
 print('Fresh numerical comparison passed (not an interval certificate)',flush=True)

def main():
 p=argparse.ArgumentParser();p.add_argument('--sources',type=Path,help='Directory containing all optional raw source zip parts');p.add_argument('--numerical',action='store_true');p.add_argument('--numerical-small',action='store_true');p.add_argument('--skip-hashes',action='store_true');args=p.parse_args()
 if not args.skip_hashes:check_hashes()
 for name in ['check_exact_scalars.py','check_numerical_assembly.py']:subprocess.run([sys.executable,str(ROOT/'code'/name)],check=True)
 report=json.loads((ROOT/'verification/P8_divergence_acceptance.json').read_text());assert report['full_rational_divergent_polynomial_equal'] and all(r['exact_equal'] for r in report['six_displayed_checks'])
 sample=json.loads((ROOT/'verification/independent_final_period_check.json').read_text());assert Decimal(sample['maximum_absolute_difference'])<Decimal('1e-60')
 print('Saved divergence and independent period reports agree',flush=True)
 if args.sources:sources(args.sources)
 if args.numerical or args.numerical_small:numerics(args.numerical_small)
 print('Completed checks distinguish numerical input precision from exact assembly.',flush=True)
if __name__=='__main__':main()
