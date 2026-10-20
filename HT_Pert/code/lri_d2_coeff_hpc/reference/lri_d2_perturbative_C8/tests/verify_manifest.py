"""Verify distribution bytes before reproduction modifies result records."""
from pathlib import Path
import hashlib
ROOT=Path(__file__).resolve().parents[1]
for line in (ROOT/'MANIFEST.sha256').read_text().splitlines():
    digest,name=line.split('  ',1);p=(ROOT/name).resolve()
    if not p.is_relative_to(ROOT):raise ValueError(name)
    if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:raise AssertionError(name)
print('All manifest entries verified.')
