#!/usr/bin/env python3
"""tests/verify_manifest.py for the public tree. MANIFEST.sha256 ships verbatim from the delivered package; two of its files
(code/ht2d/hpc.py, code/ht2d/solver.py) were changed by the Expanse-layer commits and are checked against their sha256
at the production commit 889a968 (public/MANIFEST_889a968_changes.txt). Files whose bytes the public placeholder scrub
changed are listed in public/SCRUBBED.txt and reported, not failed. Any other mismatch or missing file fails."""
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
scrubbed = set()
s = ROOT / "public" / "SCRUBBED.txt"
if s.exists():
    scrubbed = {l.strip() for l in s.read_text().splitlines() if l.strip() and not l.startswith("#")}
changed = {}
for line in (ROOT / "public" / "MANIFEST_889a968_changes.txt").read_text().splitlines():
    if line.strip() and not line.startswith("#"):
        d, name = line.split("  ", 1)
        changed[name] = d
ok = n = 0
bad = []
for line in (ROOT / "MANIFEST.sha256").read_text().splitlines():
    digest, name = line.split("  ", 1)
    p = ROOT / name
    if name in changed:
        print(f"changed after delivery, checked at 889a968: {name}")
        digest = changed[name]
    n += 1
    if p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest() == digest:
        ok += 1
    elif name in scrubbed and p.is_file():
        print(f"scrubbed (placeholder tokens): {name}")
    else:
        bad.append(name)
for b in bad:
    print(f"FAIL {'changed' if (ROOT / b).exists() else 'missing'}: {b}")
print(f"{ok}/{n} files byte-identical to MANIFEST.sha256 (2 of them to the 889a968 list), {len(scrubbed)} listed as scrubbed, {len(bad)} failures")
sys.exit(1 if bad else 0)
