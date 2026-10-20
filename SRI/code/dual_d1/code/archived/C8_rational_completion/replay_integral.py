#!/usr/bin/env python3
"""Reintegrate one complete boundary block in an isolated scratch directory.
Install requirements and build native extensions in workspace/R8_work first.
"""
from pathlib import Path
import argparse,subprocess,sys,shutil,json,time,os
ROOT=Path(__file__).resolve().parent

def main():
 p=argparse.ArgumentParser();p.add_argument('--kind',choices=['A','Z'],required=True);p.add_argument('--deriv',choices=['base','d','v'],required=True);p.add_argument('--block',required=True);p.add_argument('--jets',action='store_true');p.add_argument('--from-stage',type=int,default=1);args=p.parse_args()
 arch=ROOT/'workspace/R8_work';src=arch/'tail_blocks'/f'{args.kind}_{args.deriv}'/args.block
 if not (src/'source.json').exists():raise SystemExit('Unknown archived boundary source block.')
 if args.jets and not (src/'full_boundary_jets.json').exists():raise SystemExit('This block has no archived full-jet comparison; omit --jets or choose a primary block.')
 if args.from_stage<1 or not (src/f'stage{args.from_stage}.jsonl').exists():raise SystemExit('Requested archived intermediate stage is absent.')
 replay=ROOT/'verification/raw_replay'/f'{args.kind}_{args.deriv}_{args.block}'
 if replay.exists():raise SystemExit(f'Replay folder already exists: {replay}. Rename it to request a fresh replay.')
 out=replay/'tail_blocks'/f'{args.kind}_{args.deriv}'/args.block;out.mkdir(parents=True)
 shutil.copytree(arch/'engine',replay/'engine',ignore=shutil.ignore_patterns('__pycache__'))
 for name in ['source.json','stage1.jsonl']:shutil.copy2(src/name,out/name)
 if args.from_stage>1:shutil.copy2(src/f'stage{args.from_stage}.jsonl',out/f'stage{args.from_stage}.jsonl')
 eng=replay/'engine';env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
 with (replay/'raw_replay.log').open('w') as log:
  subprocess.run([sys.executable,str(eng/'tail_boundary.py'),'--kind',args.kind,'--deriv',args.deriv,'--block',args.block],cwd=eng,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 got=json.loads((out/'result.json').read_text());want=json.loads((src/'result.json').read_text())
 for key in ['value','dimensionless_negative_inverse_euler','source_sha256']:assert got[key]==want[key],key
 if args.jets:
  with (replay/'jet_replay.log').open('w') as log:subprocess.run([sys.executable,str(eng/'tail_jets.py'),args.kind,args.deriv,args.block],cwd=eng,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  g=json.loads((out/'full_boundary_jets.json').read_text());w=json.loads((src/'full_boundary_jets.json').read_text());assert g['boundary_polynomials']==w['boundary_polynomials']
 report={'status':'complete_block_fresh_replay_agrees','block':args.block,'kind':args.kind,'derivative':args.deriv,'boundary_constant':got['value'],'complete_logarithmic_jet_replayed':args.jets,'started_from_archived_stage':args.from_stage}
 (replay/'comparison.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
