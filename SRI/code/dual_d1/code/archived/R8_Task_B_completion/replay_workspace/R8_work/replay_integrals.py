"""Re-evaluate a complete Task B block in a separate, auditable workspace.

--from-stage 1 restarts after the analytically specified first integration.
--from-stage 4 redoes the last two integrations from the exact saved checkpoint.
No source archive is overwritten. A reused completed replay is labelled as such.
"""
from pathlib import Path
from fractions import Fraction
import argparse,hashlib,json,os,shutil,subprocess,sys,time
ROOT=Path(__file__).resolve().parent

def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for x in iter(lambda:f.read(1<<20),b''):h.update(x)
 return h.hexdigest()

def one(name,stage,native,force):
 if not name.startswith('n8_f') or not name.replace('_','').isalnum():
  raise ValueError('Use a block identifier from the source manifests.')
 original=ROOT/'scaled_blocks'/name
 if not (original/'result.json').exists():raise RuntimeError('No complete reference block.')
 work=ROOT/'replay_integrals'/name
 if force and work.exists():shutil.rmtree(work)
 work.mkdir(parents=True,exist_ok=True)
 engine=work/'engine'
 if not engine.exists():shutil.copytree(ROOT/'engine',engine,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
 destination=work/'scaled_blocks'/name;destination.mkdir(parents=True,exist_ok=True)
 for f in ['source.json','stage1.jsonl']+([] if stage==1 else [f'stage{stage}.jsonl']):
  target=destination/f
  if target.exists():assert sha(target)==sha(original/f),('changed replay seed',f)
  else:shutil.copy2(original/f,target)
 marker=destination/'result.json';reused=marker.exists();start=time.time()
 env={**os.environ,'OPENBLAS_NUM_THREADS':'1','R6_NATIVE':str(int(native)),
      'R6_LINEAR':str(int(native)),'R6_MOD':str(int(native)),'R6_ACCEL':'1'}
 if not reused:
  with (work/'execution.log').open('w') as stream:
   subprocess.run([sys.executable,'-u','scaled_worker.py',name],cwd=engine,
      env=env,stdout=stream,stderr=subprocess.STDOUT,check=True)
 new=json.loads(marker.read_text());old=json.loads((original/'result.json').read_text())
 assert new['status']=='complete_block_not_full_integral'
 assert new['source_sha256']==old['source_sha256']==sha(original/'stage1.jsonl')
 assert Fraction(new['value'])==Fraction(old['value'])
 assert list(map(Fraction,new['dimensionless_negative_inverse_euler']))==list(map(Fraction,old['dimensionless_negative_inverse_euler']))
 report={'status':'exact_replay_agreement','block':name,'from_stage':stage,
  'complete_saved_replay_reused':reused,'native_exact_helpers':native,
  'source_sha256':new['source_sha256'],'value':new['value'],
  'all_six_negative_moments_equal':True,'seconds':time.time()-start,
  'scope':'fresh integrations after specified checkpoint unless reuse explicitly recorded'}
 (work/'verification.json').write_text(json.dumps(report,indent=2))
 print(json.dumps(report,indent=2),flush=True)
 return report

def main():
 p=argparse.ArgumentParser(description=__doc__)
 g=p.add_mutually_exclusive_group(required=True);g.add_argument('--block');g.add_argument('--all',action='store_true')
 p.add_argument('--from-stage',type=int,choices=(1,4),default=1)
 p.add_argument('--native',action='store_true');p.add_argument('--force',action='store_true')
 a=p.parse_args()
 if a.all:
  names=[]
  for face in (1,2,3,4):names += [r['id'] for r in json.loads((ROOT/'scaled_blocks'/f'n8_face{face}_manifest.json').read_text())['blocks']]
 else:names=[a.block]
 reports=[one(n,a.from_stage,a.native,a.force) for n in names]
 (ROOT/'replay_integrals'/'summary.json').write_text(json.dumps(reports,indent=2))
if __name__=='__main__':main()
