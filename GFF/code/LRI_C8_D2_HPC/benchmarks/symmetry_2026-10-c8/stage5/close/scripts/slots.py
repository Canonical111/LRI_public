#!/usr/bin/env python3
"""slots.py MANIFEST: the SLOTS string of fix/scripts/fxio.slurm for a campaign planned like io-2b3a9233353d.

The A-ORC-13 rerun after the F12 fix runs the same 22 claims, by (group, shard), as the fix round's job 570170
(SLOTS '38;39;40;41;42;43;6;0,1,17,18,19,33,34,48,50,2,35,20,51,3,36' of io-2b3a9233353d): six b_free_L8 indices
(shards 0-5), one per slot; a_free_L8 shard 0; and, one after the other in the eighth slot, shard 0 of a_free_L3,
a_free_L4, a_power_L3, a_power_L4, a_power_L5, b_free_L3, b_free_L4, b_power_L3, b_power_L5, a_free_L5, b_free_L5,
a_power_L6, b_power_L6, a_free_L6, b_free_L6. The indices are looked up in MANIFEST's job table, so a new plan's
numbering is followed; a missing (group, shard) refuses (exit 64). Prints the SLOTS string and, on stderr, the table."""
import json, sys
m = json.load(open(sys.argv[1]))
by = {(j['group'], j['shard']): j for j in m['jobs']}
want = [[('b_free_L8', s)] for s in range(6)] + [[('a_free_L8', 0)]] + [[(g, 0) for g in (
    'a_free_L3', 'a_free_L4', 'a_power_L3', 'a_power_L4', 'a_power_L5', 'b_free_L3', 'b_free_L4', 'b_power_L3',
    'b_power_L5', 'a_free_L5', 'b_free_L5', 'a_power_L6', 'b_power_L6', 'a_free_L6', 'b_free_L6')]]
miss = [k for slot in want for k in slot if k not in by]
if miss:
    sys.exit(f'not in the manifest: {miss}')
for k, slot in enumerate(want):
    for g in slot:
        j = by[g]; print(f'slot {k} index {j["id"]} {g[0]} shard {g[1]} tasks {j["tasks"]} est {j["est_core_seconds"]:.0f} core-s', file=sys.stderr)
print(';'.join(','.join(str(by[g]['id']) for g in slot) for slot in want))
