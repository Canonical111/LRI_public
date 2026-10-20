#!/usr/bin/env python3
"""Print the path prefix under which the 2D or 3D analysis records name their histogram indices, for --index-remap OLD=NEW.

The production records store the absolute index path of the machine they were written on; the evaluators verify the index by its SHA-256
and read it from the released layout through --index-remap. Reading OLD from the records keeps paths and user names out of the Makefile
and works whether the released records are byte-identical or path-scrubbed.

Usage: index_prefix.py DIM     (run from MC/; DIM = 2 or 3)
"""
import glob, json, os, sys

dim = sys.argv[1]
pattern = 'data/2d/prod/analysis_b2000_s*/results.json' if dim == '2' else 'data/3d/prod/analysis_*_b2000_s*/results.json'
files = sorted(glob.glob(pattern))
if not files: sys.exit(f'index_prefix.py: no records match {pattern} (run from MC/)')
prefixes = {os.path.dirname(os.path.dirname(json.load(open(f))['index_path'])) + '/' for f in files}
if len(prefixes) != 1: sys.exit(f'index_prefix.py: records name {len(prefixes)} different index prefixes: {sorted(prefixes)}')
print(prefixes.pop())
