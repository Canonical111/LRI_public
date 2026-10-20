"""Gate for production: is there a passing cluster validation for THIS solver and software stack?
It does not trust any stored verdict. For each <data>/validation/<job>/ it RECOMPUTES the comparison of the four
records (dconn L=40,42,44 and raw L=44, degree 8) against the archived records, at the fixed tolerance
compare_archive.RTOL with exact counts; the archived records are pinned by their sha256 in the baseline zip. Each
validation record's provenance must carry the given solver sha256 and this interpreter's Python/NumPy/SciPy.
Prints the validating job directory; exit 0 only if one exists."""
from pathlib import Path
import argparse, hashlib, json, platform, sys
import numpy, scipy
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'code'))
from compare_archive import compare, RTOL
PINNED={'dconn_L40_d8.json':'3dfec3672335a76df15e195c08fd59825e36113e8bfb36d42f2309de84616d5c',
        'dconn_L42_d8.json':'74f56a8b734f3fa8756f2467e05e2fda738497a8a16b91968e3f68fa346b29d6',
        'dconn_L44_d8.json':'5716c15e11f89675d5a68aac8a6ec34c07a5b3b379b6af14109421627d60048e',
        'raw_L44_d8.json':'bd66be83c0653caf9069d9976e3ccee3fdf9445594aec43ea9026193e6adc369'}
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data',type=Path,required=True)
p.add_argument('--solver-sha',required=True,help='sha256 of the solver file production will run');a=p.parse_args()
archive={}
for f,h in PINNED.items():
    b=(ROOT/'results/new_coefficients'/f).read_bytes()
    if hashlib.sha256(b).hexdigest()!=h:sys.exit(f'archived record {f} does not match its pinned sha256')
    archive[f]=json.loads(b)
stack=(platform.python_version(),numpy.__version__,scipy.__version__);reasons=[]
for d in sorted((a.data/'validation').glob('*'),reverse=True):
    try:
        bad=[]
        for f,old in archive.items():
            new=json.loads((d/f).read_text());pv=new['provenance']
            if pv['code_sha256']!=a.solver_sha:bad.append(f'{f}: solver {pv["code_sha256"][:12]}')
            if (pv['python'],pv['numpy'],pv['scipy'])!=stack:bad.append(f'{f}: stack {pv["python"]},{pv["numpy"]},{pv["scipy"]}')
            passed,worst=compare(new,old,RTOL)
            if not passed:bad.append(f'{f}: differs {max(worst.values()):.1e}')
        if bad:reasons.append(f'{d.name}: '+'; '.join(bad));continue
        print(d);sys.exit(0)
    except (OSError,ValueError,KeyError) as e:reasons.append(f'{d.name}: {e!r}')
print('no passing validation for solver',a.solver_sha[:12],'and stack',stack,file=sys.stderr)
for r in reasons[:10]:print('  ',r,file=sys.stderr)
sys.exit(1)
