#!/usr/bin/env python3
"""Rerun exact and independent controls without replacing the recorded evidence."""
from pathlib import Path
import datetime,json,random,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'checks_output'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
out.mkdir(parents=True,exist_ok=False)
p=out/'power_mass';(p/'code').mkdir(parents=True);(p/'verification').mkdir();(p/'records').mkdir()
(p/'inputs').symlink_to(ROOT/'power_mass/inputs',target_is_directory=True)
(out/'LRI_C7_d2_progress').symlink_to(ROOT/'LRI_C7_d2_progress',target_is_directory=True)
checks=[]
for L in range(3,8):
 target=p/f'verification/edge_forests_L{L}.json'
 subprocess.run([str(ROOT/'power_mass/code/check_edge_forests'),str(ROOT/f'LRI_C7_d2_progress/reference/classes{L}.txt'),str(ROOT/f'power_mass/inputs/L{L}'),str(target)],check=True)
 d=json.load(open(target));assert d['failures']==0;checks.append(dict(name=f'edge_forests_L{L}',passed=True))
rr=random.Random(83461172);files=[]
for L in range(3,8):
 gs=[g for g in json.load(open(ROOT/f'power_mass/inputs/L{L}/inventory.json'))if'file'in g]
 files.extend(str(ROOT/'power_mass/inputs'/g['file'])for g in rr.sample(gs,min(18,len(gs))))
listing=p/'records/point_graphs.txt';listing.write_text('\n'.join(files)+'\n')
with (p/'verification/fallback_checks.json').open('w')as f:
 subprocess.run([str(ROOT/'power_mass/code/check_fallback'),str(listing)],stdout=f,check=True)
checks.append(dict(name='fallback_checks',passed=True))
for name in ('validate_kirchhoff.py','check_three_loop_radial.py','check_assembly.py'):
 shutil.copy2(ROOT/'power_mass/code'/name,p/'code'/name)
 with (p/'records'/f'{name}.log').open('w')as f:subprocess.run([sys.executable,str(p/'code'/name)],stdout=f,stderr=f,check=True)
 checks.append(dict(name=name,passed=True))
report=dict(status='passed',checks=checks,recorded_evidence_overwritten=False)
(out/'summary.json').write_text(json.dumps(report,indent=2));print(out/'summary.json')
