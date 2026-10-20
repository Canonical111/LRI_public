#!/usr/bin/env python3
# Production helper used for the 2026 C7(2) run (Claude Code session C62d), unchanged apart from this header.
"""Committed vs expected checkpoint blocks for every job index of a C7(2) campaign (read-only).
usage: c7prod_status.py RUN [--missing]   exit 0 iff every block of every index is committed."""
import json,math,sqlite3,sys
from pathlib import Path
run=Path(sys.argv[1]);m=json.load(open(run/'manifest.json'));T=m['checkpoint_tasks'];missing=[];bygroup={}
counts={}
for g in m['groups']:
    p=run/'groups'/g['name'];db=sqlite3.connect(f'file:{p}/tasks.sqlite?mode=ro',uri=True)
    counts[g['name']]={s:n for s,n in db.execute('SELECT shard,COUNT(*) FROM tasks GROUP BY shard')};db.close()
done=tot=0
for j in m['jobs']:
    p=run/'groups'/j['group']/'checkpoints';need=math.ceil(counts[j['group']].get(j['shard'],0)/T)
    have=sum(1 for k in range(need) if (p/f's{j["shard"]:06d}_p{k:06d}.json').exists())
    b=bygroup.setdefault(j['group'],[0,0]);b[0]+=have;b[1]+=need;done+=have;tot+=need
    if have<need:missing.append(j['id'])
def ranges(ids):
    out=[];s=None
    for i in ids:
        if s is None:s=e=i
        elif i==e+1:e=i
        else:out.append(f'{s}-{e}'if e>s else str(s));s=e=i
    if s is not None:out.append(f'{s}-{e}'if e>s else str(s))
    return ','.join(out)
print(json.dumps({'blocks_committed':done,'blocks_total':tot,'groups':{k:f'{a}/{b}' for k,a,b in ((k,*v) for k,v in bygroup.items())},'incomplete_jobs':len(missing),'incomplete_ranges':ranges(missing)}))
sys.exit(0 if not missing else 1)
