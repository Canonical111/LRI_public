#!/usr/bin/env python3
"""Non-destructive positive and negative tests for the delivery verifier (tools/verify_delivery.py), including R16: a
tracked internal relative symlink and an escaping one are each rejected by --strict (listed in the manifest, or only
present), a listed path with a symlinked directory component fails both modes, and --write refuses to record a tracked
symlink.

Every negative case asserts the verifier's exact error list, so it fails for the reason it names and no other. The
unsafe-path cases (Stage-6 X20) list one unsafe or noncanonical path (escaping, absolute, internal '..', backslash,
'./', '//') whose file exists, with its true size and digest, the manifest totals and SHA256SUMS refreshed and no
stray file: the only defect is the path. A control runs the same fixtures through the verifier with its path-safety
checks removed (safe_file reduced to "an existing regular file") and requires that they pass, so the rejection comes
from those checks alone.

W13 (Stage-6 fix round 4, S6D-R4-04 and S6G4-01): in a scratch git package with the result verifier's dependencies, a
real C8 result record, a historical C7 record and a JSON note that only mentions the result schema, --write lists the
one record in result_records and --strict verifies it with tools/verify_result.py. A deleted gates block, an
inconsistent coefficient, an added key and a changed schema (the record stays listed), each with regenerated delivery
checksums, fail both modes and --write (nothing written); an unlisted record, a truncated one and a listed absent one
fail; a negative fixture is excluded only by name (NEGATIVE_FIXTURES). Before the fix --write and --strict passed a
record without its gates block."""
from pathlib import Path
import hashlib, importlib.util, json, shutil, subprocess, sys, tempfile
ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
with tempfile.TemporaryDirectory(prefix='c8d2_delivery_check_') as tmp:
    r = Path(tmp)/'pkg'; (r/'tools').mkdir(parents=True)  # the package root; tmp/escape.txt is a real file outside it
    shutil.copy2(ROOT/'tools/verify_delivery.py', r/'tools/verify_delivery.py')
    (r/'payload.txt').write_text('unchanged data\n')
    outside = Path(tmp)/'escape.txt'; outside.write_text('outside the package\n')
    rows = [dict(path=p.relative_to(r).as_posix(), bytes=p.stat().st_size, sha256=sha(p))
            for p in sorted(r.rglob('*')) if p.is_file()]
    def publish(files):
        """Write a self-consistent manifest over `files` (totals) and a matching SHA256SUMS."""
        d = dict(schema='lri-c8-d2-hpc-delivery-1', files=files, payload_file_count=len(files),
                 payload_bytes=sum(x['bytes'] for x in files))
        (r/'DELIVERY_MANIFEST.json').write_text(json.dumps(d))
        checks = {x['path']:x['sha256'] for x in files}
        checks['DELIVERY_MANIFEST.json'] = sha(r/'DELIVERY_MANIFEST.json')
        (r/'SHA256SUMS').write_text(''.join(f'{h}  {n}\n' for n,h in sorted(checks.items())))
        return d
    publish(rows)
    results = []
    def call(name, passed, strict=True, errors=None):
        cmd=[sys.executable, str(r/'tools/verify_delivery.py')]
        if strict: cmd+=['--strict']
        cp=subprocess.run(cmd, cwd='/', capture_output=True,text=True)
        data=json.loads(cp.stdout)
        assert (cp.returncode==0)==passed,(name,data)
        assert passed or errors is not None,(name,'a negative case names its exact errors')
        if errors is not None: assert data['errors']==errors,(name,data['errors'],errors)
        results.append(dict(test=name,status='passed',expected_verifier_status=data['status'],errors=[e.replace(tmp,'<tmp>')for e in data['errors']]))
    call('valid_package_from_another_directory',True)
    (r/'payload.txt').write_text('changed data\n')
    call('changed_payload_rejected',False,errors=['Size mismatch: payload.txt','SHA-256 mismatch: payload.txt'])
    (r/'payload.txt').write_text('unchanged data\n')
    (r/'payload.txt').unlink();call('missing_payload_rejected',False,errors=['Missing regular file: payload.txt'])
    (r/'payload.txt').write_text('unchanged data\n')
    old=(r/'SHA256SUMS').read_text();(r/'SHA256SUMS').write_text(old.replace('a','b',1))
    call('changed_checksum_index_rejected',False,errors=['SHA256SUMS does not match the payload plus delivery manifest'])
    (r/'SHA256SUMS').write_text(old)
    (r/'local_build').write_text('allowed only in non-strict mode')
    call('unexpected_file_rejected_in_strict_mode',False,errors=['1 unexpected files in strict mode'])
    call('local_build_allowed_in_default_mode',True,False)
    (r/'local_build').unlink();call('local_build_removed_passes',True)
    # X20: one unsafe or noncanonical path in an otherwise consistent package, rejected by its own diagnostic in both
    # modes; the control (path checks removed) accepts each fixture.
    spec=importlib.util.spec_from_file_location('verify_delivery_lax',r/'tools/verify_delivery.py')
    lax=importlib.util.module_from_spec(spec);spec.loader.exec_module(lax)
    def lax_safe_file(root,name):
        t=Path(root)/name
        if not t.is_file():raise ValueError('Missing regular file: '+name)
        return t
    lax.safe_file=lax_safe_file
    backslash=r/'payload\\alias.txt'
    unsafe=(('../escape.txt',outside),(str(outside),outside),('tools/../payload.txt',r/'payload.txt'),
            ('payload\\alias.txt',backslash),('./payload.txt',r/'payload.txt'),('tools//verify_delivery.py',r/'tools/verify_delivery.py'))
    for name,target in unsafe:
        if target==backslash:backslash.write_text('one file whose name holds a backslash\n')
        publish(rows+[dict(path=name,bytes=target.stat().st_size,sha256=sha(target))])
        for strict in (True,False):
            control=lax.verify(r,strict)
            assert control['status']=='passed' and not control['errors'],(name,strict,'control',control)
            call(f'unsafe_path_rejected_{"strict"if strict else"default"}:{name.replace(tmp,"<tmp>")}',False,strict,
                 errors=['Unsafe or noncanonical path: '+repr(name)])
        if target==backslash:backslash.unlink()
    publish(rows);call('unsafe_paths_removed_passes',True)
    # --write in a git checkout: regenerates both files from the index; build outputs and caches stay excluded.
    git=lambda *a:subprocess.run(['git','-C',str(r),*a],capture_output=True,text=True,check=True)
    if shutil.which('git'):
        git('init','-q');(r/'.gitignore').write_text('bin/\n__pycache__/\n');(r/'bin').mkdir();(r/'bin/exe').write_text('x');(r/'tools/__pycache__').mkdir();(r/'tools/__pycache__/v.pyc').write_text('x')
        (r/'new.txt').write_text('added\n');w=subprocess.run([sys.executable,str(r/'tools/verify_delivery.py'),'--write'],capture_output=True,text=True)
        assert w.returncode!=0 and 'git add -A'in w.stdout,w.stdout
        git('add','-A');w=subprocess.run([sys.executable,str(r/'tools/verify_delivery.py'),'--write'],capture_output=True,text=True);assert w.returncode==0,w.stdout
        m=json.loads((r/'DELIVERY_MANIFEST.json').read_text());names={f['path']for f in m['files']}
        assert names=={'payload.txt','new.txt','.gitignore','tools/verify_delivery.py'},names
        call('write_then_strict_passes_with_build_outputs_present',True)
        (r/'new.txt').write_text('changed\n');call('write_then_changed_file_rejected',False,errors=['Size mismatch: new.txt','SHA-256 mismatch: new.txt'])
        (r/'new.txt').write_text('added\n');call('write_restored_passes',True)
        # R16: symlinks. An unlisted internal or escaping symlink fails --strict; listed in the manifest (as --write of
        # an older verifier would have recorded it, through the link), each fails both modes; --write refuses them.
        good=json.loads((r/'DELIVERY_MANIFEST.json').read_text());good_sums=(r/'SHA256SUMS').read_text()
        for name,target in (('link_internal','payload.txt'),('link_escape','../../../../../../etc/hosts')):
            (r/name).symlink_to(target)
            call(f'{name}_present_rejected_in_strict_mode',False,errors=['1 unexpected files in strict mode'])
            git('add','-A');w=subprocess.run([sys.executable,str(r/'tools/verify_delivery.py'),'--write'],capture_output=True,text=True)
            assert w.returncode!=0 and 'tracked symlinks'in w.stdout,w.stdout
            assert json.loads((r/'DELIVERY_MANIFEST.json').read_text())==good,'--write changed the manifest'
            doc2=dict(good);data=(r/target).read_bytes()if name=='link_internal'else b'x'
            doc2['files']=good['files']+[dict(path=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest())]
            doc2['payload_file_count']=len(doc2['files']);doc2['payload_bytes']=sum(x['bytes']for x in doc2['files'])
            (r/'DELIVERY_MANIFEST.json').write_text(json.dumps(doc2))
            sums={x['path']:x['sha256']for x in doc2['files']};sums['DELIVERY_MANIFEST.json']=sha(r/'DELIVERY_MANIFEST.json')
            (r/'SHA256SUMS').write_text(''.join(f'{h}  {n}\n'for n,h in sorted(sums.items())))
            want=['Symlink or escaping path: '+repr(name)]
            call(f'{name}_listed_rejected_strict',False,errors=want);call(f'{name}_listed_rejected_default',False,False,errors=want)
            (r/'DELIVERY_MANIFEST.json').write_text(json.dumps(good,indent=2)+'\n');(r/'SHA256SUMS').write_text(good_sums)
            git('rm','-q','--cached',name);(r/name).unlink()
        call('symlinks_removed_passes',True)
        # R16 for a directory symlink inside a listed path (Stage-6 fix round 1, G4's observation): 'sub' links to
        # tools/, and 'sub/verify_delivery.py' is listed with its true size and digest. A check of the final component
        # alone passed default mode; every component of a listed path is now checked, in both modes.
        (r/'sub').symlink_to('tools');t=r/'tools/verify_delivery.py'
        doc2=dict(good);doc2['files']=good['files']+[dict(path='sub/verify_delivery.py',bytes=t.stat().st_size,sha256=sha(t))]
        doc2['payload_file_count']=len(doc2['files']);doc2['payload_bytes']=sum(x['bytes']for x in doc2['files'])
        (r/'DELIVERY_MANIFEST.json').write_text(json.dumps(doc2))
        sums={x['path']:x['sha256']for x in doc2['files']};sums['DELIVERY_MANIFEST.json']=sha(r/'DELIVERY_MANIFEST.json')
        (r/'SHA256SUMS').write_text(''.join(f'{h}  {n}\n'for n,h in sorted(sums.items())))
        want=['Symlink or escaping path: '+repr('sub/verify_delivery.py')]
        call('dir_symlink_component_listed_rejected_strict',False,errors=want+['1 unexpected files in strict mode'])
        call('dir_symlink_component_listed_rejected_default',False,False,errors=want)
        (r/'DELIVERY_MANIFEST.json').write_text(json.dumps(good,indent=2)+'\n');(r/'SHA256SUMS').write_text(good_sums);(r/'sub').unlink()
        call('dir_symlink_removed_passes',True)
