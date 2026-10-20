"""Compare fixed-spin residue sums with the independent real spectral kernel.
This test respects the inner (n) summation order of the Kappa formula.
Finite truncation differences are diagnostics, not interval error bounds.
"""
from pathlib import Path
import json
import numpy as np
from hypergeometric_series import series_terms
from wheel_spectrum import terms, kterms


def main() -> None:
    rows = []
    for d in (1, 2, 3):
        spins = np.array([0, 1]) if d == 1 else np.array([0, 1, 3, 7])
        spectral = np.vstack([terms(d, spins, 768)[:4], kterms(d, spins, 768)])
        for n_terms in (256, 1024, 4096):
            partial = series_terms(d, spins, np.arange(n_terms)).sum(axis=2)
            rows.append({
                'd': d, 'spins': spins.tolist(), 'n_terms': n_terms,
                'labels': ['W3', 'P4', 'L', 'Z', 'K_integral_part'],
                'partial_sums': partial.tolist(),
                'spectral_fixed_spin_values': spectral.tolist(),
                'partial_minus_spectral': (partial-spectral).tolist(),
            })
    result = {
        'scope': 'fixed-spin inner residue-series checks; no angular tail approximation or interval bounds',
        'K_summation_order': 'n sum before spin sum; two residue families paired',
        'rows': rows,
    }
    Path(__file__).with_suffix('.json').write_text(json.dumps(result, indent=2))
    print('Saved fixed-spin series diagnostics; no accuracy certification is inferred.')


if __name__ == '__main__':
    main()
