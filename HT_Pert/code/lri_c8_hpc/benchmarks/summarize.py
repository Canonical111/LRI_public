#!/usr/bin/env python3
from pathlib import Path
import argparse,json,statistics
ROOT=Path(__file__).resolve().parents[1]
# benchmarks/SUMMARY.json is manifest-listed; write elsewhere unless asked explicitly.
ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=ROOT/'validation/summary.json')
ap.add_argument('--input-dir',type=Path,default=ROOT/'validation/benchmarks',
                help='fresh run_suite.py results; benchmarks/results holds the bundled historical records');args=ap.parse_args()
groups={}
paths=sorted(args.input_dir.glob('*.json'))
if not paths:raise SystemExit(f'No benchmark records in {args.input_dir}')
for path in paths:
 r=json.loads(path.read_text());c=r['config']
 if c.get('profile'):raise ValueError('Profile runs must not enter clean timing summary')
 key=(c['cutoff'],c['scheme'],c['solver'],c['backend'],c['threads']);groups.setdefault(key,[]).append(r)
rows=[]
for (L,s,impl,b,t),rs in sorted(groups.items()):
 rows.append({'cutoff':L,'scheme':s,'implementation':impl,'backend':b,'threads':t,'repetitions':len(rs),
              'median_seconds':statistics.median(r['seconds'] for r in rs),
              'all_seconds':[r['seconds'] for r in rs],
              'peak_rss_mib':max(r['peak_rss_mib'] for r in rs),
              'max_reference_difference':max(max(r['reference_max_abs'].values()) for r in rs if r['reference_max_abs'])})
summary={'scope':'Independent processes; warmed compilation; entire numerical solve; four-CPU local quota; not Expanse measurements.',
         'profiled_runs_excluded':True,'rows':rows}
args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