# W13 (Stage-6 fix round 4, S6D-R4-04 / S6G4-01): the delivered C8 result records are verified by tools/verify_result.py
# in both modes. A scratch package with the verifier's dependencies (tools/, the vendored assembly, inputs/two_loop.json),
# one real result record, a historical C7 record and a JSON document that only mentions the result schema. Each damaged
# record has otherwise valid, regenerated delivery checksums (the finding's case): before the fix --strict passed it.
def regenerate(r):
    """Every manifest row and SHA256SUMS recomputed from the files on disk (a maintainer's hand edit, not --write)."""
    d=json.loads((r/'DELIVERY_MANIFEST.json').read_text())
    for x in d['files']:p=r/x['path'];x['bytes']=p.stat().st_size;x['sha256']=sha(p)
    d['payload_file_count']=len(d['files']);d['payload_bytes']=sum(x['bytes']for x in d['files'])
    (r/'DELIVERY_MANIFEST.json').write_text(json.dumps(d,indent=2)+'\n')
    sums={x['path']:x['sha256']for x in d['files']};sums['DELIVERY_MANIFEST.json']=sha(r/'DELIVERY_MANIFEST.json')
    (r/'SHA256SUMS').write_text(''.join(f'{h}  {n}\n'for n,h in sorted(sums.items(),key=lambda t:t[0].encode())))
