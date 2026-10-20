#!/usr/bin/env python3
"""J-DRL-8 record (A-ORC-12 on real Slurm, R03; F8 rerun): the recovery of a completed index, unattended.
  drl8_check.py RUN SAVED GROUP CHECKPOINT INDEX OUT.json
SAVED holds the copies made before the deletion: SAVED/merged/<group>/merged.json for all 24 groups, SAVED/<CHECKPOINT>
(the deleted checkpoint) and SAVED/C8_test_result.json. Checks: the recomputed checkpoint's scientific row fields equal
the saved ones and it was recomputed (new fingerprint or integration time); all 24 merged.json batches bitwise equal to
the saved ones (canonical JSON); lanes/done_invalidated.jsonl names INDEX; the result was superseded, not refused: the
new C8_test_result.json differs from the saved one only in the merged_sha256 of GROUP, and the saved bytes are kept as
C8_test_result.superseded.<sha12>.json."""
import glob, hashlib, json, os, sys
run, saved, group, ckpt, index, out = sys.argv[1:7]; index = int(index)
SCI = ('uid', 'rep', 'graph', 'begin', 'end', 'total', 'values', 'quad', 'mp', 'max_abs', 'tail_top', 'tail_sum', 'tail_argmax')
old = json.load(open(os.path.join(saved, os.path.basename(ckpt)))); new = json.load(open(os.path.join(run, 'groups', group, 'checkpoints', os.path.basename(ckpt))))
ro, rn = old['native']['rows'], new['native']['rows']
res = {'index': index, 'group': group, 'checkpoint': f'groups/{group}/checkpoints/{os.path.basename(ckpt)}', 'rows': len(rn),
       'scientific_fields_equal': len(ro) == len(rn) and all(all(a.get(k) == b.get(k) for k in SCI) for a, b in zip(ro, rn)),
       'recomputed': old['native'].get('integration_seconds') != new['native'].get('integration_seconds') or old['runtime']['fingerprint'] != new['runtime']['fingerprint'],
       'old_job': (old['runtime']['fingerprint'].get('slurm') or {}).get('SLURM_JOB_ID'), 'new_job': (new['runtime']['fingerprint'].get('slurm') or {}).get('SLURM_JOB_ID'),
       'new_runtime_cpu': new['runtime'].get('cpu')}
mb = {}
for d in sorted(os.listdir(os.path.join(saved, 'merged'))):
    a = json.load(open(os.path.join(saved, 'merged', d, 'merged.json'))); b = json.load(open(os.path.join(run, 'groups', d, 'merged.json')))
    mb[d] = json.dumps(a['batches'], sort_keys=True) == json.dumps(b['batches'], sort_keys=True)
res['merged_batches_equal'] = mb; res['all_24_batches_equal'] = len(mb) == 24 and all(mb.values())
inv = [json.loads(l) for l in open(os.path.join(run, 'lanes', 'done_invalidated.jsonl'))]
res['done_invalidated'] = inv; res['names_index'] = any(x.get('index') == index for x in inv)
sold = open(os.path.join(saved, 'C8_test_result.json'), 'rb').read(); snew = open(os.path.join(run, 'C8_test_result.json'), 'rb').read()
h12 = hashlib.sha256(sold).hexdigest()[:12]; sup = os.path.join(run, f'C8_test_result.superseded.{h12}.json')
res['result'] = {'saved_sha256': hashlib.sha256(sold).hexdigest(), 'new_sha256': hashlib.sha256(snew).hexdigest(),
                 'superseded_copy': os.path.basename(sup), 'superseded_copy_exists': os.path.exists(sup),
                 'superseded_copy_equals_saved': os.path.exists(sup) and open(sup, 'rb').read() == sold,
                 'all_superseded_files': sorted(os.path.basename(p) for p in glob.glob(os.path.join(run, 'C8_test_result.superseded.*.json')))}
def diff(a, b, path=''):
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in sorted(set(a) | set(b)): out += diff(a.get(k), b.get(k), f'{path}/{k}')
        return out
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        out = []
        for i, (x, y) in enumerate(zip(a, b)): out += diff(x, y, f'{path}[{i}]')
        return out
    return [] if a == b else [path]
d = diff(json.loads(sold), json.loads(snew)); res['result']['differing_paths'] = d
res['result']['only_merged_sha256_of_group_changed'] = bool(d) and all('merged_sha256' in p for p in d) and all(group in p for p in d)
res['passed'] = (res['scientific_fields_equal'] and res['recomputed'] and res['all_24_batches_equal'] and res['names_index']
                 and res['result']['superseded_copy_equals_saved'] and res['result']['only_merged_sha256_of_group_changed'])
json.dump(res, open(out, 'w'), indent=1); print(json.dumps({k: v for k, v in res.items() if k not in ('merged_batches_equal', 'done_invalidated')}))
sys.exit(0 if res['passed'] else 1)
