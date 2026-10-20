"""Local task/concurrency/signal drills. These are not actual Slurm tests."""
from pathlib import Path
import hashlib,os,signal,subprocess,sys
from lri_coeff.storage import read_envelope
ROOT=Path(__file__).resolve().parents[1]

def env():
    e={k:v for k,v in os.environ.items() if not k.startswith('LRI_COEFF_') or k=='LRI_COEFF_NATIVE_CACHE'}
    return dict(e,PYTHONPATH=str(ROOT/'src'),OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMBA_NUM_THREADS='4',OMP_NUM_THREADS='4')

def test_two_tasks(tmp_path):
    manifest=tmp_path/'campaign.json';out=tmp_path/'runs'
    p=subprocess.run([sys.executable,str(ROOT/'scripts/make_campaign.py'),'--cutoffs','4','--schemes','raw','consistent','--threads','1','--output-root',str(out),'--manifest',str(manifest)],env=env(),text=True,capture_output=True)
    assert p.returncode==0,p.stderr
    children=[subprocess.Popen([sys.executable,str(ROOT/'scripts/run_task.py'),'--manifest',str(manifest),'--index',str(i)],env=env(),text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE) for i in range(2)]
    for p in children:
        stdout,stderr=p.communicate(timeout=60);assert p.returncode==0,(stdout,stderr)
    rows=[read_envelope(p)['result'] for p in (out/'d8').glob('*.json')]
    assert {r['scheme'] for r in rows}=={'consistent','raw'}
    assert abs(rows[0]['C'][8]-rows[1]['C'][8])>.1


def test_real_signal(tmp_path):
    output=tmp_path/'point.json'
    cmd=[sys.executable,'-u','-m','lri_coeff','run','--cutoff','16','--threads','1','--output',str(output),'--checkpoint',str(tmp_path/'checkpoint')]
    p=subprocess.Popen(cmd,env=env(),text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    lines=[]
    while True:
        line=p.stdout.readline();lines.append(line)
        if 'wave order' in line:
            p.send_signal(signal.SIGUSR1);break
        if not line:raise AssertionError('Process ended before signal boundary: '+p.stderr.read())
    stdout,stderr=p.communicate(timeout=60)
    assert p.returncode==75,(lines,stdout,stderr)
    assert not output.exists();assert not Path(str(output)+'.lock').exists()
    p=subprocess.run(cmd+['--resume','--threads','2'],env=env(),text=True,capture_output=True,timeout=60)
    assert p.returncode==0,p.stderr
    a=read_envelope(output);assert a['execution']['resumed'];assert a['result']['tuning_residual']<1e-7


def test_cluster_task_settings(tmp_path):
    """Allocation threads, manifest hash check, shared graph cache, checkpoint interval, no manifest rewrite."""
    manifest=tmp_path/'campaign.json';out=tmp_path/'runs'
    make=[sys.executable,str(ROOT/'scripts/make_campaign.py'),'--cutoffs','4','--schemes','consistent','--threads','1','--output-root',str(out),'--manifest',str(manifest)]
    p=subprocess.run(make+['--cache-mode','shared','--checkpoint-seconds','60'],env=env(),text=True,capture_output=True);assert p.returncode==0,p.stderr
    task=read_envelope(manifest)['tasks'][0];assert task['cache']==str(out/'graph_cache') and task['checkpoint_seconds']==60
    run=[sys.executable,str(ROOT/'scripts/run_task.py'),'--manifest',str(manifest),'--index','0']
    bad=subprocess.run(run,env=dict(env(),LRI_COEFF_MANIFEST_SHA256='0'*64),text=True,capture_output=True)
    assert bad.returncode!=0 and 'changed after submission' in bad.stderr and not Path(task['output']).exists()
    ok=subprocess.run(run,env=dict(env(),LRI_COEFF_MANIFEST_SHA256=hashlib.sha256(manifest.read_bytes()).hexdigest(),LRI_COEFF_THREADS='2'),text=True,capture_output=True,timeout=120)
    assert ok.returncode==0,ok.stderr;assert 'threads=2' in ok.stdout
    assert read_envelope(task['output'])['execution']['threads']==2 and any((out/'graph_cache').iterdir())
    p=subprocess.run(make+['--checkpoint-seconds','120'],env=env(),text=True,capture_output=True);assert p.returncode!=0 and 'different content' in p.stderr
    p=subprocess.run(make+['--cache-mode','shared','--checkpoint-seconds','60'],env=env(),text=True,capture_output=True);assert p.returncode==0,p.stderr


def test_supervised_checkpoint_resume(tmp_path):
    """Cluster task path: node-local checkpoints published as one archive, restored by a later job elsewhere."""
    manifest=tmp_path/'campaign.json';out=tmp_path/'runs'
    p=subprocess.run([sys.executable,str(ROOT/'scripts/make_campaign.py'),'--cutoffs','16','--schemes','consistent','--threads','1','--checkpoint-seconds','1000',
                      '--output-root',str(out),'--manifest',str(manifest)],env=env(),text=True,capture_output=True);assert p.returncode==0,p.stderr
    task=read_envelope(manifest)['tasks'][0];archive=Path(task['checkpoint'])/f"task-{task['task_digest'][:16]}.tar"
    run=[sys.executable,'-u',str(ROOT/'scripts/run_task.py'),'--manifest',str(manifest),'--index','0']
    p=subprocess.Popen(run,env=dict(env(),LRI_COEFF_LOCAL_CHECKPOINT=str(tmp_path/'node1')),text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    lines=[]
    while True:
        line=p.stdout.readline();lines.append(line)
        if 'wave order' in line:
            p.send_signal(signal.SIGUSR1);break
        if not line:raise AssertionError('Process ended before signal boundary: '+p.stderr.read())
    stdout,stderr=p.communicate(timeout=120)
    assert p.returncode==75,(lines,stdout,stderr);assert archive.is_file() and not Path(task['output']).exists()
    assert not Path(task['output']+'.lock').exists() and not any(Path(task['checkpoint']).glob('*/latest.json'))
    q=subprocess.run(run,env=dict(env(),LRI_COEFF_LOCAL_CHECKPOINT=str(tmp_path/'node2'),LRI_COEFF_THREADS='2'),text=True,capture_output=True,timeout=120)
    assert q.returncode==0 and 'restored' in q.stdout,(q.stdout,q.stderr)
    a=read_envelope(task['output']);assert a['execution']['resumed'] and a['execution']['threads']==2;assert not archive.exists()
