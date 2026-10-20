from full_boundary import *
import subprocess
for f in [1,2]:
 sources_boundary(4,f,'v')
 tag=f'B4_v_f{f}'
 meta=json.loads((ROOT/tag/'manifest.json').read_text())
 for rec in meta['blocks']:
  subprocess.run([sys.executable,'-u',str(ROOT/'engine/full_boundary.py'),'--tag',tag,'--block',rec['block']],check=True)
