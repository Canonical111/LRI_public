import os,sys,json,signal,subprocess
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'code'))
from ht2d import hpc


def options(tmp):
 return ['--L','4','--x','.3','--nz','12','--osc','96','--diagnostics','first','--threads','1','--output',str(tmp/'point.json')]


def env():
 return {**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1','NUMBA_NUM_THREADS':'4'}


def cli(argv,ok=0):
 p=subprocess.run([sys.executable,str(ROOT/'code/hpc_run.py'),*argv],env=env(),capture_output=True,text=True)
 assert p.returncode==ok,(p.returncode,p.stdout,p.stderr)
 return p


def test_claim_is_exclusive_and_fail_closed(tmp_path):
 out=tmp_path/'p.json'
 with hpc.claim(out,'abc'):
  assert Path(str(out)+'.claim/owner.json').exists()
  with pytest.raises(hpc.Claimed):
   with hpc.claim(out,'abc'):pass
 assert not Path(str(out)+'.claim').exists()
 Path(str(out)+'.claim').mkdir()
 with pytest.raises(hpc.Claimed):
  with hpc.claim(out,'abc'):pass


def test_full_cli_publication_restart_and_corruption(tmp_path):
 a=options(tmp_path);cli(a)
 file=tmp_path/'point.json';d=json.loads(file.read_text());hpc.validate_record(d,d['request_digest'])
 assert d['accepted'] and len(d['diagnostics']['records'])==3
 old=file.read_bytes();p=cli(a+['--resume']);assert 'REUSE' in p.stdout;assert file.read_bytes()==old
 cli(a+['--check-only'])
 d['Delta_thermal']+=.01;file.write_text(json.dumps(d))
 p=subprocess.run([sys.executable,str(ROOT/'code/hpc_run.py'),*a,'--resume'],env=env(),capture_output=True)
 assert p.returncode!=0
 assert json.loads(file.read_text())['Delta_thermal']==d['Delta_thermal']


def test_interrupted_newton_restart_real_solve(tmp_path,monkeypatch):
 # Register test signal callbacks without modifying pytest's real signal handlers.
 handlers={};monkeypatch.setattr(signal,'signal',lambda sig,f:handlers.setdefault(sig,f))
 from ht2d.solver import DressedSolver
 original=DressedSolver.solve
 def interrupted(self,*args,**kw):
  cp=self.checkpoint
  def stop(theta,history):
   handlers[signal.SIGUSR1](signal.SIGUSR1,None)
   cp(theta,history)
  self.checkpoint=stop
  return original(self,*args,**kw)
 monkeypatch.setattr(DressedSolver,'solve',interrupted)
 a=hpc.parser().parse_args(options(tmp_path))
 assert hpc.main(options(tmp_path))==75
 assert not (tmp_path/'point.json').exists()
 assert (tmp_path/'point.json.checkpoint.json').exists()
 assert not (tmp_path/'point.json.claim').exists()
 monkeypatch.setattr(DressedSolver,'solve',original)
 assert hpc.main(options(tmp_path)+['--resume'])==0
 d=json.loads((tmp_path/'point.json').read_text());assert d['tuning_residual']<1e-10


def test_frozen_manifest_and_two_process_reuse(tmp_path):
 argv=options(tmp_path)
 request=tmp_path/'requests.json';request.write_text(json.dumps([argv]))
 manifest=tmp_path/'manifest.json'
 subprocess.run([sys.executable,str(ROOT/'cluster/make_manifest.py'),'--request-list',str(request),'--output',str(manifest)],check=True,env=env(),capture_output=True)
 for _ in range(2):
  subprocess.run([sys.executable,str(ROOT/'cluster/run_item.py'),'--manifest',str(manifest),'--index','0'],check=True,env=env(),capture_output=True)
 m=json.loads(manifest.read_text());m['items'][0]['argv'][3]='.35';manifest.write_text(json.dumps(m))
 p=subprocess.run([sys.executable,str(ROOT/'cluster/run_item.py'),'--manifest',str(manifest),'--index','0'],env=env(),capture_output=True)
 assert p.returncode!=0


def test_basis_training_and_transfer_cli(tmp_path):
 teacher=tmp_path/'teacher.json'
 a=['--L','4','--x','.3','--nz','16','--osc','128','--diagnostics','none','--train-keep','12','--output',str(teacher)]
 cli(a);d=json.loads(teacher.read_text());assert not d['basis_artifact']['metadata']['thermal_target']
 out=tmp_path/'target.json'
 a=['--L','6','--x','.3','--nz','12','--basis',str(teacher),'--diagnostics','all','--output',str(out),'--backend','gram']
 cli(a);t=json.loads(out.read_text());assert len(t['diagnostics']['records'])==9
 cli(a+['--resume'])
 d['basis_artifact']['scale']*=1.001;teacher.write_text(json.dumps(d))
 p=subprocess.run([sys.executable,str(ROOT/'code/hpc_run.py'),*a,'--resume'],env=env(),capture_output=True)
 assert p.returncode!=0


def test_incompatible_basis_mode_rejected(tmp_path):
 a=hpc.parser().parse_args(options(tmp_path)+['--basis',str(tmp_path/'missing.json'),'--window','none'])
 with pytest.raises(ValueError):hpc.run(a)


def test_manifest_resolves_equals_path_and_checks_index(tmp_path):
 teacher=ROOT/'reference/results/teacher_L6_x0.300.json'
 out=tmp_path/'o.json';manifest=tmp_path/'manifest.json'
 request=tmp_path/'requests.json'
 request.write_text(json.dumps([['--L','6','--x','.3','--basis='+str(teacher),'--output='+str(out)]]))
 subprocess.run([sys.executable,str(ROOT/'cluster/make_manifest.py'),'--request-list',str(request),'--output',str(manifest)],check=True,env=env(),capture_output=True)
 d=json.loads(manifest.read_text());argv=d['items'][0]['argv']
 assert argv[argv.index('--output')+1]==str(out.resolve())
 assert argv[argv.index('--basis')+1]==str(teacher.resolve())
 p=subprocess.run([sys.executable,str(ROOT/'cluster/run_item.py'),'--manifest',str(manifest),'--index','-1'],env=env(),capture_output=True)
 assert p.returncode!=0


def test_driver_rechecks_frozen_source_and_input_bytes(tmp_path,monkeypatch):
 argv=options(tmp_path)
 monkeypatch.setenv('HT2D_FROZEN_SOURCE','bad')
 with pytest.raises(ValueError,match='Source changed'):hpc.run(hpc.parser().parse_args(argv))
 monkeypatch.setenv('HT2D_FROZEN_SOURCE',hpc.source_hash())
 seed=tmp_path/'seed.json';seed.write_text(json.dumps({'theta':[-.01,-3.]}))
 monkeypatch.setenv('HT2D_FROZEN_INPUTS',json.dumps({str(seed.resolve()):'bad'}))
 with pytest.raises(ValueError,match='Inputs changed'):hpc.run(hpc.parser().parse_args(argv+['--seed',str(seed)]))
