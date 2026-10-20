"""Reassemble the complete C7 estimate from the delivered raw data.
No expensive integration is run. Python 3.10+ and NumPy are sufficient.
"""
from pathlib import Path
import hashlib,json,subprocess,sys
W=Path(__file__).resolve().parents[1]
def main()->None:
    manifest=W/'verification/production_audit.json'
    if not manifest.is_file():
        raise FileNotFoundError('Extract the entire archive before running this script.')
    data=json.loads(manifest.read_text())
    for row in data['streams']:
        p=W/row['file']
        if not p.is_file():raise FileNotFoundError(f'Missing production data: {p}')
        if hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256']:
            raise ValueError(f'Production data checksum mismatch: {p}')
    expected=json.loads((W/'verification/C7_assembled_result.json').read_text())
    subprocess.run([sys.executable,str(W/'code/final_analysis.py')],check=True)
    actual=json.loads((W/'verification/C7_assembled_result.json').read_text())
    for key in ['C7_full','sampling_se','empirical_allowance']:
        tolerance=1e-7 if key!='empirical_allowance' else 0
        if abs(actual[key]-expected[key])>tolerance:
            raise ArithmeticError(f'Reassembly differs for {key}: {actual[key]} vs {expected[key]}')
    print('All production checksums and final mean/error reassembly checks passed.')
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,ArithmeticError,subprocess.CalledProcessError) as exc:
        print(f'Reproduction failed: {exc}',file=sys.stderr);sys.exit(1)
