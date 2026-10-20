#!/usr/bin/env python3
"""Tabulate a calibration (or any) lane campaign: per step wall time, Newton steps, RSS, sizes;
per lane Slurm elapsed and charges (measured billing TRES and memory-aware estimate).

  python calib_report.py CAMPAIGN_DIR [--md report.md] [--json report.json]

Figures are measurements of these finite problems on these nodes, not physics results.
"""
import argparse,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import campaign,lanes  # noqa: E402


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('dir');p.add_argument('--md');p.add_argument('--json')
    a=p.parse_args();d=Path(a.dir).resolve();m=lanes.load_manifest(d/'manifest.json')
    steps=[]
    for i,ln in enumerate(m['lanes']):
        states=lanes.lane_states(ln)
        for k,s in enumerate(ln['steps']):
            row={'lane':i,'group':ln['group'],'x':ln['x'],'cpus':ln['resources']['cpus'],'mem_gib':ln['resources']['mem_gib'],
                 'step':s['name'],'threads':s['threads'],'state':states[k]}
            if row['state']=='done':
                r=json.loads(Path(s['output']).read_text())
                row.update(L=r['bath_cut'],dimension=r.get('dimension'),elapsed_s=r.get('elapsed_total_seconds'),
                           solve_s=r.get('seconds'),timings=r.get('timings'),newton=len(r.get('history',[])),
                           spectral_evaluations=r.get('spectral_evaluations'),matvecs=r.get('matvec_count'),
                           peak_rss_gib=r.get('peak_rss_kib',0)/1024**2,op_storage_gib=r.get('operator_storage_bytes_all',0)/1024**3,
                           mem_estimate_gib=r.get('memory_estimate_bytes',0)/1024**3,Delta_thermal=r.get('Delta_thermal'))
            steps.append(row)
    ch=campaign.charges(d)
    lines=['| group | x | step | threads | dim | elapsed s | Newton | matvecs | peak RSS GiB | est. GiB |','|---|---|---|---|---|---|---|---|---|---|']
    for r in steps:
        if r['state']!='done':lines.append(f"| {r['group']} | {r['x']:g} | {r['step']} | {r['threads']} | — | {r['state']} | | | | |");continue
        lines.append(f"| {r['group']} | {r['x']:g} | {r['step']} | {r['threads']} | {r['dimension']} | {r['elapsed_s']:.1f} | {r['newton']} | "
                     f"{r['matvecs']} | {r['peak_rss_gib']:.2f} | {r['mem_estimate_gib']:.2f} |")
    lines+=['','| array element | state | hours | cpus | mem GB | billing | SU measured | SU estimated |','|---|---|---|---|---|---|---|---|']
    for c in ch:
        if 'job' not in c:lines.append(f"| {c.get('array_job_id')} | {c.get('error')} | | | | | | |");continue
        lines.append(f"| {c['array_element']} | {c['state']} | {c['hours']:.3f} | {c['cpus']} | {(c['mem_mb'] or 0)/1024:.0f} | "
                     f"{c['billing'] if c['billing'] is not None else '—'} | {c['su_measured'] if c['su_measured'] is not None else float('nan'):.2f} | {c['su_estimated']:.2f} |")
    text='\n'.join(lines);print(text)
    if a.md:Path(a.md).write_text(text+'\n')
    if a.json:Path(a.json).write_text(json.dumps({'steps':steps,'charges':ch},indent=1))
    return 0

if __name__=='__main__':raise SystemExit(main())
