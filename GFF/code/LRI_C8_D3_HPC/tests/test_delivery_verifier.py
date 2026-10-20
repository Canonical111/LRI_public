#!/usr/bin/env python3
"""Non-destructive positive and negative tests for the delivery verifier (tools/verify_delivery.py), including R16: a
tracked internal relative symlink and an escaping one are each rejected by --strict (listed in the manifest, or only
present), and --write refuses to record a tracked symlink. A .pytest_cache/ directory (any depth) is a cache like
__pycache__/: --strict passes with it and --write neither lists it nor refuses an untracked one; only that exact
component name is skipped (.pytest_cache_notes.txt and pytest_cache/ are unexpected files), and a changed listed file
still fails with it present."""
from pathlib import Path
import hashlib, json, shutil, subprocess, sys, tempfile
ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
with tempfile.TemporaryDirectory(prefix='c8d3_delivery_check_') as tmp:
    r = Path(tmp); (r/'tools').mkdir()
    shutil.copy2(ROOT/'tools/verify_delivery.py', r/'tools/verify_delivery.py')
    (r/'payload.txt').write_text('unchanged data\n')
    rows = [dict(path=p.relative_to(r).as_posix(), bytes=p.stat().st_size, sha256=sha(p))
            for p in sorted(r.rglob('*')) if p.is_file()]
    doc = dict(schema='lri-c8-d3-hpc-delivery-1', files=rows, payload_file_count=len(rows),
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
    for f in ('.pytest_cache/v/cache/nodeids','tools/.pytest_cache/README.md'):(r/f).parent.mkdir(parents=True,exist_ok=True);(r/f).write_text('x\n')
    call('pytest_cache_ignored_in_strict_mode',True)
    (r/'.pytest_cache_notes.txt').write_text('x\n');call('pytest_cache_lookalike_file_rejected_in_strict_mode',False);(r/'.pytest_cache_notes.txt').unlink()
    (r/'pytest_cache').mkdir();(r/'pytest_cache/x').write_text('x\n');call('pytest_cache_without_dot_rejected_in_strict_mode',False);shutil.rmtree(r/'pytest_cache')
    (r/'payload.txt').write_text('changed data\n');call('changed_payload_rejected_with_pytest_cache_present',False);(r/'payload.txt').write_text('unchanged data\n')
    call('pytest_cache_present_passes_again',True)
    (r/'local_build').write_text('allowed only in non-strict mode')
    call('unexpected_file_rejected_in_strict_mode',False)
    call('local_build_allowed_in_default_mode',True,False)
    doc['files'][0]['path']='../escape.txt'
    (r/'DELIVERY_MANIFEST.json').write_text(json.dumps(doc))
    call('unsafe_path_rejected',False)
    (r/'local_build').unlink()
    # --write in a git checkout: regenerates both files from the index; build outputs and caches stay excluded.
    git=lambda *a:subprocess.run(['git','-C',str(r),*a],capture_output=True,text=True,check=True)
    if shutil.which('git'):
        git('init','-q');(r/'.gitignore').write_text('bin/\n__pycache__/\n');(r/'bin').mkdir();(r/'bin/exe').write_text('x');(r/'tools/__pycache__').mkdir();(r/'tools/__pycache__/v.pyc').write_text('x')
        (r/'new.txt').write_text('added\n');w=subprocess.run([sys.executable,str(r/'tools/verify_delivery.py'),'--write'],capture_output=True,text=True)
        assert w.returncode!=0 and 'git add -A'in w.stdout,w.stdout
        git('add','-A');(r/'.pytest_cache/x').write_text('untracked\n')   # the .gitignore lacks .pytest_cache/: an untracked cache file
        assert '.pytest_cache/x'in git('ls-files','--others','--exclude-standard').stdout
        w=subprocess.run([sys.executable,str(r/'tools/verify_delivery.py'),'--write'],capture_output=True,text=True);assert w.returncode==0,w.stdout
        m=json.loads((r/'DELIVERY_MANIFEST.json').read_text());names={f['path']for f in m['files']}
        assert names=={'payload.txt','new.txt','.gitignore','tools/verify_delivery.py'},names   # no .pytest_cache file, tracked or not
        call('write_then_strict_passes_with_build_outputs_present',True)
        (r/'new.txt').write_text('changed\n');call('write_then_changed_file_rejected',False)
        (r/'new.txt').write_text('added\n');call('write_restored_passes',True)
        # R16: symlinks. An unlisted internal or escaping symlink fails --strict; listed in the manifest (as --write of
        # an older verifier would have recorded it, through the link), each fails both modes; --write refuses them.
        good=json.loads((r/'DELIVERY_MANIFEST.json').read_text());good_sums=(r/'SHA256SUMS').read_text()
        for name,target in (('link_internal','payload.txt'),('link_escape','../../../../../../etc/hosts')):
            (r/name).symlink_to(target)
            call(f'{name}_present_rejected_in_strict_mode',False)
            git('add','-A');w=subprocess.run([sys.executable,str(r/'tools/verify_delivery.py'),'--write'],capture_output=True,text=True)
            assert w.returncode!=0 and 'tracked symlinks'in w.stdout,w.stdout
            assert json.loads((r/'DELIVERY_MANIFEST.json').read_text())==good,'--write changed the manifest'
            doc2=dict(good);data=(r/target).read_bytes()if name=='link_internal'else b'x'
            doc2['files']=good['files']+[dict(path=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest())]
            doc2['payload_file_count']=len(doc2['files']);doc2['payload_bytes']=sum(x['bytes']for x in doc2['files'])
            (r/'DELIVERY_MANIFEST.json').write_text(json.dumps(doc2))
            sums={x['path']:x['sha256']for x in doc2['files']};sums['DELIVERY_MANIFEST.json']=sha(r/'DELIVERY_MANIFEST.json')
            (r/'SHA256SUMS').write_text(''.join(f'{h}  {n}\n'for n,h in sorted(sums.items())))
            call(f'{name}_listed_rejected_strict',False);call(f'{name}_listed_rejected_default',False,False)
            (r/'DELIVERY_MANIFEST.json').write_text(json.dumps(good,indent=2)+'\n');(r/'SHA256SUMS').write_text(good_sums)
            git('rm','-q','--cached',name);(r/name).unlink()
        call('symlinks_removed_passes',True)
    print(json.dumps(dict(status='passed',tests=results),indent=2))
