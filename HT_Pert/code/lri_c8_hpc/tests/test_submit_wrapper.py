"""slurm/submit_defq.sh against shimmed squeue/sbatch/sacct (C8_LOCAL_TEST=1 keeps the real
Slurm binaries off PATH, so nothing is ever submitted)."""
import json,os,subprocess,sys
from pathlib import Path
import pytest
from lri_c8 import io
ROOT=Path(__file__).resolve().parents[1]
pytestmark=pytest.mark.skipif(sys.platform=='win32',reason='bash wrapper')

@pytest.fixture
def rig(tmp_path):
    tmp_path=tmp_path.resolve();bindir=tmp_path/'bin';bindir.mkdir()
    (bindir/'squeue').write_text('#!/bin/bash\n[[ -n ${SHIM_SQUEUE_FAIL:-} ]] && exit 1\n[[ -f ${SHIM_SQUEUE_OUT:-/nonexistent} ]] && cat "$SHIM_SQUEUE_OUT"\nexit 0\n')
    (bindir/'sbatch').write_text('#!/bin/bash\nprintf "%s\\n" "$@" > "$SHIM_LOG.args"\nenv > "$SHIM_LOG.env"\necho 4242\n')
    (bindir/'sacct').write_text('#!/bin/bash\nexit 1\n')
    for f in bindir.iterdir():f.chmod(0o755)
    env={k:v for k,v in os.environ.items() if not k.startswith(('SLURM_','SBATCH_','SQUEUE_'))}
    env.update(PATH=f'{bindir}{os.pathsep}{Path(sys.executable).parent}{os.pathsep}{os.environ["PATH"]}',
               C8_LOCAL_TEST='1',C8_TEST_OUTPUT_PREFIX=str(tmp_path)+'/',C8_DATA=str(tmp_path/'data'),
               SHIM_LOG=str(tmp_path/'sbatch'),USER='tester',PYTHONPATH=str(ROOT/'src'),NUMBA_THREADING_LAYER='tbb')
    io.atomic_save(tmp_path/'r.json',{'status':'pass','source_sha256':io.source_digest()})
    subprocess.run([sys.executable,str(ROOT/'scripts/make_campaign.py'),'--cutoffs','4','6','--threads','1',
                    '--memory-limit-gib','2','--receipt',str(tmp_path/'r.json'),'--output',str(tmp_path/'c.json'),
                    '--allow-local-receipt'],env=env,check=True,capture_output=True)
    def submit(*extra,**over):
        r=subprocess.run(['bash',str(ROOT/'slurm/submit_defq.sh'),'lanes',str(tmp_path/'c.json'),str(tmp_path/'out'),*extra],
                         env={**env,**over},capture_output=True,text=True)
        args=(tmp_path/'sbatch.args').read_text().split('\n') if (tmp_path/'sbatch.args').exists() else None
        senv=dict(l.split('=',1) for l in (tmp_path/'sbatch.env').read_text().splitlines() if '=' in l) if args else None
        for f in ('sbatch.args','sbatch.env'):(tmp_path/f).unlink(missing_ok=True)
        return r,args,senv
    return tmp_path,submit

def test_hostile_environment_cannot_change_the_submission(rig):
    tmp,submit=rig
    r,args,senv=submit('--time=01:00:00',SBATCH_MEM_PER_NODE='8G',SBATCH_REQUEUE='1',SBATCH_SIGNAL='B:USR1@60',
                       SBATCH_PARTITION='debugq',SBATCH_ARRAY_INX='0',SQUEUE_STATES='RUNNING',
                       CAMPAIGN='/wrong/campaign.json',C8_OUTPUT='/wrong/out')
    assert r.returncode==0,r.stderr
    assert not [k for k in senv if k.startswith(('SBATCH_','SQUEUE_'))]
    for a in ('--nodes=1','--ntasks=1','--exclusive','--mem=180G','--no-requeue','--signal=B:USR1@1800','--export=ALL',
              '--array=0,1%8','--time=01:00:00'):assert a in args,(a,args)
    assert senv['CAMPAIGN']==str(tmp/'c.json') and senv['C8_OUTPUT']==str(tmp/'out')
    assert (tmp/'out'/'submissions.txt').read_text().split()[0]=='4242'

@pytest.mark.parametrize('bad',['--arr=0','-t','-J','--export=NONE','--mem=8G','--array=0','positional'])
def test_disallowed_sbatch_arguments(rig,bad):
    tmp,submit=rig
    r,args,_=submit(bad);assert r.returncode==2 and args is None and 'not allowed' in r.stderr

def test_queue_failure_and_live_jobs_refuse(rig):
    tmp,submit=rig
    r,args,_=submit(SHIM_SQUEUE_FAIL='1');assert r.returncode==2 and args is None and 'squeue failed' in r.stderr
    assert submit()[0].returncode==0  # records job 4242
    (tmp/'sq').write_text('4242 renamed-job SUSPENDED\n')
    r,args,_=submit(SHIM_SQUEUE_OUT=str(tmp/'sq'));assert r.returncode==2 and args is None and 'SUSPENDED' in r.stderr
