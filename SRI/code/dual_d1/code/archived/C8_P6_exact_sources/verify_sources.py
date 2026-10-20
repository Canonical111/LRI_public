"""Saved source coverage and hashes. Does not reintegrate a kernel."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parent;P=ROOT/'P6_full'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files=set();counts=[]
for face in range(1,4):
 folder=P/f'B6_vd_f{face}';m=json.loads((folder/'manifest.json').read_text());counts.append(len(m['blocks']))
 for b in m['blocks']:
  f=folder/b['block']/'stage1.jsonl';assert sha(f)==b['source_sha256'];files.add(str((folder/b['block']/'stage2.jsonl').relative_to(P)))
assert counts==[6,9,6]
part=json.loads((P/'weighted_s2/partition.json').read_text());assert {r['path'] for r in part['inputs']}==files
for r in part['inputs']:
 f=P/r['path'];assert sha(f)==r['sha256'];assert sum(1 for _ in f.open())==r['rows'];assert r['weight']==(1 if 'B6_vd_f3/' in r['path'] else 2)
rep=json.loads((P/'terminal/report.json').read_text());assert sha(P/'moving_total.jsonl')==rep['source_sha256'];assert sum(1 for _ in (P/'moving_total.jsonl').open())==rep['input_rows']
last=json.loads((P/'P6_exact_report.json').read_text())
for r in last['input_buckets']:assert sha(P/r['path'])==r['sha256']
assert sha(P/'P6.expr')==last['expression_sha256']
print('ALL 21 RAW SOURCE BLOCKS, WEIGHTS, MOVING SOURCE, AND 64 TERMINAL OUTPUTS ACCOUNTED FOR')
