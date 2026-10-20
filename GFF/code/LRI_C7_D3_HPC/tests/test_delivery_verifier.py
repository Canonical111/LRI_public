#!/usr/bin/env python3
"""Non-destructive positive and negative tests for the delivery verifier."""
from pathlib import Path
import hashlib, json, shutil, subprocess, sys, tempfile
ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
with tempfile.TemporaryDirectory(prefix='c7d3_delivery_check_') as tmp:
    r = Path(tmp); (r/'tools').mkdir()
    shutil.copy2(ROOT/'tools/verify_delivery.py', r/'tools/verify_delivery.py')
    (r/'payload.txt').write_text('unchanged data\n')
    rows = [dict(path=p.relative_to(r).as_posix(), bytes=p.stat().st_size, sha256=sha(p))
            for p in sorted(r.rglob('*')) if p.is_file()]
    doc = dict(schema='lri-c7-d3-hpc-delivery-1', files=rows, payload_file_count=len(rows),
               payload_bytes=sum(x['bytes'] for x in rows))
    (r/'DELIVERY_MANIFEST.json').write_text(json.dumps(doc))
    checks = {x['path']:x['sha256'] for x in rows}
    checks['DELIVERY_MANIFEST.json'] = sha(r/'DELIVERY_MANIFEST.json')
    (r/'SHA256SUMS').write_text(''.join(f'{h}  {n}\n' for n,h in sorted(checks.items())))
    results = []
    def call(name, passed, strict=True):
        cmd=[sys.executable, str(r/'tools/verify_delivery.py')]
        if strict: cmd+=['--strict']
        cp=subprocess.run(cmd, cwd='/', capture_output=True,text=True)
        data=json.loads(cp.stdout)
        assert (cp.returncode==0)==passed,(name,data)
        results.append(dict(test=name,status='passed',expected_verifier_status=data['status']))
    call('valid_package_from_another_directory',True)
    (r/'payload.txt').write_text('changed data\n');call('changed_payload_rejected',False)
    (r/'payload.txt').write_text('unchanged data\n')
    (r/'payload.txt').unlink();call('missing_payload_rejected',False)
    (r/'payload.txt').write_text('unchanged data\n')
    old=(r/'SHA256SUMS').read_text();(r/'SHA256SUMS').write_text(old.replace('a','b',1))
    call('changed_checksum_index_rejected',False);(r/'SHA256SUMS').write_text(old)
    (r/'local_build').write_text('allowed only in non-strict mode')
    call('unexpected_file_rejected_in_strict_mode',False)
    call('local_build_allowed_in_default_mode',True,False)
    doc['files'][0]['path']='../escape.txt'
    (r/'DELIVERY_MANIFEST.json').write_text(json.dumps(doc))
    call('unsafe_path_rejected',False)
    print(json.dumps(dict(status='passed',tests=results),indent=2))
