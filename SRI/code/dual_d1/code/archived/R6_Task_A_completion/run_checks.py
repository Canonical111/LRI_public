"""Verify exact source coverage, the residue sum, and independent divergence checks.
Default checks require only Python's standard library and operate on the
supplied exact checkpoint values; they do not re-integrate every primitive.
"""
from pathlib import Path
import argparse,hashlib,json,os,shutil,subprocess,sys,time
ROOT=Path(__file__).resolve().parent

def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def main():
    pa=argparse.ArgumentParser(description=__doc__);pa.add_argument('--regression',action='store_true');pa.add_argument('--native',action='store_true');a=pa.parse_args()
    start=time.time();records=[]
    manifest=json.loads((ROOT/'MANIFEST.json').read_text())
    for row in manifest['files']:
        p=ROOT/row['path'];assert p.is_file() and digest(p)==row['sha256'],row['path']
    print('ARCHIVE HASHES VERIFIED',len(manifest['files']),flush=True)
    for name in ('verify_boundary_sum.py','verify_mixed_divergences.py'):
        subprocess.run([sys.executable,str(ROOT/'engine'/name)],check=True)
        records.append({'check':name,'passed':True})
    if a.regression:
        work=ROOT/'verification/replay_environment';work.mkdir(parents=True,exist_ok=True)
        shutil.copytree(ROOT/'engine',work/'engine',dirs_exist_ok=True)
        if not (work/'boundary').exists():(work/'boundary').symlink_to(ROOT/'boundary',target_is_directory=True)
        for name in ('boundary_control_logjets.json','lower_divergence_prediction.json','vv_singular_control.json'):
            shutil.copy2(ROOT/name,work/name)
        env={**os.environ,'R6_NATIVE':str(int(a.native)),'R6_LINEAR':str(int(a.native)),'R6_MOD':str(int(a.native)),'R6_ACCEL':'1','R6_SPLIT':'1','R6_SAVE_NEGATIVE':'0','OPENBLAS_NUM_THREADS':'1'}
        commands=[['moving_terminal.py'],['negative_moments.py','--test'],['exact_acceleration.py'],['replay_boundary_controls.py'],['derive_divergence_controls.py'],['derive_vv_singular_control.py']]
        if a.native:commands += [[n] for n in ('native_poly.py','native_linear.py','native_mod.py')]
        for command in commands:
            print('REGRESSION',*command,flush=True)
            subprocess.run([sys.executable,str(work/'engine'/command[0]),*command[1:]],env=env,check=True,cwd=work/'engine')
            records.append({'check':' '.join(command),'passed':True})
    report={'status':'all_requested_checks_passed','checks':records,'seconds':time.time()-start,'raw_integrals_reintegrated':False,'scope':'Exact checkpoint coverage and assembly; optional elementary and complete-control re-evaluations. Use replay_integrals.py for new integral blocks.'}
    (ROOT/'verification/replay_summary.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
