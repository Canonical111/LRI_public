#!/usr/bin/env python3
# Production helper used for the 2026 C7(2) run (Claude Code session C62d), unchanged apart from this header.
# Usage: queue.py RUN [efficiency]. Writes RUN/lanes/queue.txt for node.slurm.
"""Write RUN/lanes/queue.txt: incomplete job indices with estimated wall seconds at 64 threads, heaviest first."""
import json,math,sqlite3,sys
from pathlib import Path
run=Path(sys.argv[1]);eff=float(sys.argv[2]) if len(sys.argv)>2 else 0.85;m=json.load(open(run/'manifest.json'));T=m['checkpoint_tasks']
info={}
for g in m['groups']:
    db=sqlite3.connect(f"file:{run}/groups/{g['name']}/tasks.sqlite?mode=ro",uri=True)
    info[g['name']]={s:(n,c) for s,n,c in db.execute('SELECT shard,COUNT(*),SUM(cost) FROM tasks GROUP BY shard')};db.close()
todo=[]
for j in m['jobs']:
    n,c=info[j['group']][j['shard']];need=math.ceil(n/T);p=run/'groups'/j['group']/'checkpoints'
    have=sum(1 for k in range(need) if (p/f"s{j['shard']:06d}_p{k:06d}.json").exists())
    if have<need:todo.append((c/64/eff+30,j['id']))
todo.sort(key=lambda x:(-x[0],x[1]));(run/'lanes'/'logs').mkdir(parents=True,exist_ok=True)
with open(run/'lanes'/'queue.txt','w')as f:
    for est,i in todo:f.write(f'{i} {int(math.ceil(est))}\n')
tot=sum(e for e,_ in todo)
print(json.dumps({'incomplete':len(todo),'lane_hours_total':round(tot/3600,1),'heaviest_s':int(todo[0][0]) if todo else 0,'hours_per_lane_if_44_lanes':round(tot/3600/44,2)}))
