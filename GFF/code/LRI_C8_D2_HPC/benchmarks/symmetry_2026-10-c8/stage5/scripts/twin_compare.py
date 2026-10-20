#!/usr/bin/env python3
"""A-ORC-8(a) record: the restart twin against the uninterrupted smoke (same plan arguments and seed):
  twin_compare.py SMOKE TWIN OUT.json
all 24 groups' merged.json "batches" bitwise equal (as canonical JSON), plus graph_replicates.csv and graph_tails.csv
byte-identical (graph_costs.csv holds timings and is expected to differ), the twin's checkpoints by attempt job id."""
import glob,hashlib,json,sys
from pathlib import Path
a,b,out=Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3]);res={};h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for g in sorted(p.name for p in (a/'groups').iterdir()):
    x=json.loads((a/'groups'/g/'merged.json').read_text());y=json.loads((b/'groups'/g/'merged.json').read_text())
    res[g]={'batches_equal':json.dumps(x['batches'],sort_keys=True)==json.dumps(y['batches'],sort_keys=True),
            'graph_replicates_equal':h(a/'groups'/g/'graph_replicates.csv')==h(b/'groups'/g/'graph_replicates.csv'),
            'graph_tails_equal':h(a/'groups'/g/'graph_tails.csv')==h(b/'groups'/g/'graph_tails.csv')}
jobs={}
for f in glob.glob(str(b/'groups/*/checkpoints/*.json')):
    s=(json.loads(Path(f).read_text())['runtime']['fingerprint'].get('slurm')or{}).get('SLURM_JOB_ID');jobs[s]=jobs.get(s,0)+1
doc={'smoke':str(a),'twin':str(b),'groups':len(res),'all_batches_equal':len(res)==24 and all(v['batches_equal']for v in res.values()),
     'all_replicate_and_tail_tables_equal':all(v['graph_replicates_equal']and v['graph_tails_equal']for v in res.values()),
     'twin_checkpoints_by_job':jobs,'per_group':res}
out.write_text(json.dumps(doc,indent=1)+'\n');print(json.dumps({k:v for k,v in doc.items()if k!='per_group'}))
