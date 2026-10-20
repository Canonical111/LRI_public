#!/usr/bin/env python3
"""compare_gen1.py OLD.json NEW.json OUT.json: the J-GEN-1 rerun (CK-K02) against the original J-GEN-1 record.

OLD is stage1/gen1.54631551.0/regress_L3_L7.json (export 36043bb, 601b102's regress.py logic), NEW the rerun's
regress_L3_L7.json. Equal verdicts means: per (sector, L) the same file counts and the same verdict counts (identical,
rate-only, rate-whitespace-only, rate entries differing, other, accepted relabellings, inventory equality), the same
thread identity and controls, both passed with no failures. Keys present only in NEW (the CK-K02 header checks) are
listed and must show no mismatch. Writes schema c8-d2-gen1-compare-1."""
import json, sys
old, new = (json.load(open(p)) for p in sys.argv[1:3])
KEYS = ('frozen_gfiles', 'new_gfiles', 'same_file_set', 'identical', 'rate_only', 'rate_whitespace_only',
        'rate_entries_differing', 'other', 'accepted_relabelling', 'inventory_equal', 'inventory_differences',
        'inventory_bytes_identical')
diff, rows = [], {}
for s in sorted(set(old['sectors']) | set(new['sectors'])):
    o, n = old['sectors'].get(s), new['sectors'].get(s)
    if o is None or n is None:
        diff.append(f'{s}: present only in {"new" if o is None else "old"}'); continue
    rows[s] = {k: n.get(k) for k in KEYS}
    rows[s]['new_only_keys'] = {k: n[k] for k in sorted(set(n) - set(o))}
    for k in KEYS:
        if o.get(k) != n.get(k):
            diff.append(f'{s}.{k}: old {o.get(k)!r} new {n.get(k)!r}')
for k in ('threads_identical', 'controls', 'passed', 'failures', 'free_L3_L6_rate_line_files',
          'free_L3_L6_rate_whitespace_only_files', 'threads', 'loops'):
    if old.get(k) != new.get(k):
        diff.append(f'{k}: old {old.get(k)!r} new {new.get(k)!r}')
top_new = {k: new[k] for k in sorted(set(new) - set(old))}
rec = dict(schema='c8-d2-gen1-compare-1', old=sys.argv[1], new=sys.argv[2], old_passed=old.get('passed'),
           new_passed=new.get('passed'), new_failures=new.get('failures'), sectors=rows,
           top_level_keys_only_in_new=top_new, differences=diff,
           same_verdicts=not diff and old.get('passed') is True and new.get('passed') is True)
open(sys.argv[3], 'w').write(json.dumps(rec, indent=1) + '\n')
print(json.dumps({k: rec[k] for k in ('old_passed', 'new_passed', 'differences', 'same_verdicts')}, indent=1))
sys.exit(0 if rec['same_verdicts'] else 1)
