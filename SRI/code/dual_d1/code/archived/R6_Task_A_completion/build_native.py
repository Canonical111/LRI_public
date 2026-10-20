"""Build optional exact-GMP accelerators; mathematical fallbacks are retained."""
from pathlib import Path
import shutil,subprocess,sys
ROOT=Path(__file__).resolve().parent
compiler=shutil.which('g++')
if not compiler:raise SystemExit('g++ is unavailable. The default quick verifier does not need it; integral replay can use R6_NATIVE=0, R6_LINEAR=0, R6_MOD=0.')
for name in ('poly_multiply','poly_divide','poly_mod'):
    command=[compiler,'-O3','-std=c++17','-shared','-fPIC',str(ROOT/'engine'/f'{name}.cpp'),'-lgmpxx','-lgmp','-o',str(ROOT/'engine'/f'{name}.so')]
    print('Building',name,flush=True);subprocess.run(command,check=True)
print('Optional native exact arithmetic is ready.')
