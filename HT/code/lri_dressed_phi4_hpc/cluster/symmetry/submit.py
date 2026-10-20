#!/usr/bin/env python3
"""Submit K node-packing jobs for one campaign on symmetry (amdq by default).

    python cluster/symmetry/submit.py --campaign DIR --receipt R --nodes K --time 15:30:00 [--dry-run]

Checks the manifest and receipt against this install, refuses while the campaign is in
maintenance, names jobs lri-<campaign id>, and prints job ids and log paths.
"""
import argparse,json,os,subprocess,sys
from pathlib import Path
CODE=Path(__file__).resolve().parents[2];sys.path.insert(0,str(CODE/'src'));sys.path.insert(0,str(CODE/'scripts'))
from pack_node import load_manifest,check_receipt

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--campaign',required=True);ap.add_argument('--receipt',required=True)
    ap.add_argument('--nodes',type=int,required=True);ap.add_argument('--time',required=True);ap.add_argument('--partition',default='amdq')
    ap.add_argument('--pack-args',default='');ap.add_argument('--dependency');ap.add_argument('--dry-run',action='store_true');a=ap.parse_args()
    if a.partition=='longq':ap.error('longq is avoided on symmetry; use amdq/defq')
    campaign=Path(a.campaign).resolve();m=load_manifest(campaign);check_receipt(a.receipt)
    if (campaign/'MAINTENANCE').exists():raise SystemExit('Campaign is in maintenance; refusing to submit')
    logs=Path(os.environ.get('LRI_ROOT','/mnt/beegfs/zzheng1/lri_dressed'))/'logs';logs.mkdir(parents=True,exist_ok=True)
    name=f"lri-{m['campaign']}"
    env=f"ALL,LRI_CODE_DIR={CODE},LRI_CAMPAIGN={campaign},LRI_RECEIPT={Path(a.receipt).resolve()},LRI_PACK_ARGS={a.pack_args}"
    cmd=['sbatch','--parsable','-p',a.partition,'-t',a.time,'-J',name,'-o',str(logs/'%x_%j.out'),'--export',env]
    if a.dependency:cmd+=['--dependency',a.dependency]
    cmd.append(str(CODE/'cluster/symmetry/pack.sbatch'))
    print(' '.join(cmd))
    if a.dry_run:return 0
    ids=[]
    for _ in range(a.nodes):
        p=subprocess.run(cmd,capture_output=True,text=True,check=True);ids.append(p.stdout.strip().split(';')[0])
    rec={'campaign':m['campaign'],'jobs':ids,'partition':a.partition,'time':a.time,'code':str(CODE),'receipt':a.receipt,
         'logs':[str(logs/f'{name}_{j}.out') for j in ids]}
    with open(campaign/'SUBMITTED.jsonl','a') as f:f.write(json.dumps(rec)+'\n')
    print(json.dumps(rec,indent=1));return 0

if __name__=='__main__':sys.exit(main())
