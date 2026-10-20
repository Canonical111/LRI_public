"""Build exact arithmetic accelerators for optional raw integration replay.
The final acceptance checker does not require native modules or SymPy.
"""
from pathlib import Path
import subprocess,sysconfig,shutil
root=Path(__file__).resolve().parent; eng=root/'engine'
cxx=shutil.which('g++');cc=shutil.which('cc')
if not cxx or not cc:raise SystemExit('Replay requires C and C++17 compilers and GMP development headers.')
for name in ('poly_multiply','poly_divide','poly_mod','poly_fused'):
 cmd=[cxx,'-O3','-std=c++17','-shared','-fPIC',str(eng/(name+'.cpp')),'-lgmpxx','-lgmp','-o',str(eng/(name+'.so'))]
 print('Building',name,flush=True);subprocess.run(cmd,check=True)
ext=sysconfig.get_config_var('EXT_SUFFIX')
cmd=[cc,'-O3','-shared','-fPIC','-I'+sysconfig.get_paths()['include'],str(eng/'fast_fraction.c'),'-lgmp','-o',str(eng/('fast_fraction'+ext))]
print('Building exact GMP rational scalars',flush=True);subprocess.run(cmd,check=True)
