#!/usr/bin/env python3
"""Extract data/dens_v1_series.json (Delta_eps(N) and fit summary per Ds) from the shipped analysis output.
Usage: python3 tools/extract_series_d1.py <path to HT/code/lri_dressed_phi4_hpc_analysis/dens_v1_extrapolation.json>"""
import json, sys
X = json.load(open(sys.argv[1]))
out = [{'delta': x['delta'], 'cuts': x['cuts'], 'values': x['values'], 'D_inf': (x['fit'] or {}).get('D_inf'),
        'spread_half': (x['fit'] or {}).get('spread_half'), 'stable': x['stable']} for x in X]
json.dump({'about': 'Delta_eps(N) of dens_v1 (d = 1, consistent window, 16 density states) and the fit summary; extracted from '
           'HT/code/lri_dressed_phi4_hpc_analysis/dens_v1_extrapolation.json by tools/extract_series_d1.py', 'series': out},
          open('data/dens_v1_series.json', 'w'), indent=1)