def run_vd(r,*args):
    cp=subprocess.run([sys.executable,'-B',str(r/'tools/verify_delivery.py'),*args],cwd='/',capture_output=True,text=True)
    return cp.returncode,json.loads(cp.stdout)
if shutil.which('git'):
    with tempfile.TemporaryDirectory(prefix='c8d2_delivery_results_') as tmp:
        r=Path(tmp)/'pkg';rec='results/C8_test_result.json'
        for f in ROOT.joinpath('tools').iterdir():
            if f.is_file() and f.suffix in ('.py','.json'):(r/'tools').mkdir(parents=True,exist_ok=True);shutil.copy2(f,r/'tools'/f.name)
        shutil.copytree(ROOT/'vendor/c8_assembly',r/'vendor/c8_assembly',ignore=shutil.ignore_patterns('__pycache__','.DS_Store','.pytest_cache'))
        (r/'inputs').mkdir();shutil.copy2(ROOT/'inputs/two_loop.json',r/'inputs/two_loop.json')
        (r/'results').mkdir();good=(ROOT/'tests/fixtures/verify_result_cross_machine/smoke1-20261005.json').read_bytes();(r/rec).write_bytes(good)
        (r/'reference').mkdir();shutil.copy2(ROOT/'reference/c7d2_production_2026/C7_result.json',r/'reference/C7_result.json')
        (r/'results/verify_note.json').write_text(json.dumps({'schema':'c8-d2-verify-result-1','about':'a c8-d2-hpc-result-1 record'}))
        g=lambda *a:subprocess.run(['git','-C',str(r),*a],capture_output=True,text=True,check=True)
        g('init','-q');(r/'.gitignore').write_text('__pycache__/\n');g('add','-A')
        rc,w=run_vd(r,'--write');assert rc==0 and w['result_records']==1,w
        m=json.loads((r/'DELIVERY_MANIFEST.json').read_text());assert m['result_records']==[rec],m.get('result_records')  # the C7 record and the note are not records
        rc,v=run_vd(r,'--strict');assert rc==0 and v['result_records_verified']==1,v;results.append(dict(test='W13_write_lists_the_record_strict_verifies_it',status='passed'))
        good_m=(r/'DELIVERY_MANIFEST.json').read_text();good_s=(r/'SHA256SUMS').read_text()
        def damaged(name,edit,needle,write_refused=True):
            doc=json.loads(good);edit(doc);(r/rec).write_text(json.dumps(doc,indent=1)+'\n');regenerate(r)
            for mode in (('--strict',),()):
                rc,v=run_vd(r,*mode);errs=v['errors']
                assert rc==1 and len(errs)==1 and errs[0].startswith('Result record fails tools/verify_result.py')and needle in errs[0]and errs[0].endswith(rec),(name,mode,errs)
            if write_refused:
                g('add','-A');before=(r/'DELIVERY_MANIFEST.json').read_text();rc,w=run_vd(r,'--write')
                assert rc==1 and 'fail tools/verify_result.py; nothing written'in w['errors'][0]and (r/'DELIVERY_MANIFEST.json').read_text()==before,(name,w)
            (r/rec).write_bytes(good);(r/'DELIVERY_MANIFEST.json').write_text(good_m);(r/'SHA256SUMS').write_text(good_s);g('add','-A')
            assert run_vd(r,'--strict')[0]==0;results.append(dict(test=f'W13_{name}_rejected_both_modes_and_by_write',status='passed'))
        damaged('deleted_gates_block',lambda d:d['test_partial'].pop('gates'),'gates')
        damaged('inconsistent_coefficient',lambda d:d['test_partial'].__setitem__('C8_full',d['test_partial']['C8_full']+1e-3),'C8_full')
        damaged('added_key',lambda d:d.__setitem__('extra_key',1),'extra_key')
        damaged('schema_changed_still_listed',lambda d:d.__setitem__('schema','c8-d2-hpc-result-0'),'not a c8-d2-hpc-result-1 result')  # sticky: --write keeps it listed
        # an unlisted record (dropped from result_records, checksums regenerated) and a second record never listed
        m=json.loads(good_m);m['result_records']=[];(r/'DELIVERY_MANIFEST.json').write_text(json.dumps(m,indent=2)+'\n');regenerate(r)
        rc,v=run_vd(r,'--strict');assert rc==1 and v['errors']==['C8 result record not in result_records (run --write): '+rec],v['errors']
        (r/'DELIVERY_MANIFEST.json').write_text(good_m);(r/'SHA256SUMS').write_text(good_s)
        (r/'results/second.json').write_bytes(good);m=json.loads(good_m);t=r/'results/second.json'
        m['files'].append(dict(path='results/second.json',bytes=t.stat().st_size,sha256=sha(t)));(r/'DELIVERY_MANIFEST.json').write_text(json.dumps(m,indent=2)+'\n');regenerate(r)
        rc,v=run_vd(r);assert rc==1 and v['errors']==['C8 result record not in result_records (run --write): results/second.json'],v['errors']
        (r/'results/second.json').write_bytes(good[:len(good)//2]);regenerate(r)  # a truncated record naming the schema
        rc,v=run_vd(r);assert rc==1 and v['errors']==['Unparsable file naming the C8 result schema, not in result_records: results/second.json'],v['errors']
        (r/'results/second.json').unlink();(r/'DELIVERY_MANIFEST.json').write_text(good_m);(r/'SHA256SUMS').write_text(good_s)
        m=json.loads(good_m);m['result_records']=[rec,'results/absent.json'];(r/'DELIVERY_MANIFEST.json').write_text(json.dumps(m,indent=2)+'\n');regenerate(r)
        rc,v=run_vd(r);assert rc==1 and v['errors']==['Result record not a listed payload file: results/absent.json'],v['errors']
        (r/'DELIVERY_MANIFEST.json').write_text(good_m);(r/'SHA256SUMS').write_text(good_s)
        results.append(dict(test='W13_unlisted_truncated_and_absent_records_rejected',status='passed'))
        # a negative fixture is excluded only by name (NEGATIVE_FIXTURES); control: the damaged record passes only then
        spec=importlib.util.spec_from_file_location('verify_delivery_neg',r/'tools/verify_delivery.py');neg=importlib.util.module_from_spec(spec);spec.loader.exec_module(neg)
        doc=json.loads(good);doc['test_partial'].pop('gates');(r/rec).write_text(json.dumps(doc));m=json.loads(good_m);m['result_records']=[]
        (r/'DELIVERY_MANIFEST.json').write_text(json.dumps(m,indent=2)+'\n');regenerate(r)
        assert neg.verify(r,True)['status']=='failed'
        neg.NEGATIVE_FIXTURES={rec:'test: an intentionally invalid record'};x=neg.verify(r,True);assert x['status']=='passed'and not x['errors'],x
        m['result_records']=[rec];(r/'DELIVERY_MANIFEST.json').write_text(json.dumps(m,indent=2)+'\n');regenerate(r)
        x=neg.verify(r,True);assert x['errors']==['Result record listed and excluded as a negative fixture: '+rec],x['errors']
        (r/rec).write_bytes(good);(r/'DELIVERY_MANIFEST.json').write_text(good_m);(r/'SHA256SUMS').write_text(good_s)
        assert run_vd(r,'--strict')[0]==0;results.append(dict(test='W13_negative_fixture_excluded_only_by_name',status='passed'))
print(json.dumps(dict(status='passed',tests=results),indent=2))
