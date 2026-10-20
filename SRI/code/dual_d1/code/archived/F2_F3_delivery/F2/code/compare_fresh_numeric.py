#!/usr/bin/env python3
"""Compare newly replayed full F2 values without importing period tables."""
from pathlib import Path
from decimal import Decimal, localcontext
import json
ROOT = Path(__file__).resolve().parents[2]

def main():
    folder = ROOT / 'F2' / 'verification'
    reference = json.loads((folder/'run110dfs.json').read_text())['values']
    report = {}
    with localcontext() as ctx:
        ctx.prec = 140
        for name in ('replay80', 'replay110'):
            path = folder/f'{name}.json'
            if not path.is_file():
                raise FileNotFoundError(f'Fresh full numerical result is missing: {path}')
            values = json.loads(path.read_text())['values']
            if set(values) != set(reference):
                raise RuntimeError('Full-expression output names differ: '+name)
            differences = {k: abs(Decimal(values[k])-Decimal(v)) for k,v in reference.items()}
            tolerance = Decimal('1e-63') if name=='replay80' else Decimal('1e-90')
            if not all(d < tolerance for d in differences.values()):
                raise ArithmeticError(f'Full-expression comparison failed for {name}: {differences}')
            report[name] = {
                'all_compared': True,
                'max_error': str(max(differences.values())),
                'comparison_threshold': str(tolerance),
                'individual_differences': {k:str(d) for k,d in differences.items()},
            }
    output = ROOT/'verification'/'fresh_numeric_comparison.json'
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return report

if __name__=='__main__':
    main()
