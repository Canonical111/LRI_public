#!/usr/bin/env python3
"""Slurm arrays of multi-core ensemble jobs; deterministic multi-cluster sharding."""
import argparse,heapq,json,math,os,shlex,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('campaign',type=Path)
 p.add_argument('--workers-per-job',type=int,default=16);p.add_argument('--tasks-per-job',type=int,default=64)
 p.add_argument('--concurrency',type=int,default=8);p.add_argument('--shards',type=int,default=1);p.add_argument('--shard',type=int,default=0)
 p.add_argument('--time',default='08:00:00');p.add_argument('--mem',default='16G');p.add_argument('--account');p.add_argument('--partition')
 p.add_argument('--constraint');p.add_argument('--measurements',type=int);p.add_argument('--auto-requeue',action='store_true');p.add_argument('--dry-run',action='store_true')
 a=p.parse_args();root=a.campaign.resolve()
 if a.measurements is not None and a.measurements<=0:p.error('measurement target must be positive')
 if min(a.workers_per_job,a.tasks_per_job,a.concurrency,a.shards)<1 or not 0<=a.shard<a.shards:p.error('invalid positive counts or shard')
 mf=json.loads((root/'manifest.json').read_text());tasks=[t for t in mf['tasks'] if t['id']%a.shards==a.shard]
 if not tasks:p.error('empty shard')
 nslots=math.ceil(len(tasks)/a.tasks_per_job);slots=[[] for _ in range(nslots)];heap=[(0,i) for i in range(nslots)]
 for t in sorted(tasks,key=lambda t:t['N']*(t['warmup']+(a.measurements or t['measurements'])),reverse=True):
  weight,i=heapq.heappop(heap);slots[i].append(t['id']);heapq.heappush(heap,(weight+t['N']*(t['warmup']+(a.measurements or t['measurements'])),i))
 plan={'campaign_id':mf['campaign_id'],'shards':a.shards,'shard':a.shard,'slots':slots}
 log=root/'logs';log.mkdir(exist_ok=True);planpath=log/f'launch_shard{a.shard}of{a.shards}_workers{a.workers_per_job}_tasks{a.tasks_per_job}_target{a.measurements or 0}.json'
 if planpath.exists() and json.loads(planpath.read_text())!=plan:p.error('launch plan changed; use a different plan name or campaign')
 planpath.write_text(json.dumps(plan,indent=2)+'\n')
 env=os.environ.copy();env.update(LRI_ROOT=str(ROOT),LRI_CAMPAIGN=str(root),LRI_PLAN=str(planpath),LRI_WORKERS=str(a.workers_per_job),LRI_AUTOREQUEUE=str(int(a.auto_requeue)))
 env['LRI_MEASUREMENTS']=str(a.measurements or '')
 cmd=['sbatch','--export=ALL',f'--array=0-{nslots-1}%{a.concurrency}',f'--cpus-per-task={a.workers_per_job}',f'--time={a.time}',f'--mem={a.mem}',
      f'--output={log}/%A_%a.out',f'--error={log}/%A_%a.err']
 for k in ('account','partition','constraint'):
  if getattr(a,k):cmd.append(f'--{k}={getattr(a,k)}')
 cmd.append(str(ROOT/'array.slurm'))
 print(f'{len(tasks)} chains in shard {a.shard}/{a.shards}; {nslots} jobs; at most {min(a.concurrency,nslots)*a.workers_per_job} cores')
 print(shlex.join(cmd))
 if not a.dry_run:subprocess.run(cmd,env=env,check=True)
if __name__=='__main__':main()
