#!/usr/bin/env python3
"""Verify delivery and reassemble the saved full C7(2), without changing source data."""
from pathlib import Path
import argparse, hashlib, json, shutil, subprocess, sys, tempfile
ROOT=Path(__file__).resolve().parents[1]

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def copy_reassembly_tree(dst):
    # Copy only files used by numerical reassembly, not the large graph kernels.
    for name in ('LRI_C7_d2_progress','power_mass'):
        source=ROOT/name; target=dst/name
        shutil.copytree(source/'code',target/'code',ignore=shutil.ignore_patterns('__pycache__'))
        (target/'inputs').mkdir(parents=True);(target/'verification').mkdir()
        for p in (source/'inputs').glob('*.json'):shutil.copy2(p,target/'inputs'/p.name)
        for L in range(3,8):
            q=target/f'inputs/L{L}';q.mkdir();shutil.copy2(source/f'inputs/L{L}/inventory.json',q/'inventory.json')
        if name=='power_mass':
            (target/'records').mkdir()
            for tag in ('powerA','powerB'):
                for L in range(3,8):
                    for ext in ('json','tasks'):
                        p=source/f'records/{tag}_L{L}.{ext}';shutil.copy2(p,target/'records'/p.name)
                    p=source/f'inputs/{tag}_L{L}.net';shutil.copy2(p,target/'inputs'/p.name)
            shutil.copy2(source/'verification/production_manifest.json',target/'verification/production_manifest.json')
        else:
            for tag in ('productionA','productionB','primitiveA','primitiveB'):
                shutil.copytree(source/'records'/tag,target/'records'/tag)
            p=source/'verification/primitive_completion_checks.json';shutil.copy2(p,target/'verification'/p.name)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--skip-checksums',action='store_true',help='development only; not recommended for a received archive');a=ap.parse_args()
    count=0
    if not a.skip_checksums:
        mf=ROOT/'SHA256SUMS'
        if not mf.exists():raise SystemExit('SHA256SUMS is missing.')
        for line in mf.read_text().splitlines():
            expected,rel=line.split('  ',1);p=ROOT/rel
            if not p.is_file() or sha(p)!=expected:raise SystemExit('Checksum mismatch: '+rel)
            count+=1
    baseline=json.load(open(ROOT/'verification/C7_full_result.json'))
    with tempfile.TemporaryDirectory(prefix='lri_c7d2_reassemble_') as t:
        dst=Path(t);copy_reassembly_tree(dst)
        pr=subprocess.run([sys.executable,str(dst/'power_mass/code/assemble_full.py'),'--bootstrap','4096'],capture_output=True,text=True)
        if pr.returncode:
            sys.stderr.write(pr.stdout+pr.stderr);raise SystemExit(pr.returncode)
        actual=json.load(open(dst/'power_mass/verification/C7_full_result.json'))
    fields=('C7_full','sampling_se','power_correction','power_correction_se','power_free_C7','power_free_se')
    errors={k:abs(actual[k]-baseline[k])for k in fields}
    if max(errors.values())>2e-8:raise SystemExit('Reassembly mismatch: '+str(errors))
    out=dict(status='passed',checksummed_payloads=count,integrations_rerun=False,source_files_overwritten=False,result={k:actual[k]for k in fields},max_absolute_reassembly_difference=max(errors.values()),cross_platform_tolerance=2e-8,bootstrap_replicates=4096)
    print(json.dumps(out,indent=2))
if __name__=='__main__':main()
