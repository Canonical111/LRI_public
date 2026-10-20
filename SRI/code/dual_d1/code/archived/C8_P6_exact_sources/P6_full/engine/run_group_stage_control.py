from pathlib import Path
import subprocess,sys,time
ROOT=Path(__file__).resolve().parent.parent
while int(Path('/sys/fs/cgroup/memory.current').read_text())>2600000000:time.sleep(2)
with (ROOT/'logs/group_before_fibration_check.log').open('w') as f:subprocess.run([sys.executable,str(ROOT/'engine/group_before_fibration.py'),'check','0'],stdout=f,stderr=subprocess.STDOUT,check=True)
print('CONTROL_FINISHED',flush=True)
