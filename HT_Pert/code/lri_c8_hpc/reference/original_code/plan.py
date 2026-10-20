#!/usr/bin/env python3
"""Exact state counts; this is not an HPC RSS/runtime prediction."""
import argparse,json
from lri_hpc.basis import count_tables
p=argparse.ArgumentParser();p.add_argument('--cutoffs',type=int,nargs='+',default=[40,50,60,80,100,118]);a=p.parse_args()
for L in a.cutoffs:
 if L<2 or L%2:raise ValueError('Even cutoff >=2 required')
 G,Z=count_tables(L,19,16);D=int(Z[19,16,4*L])
 print(json.dumps({'cutoff':L,'basis_dimension_including_auxiliary_parities':D,
  'P_cap':19,'Q_cap':16,'single_float64_vector_GiB':8*D/2**30,
  'warning':'Several dozen vectors plus graph storage are needed; calibrate actual peak RSS.'}))
