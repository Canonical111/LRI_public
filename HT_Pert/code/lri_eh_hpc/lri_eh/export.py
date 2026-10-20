from __future__ import annotations
import json
from pathlib import Path
from .runtime import validate_result,atomic_json

def export(paths,expected_source,output):
    rows={}
    for p in paths:
        r=validate_result(json.loads(Path(p).read_text()))
        if r['source_sha256']!=expected_source:raise ValueError(f'Unexpected correction source: {p}')
        key=(r['degree'],r['cutoff'])
        if key in rows:raise ValueError(f'Duplicate correction: {key}')
        rows[key]=r
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    atomic_json(output,[rows[k] for k in sorted(rows)])
