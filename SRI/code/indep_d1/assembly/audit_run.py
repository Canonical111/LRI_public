#!/usr/bin/env python3
"""Run a Python script under an audit hook that aborts (exit 97/98) on any open or listing of an archive path.
usage: AUDIT_LOG=<file> python3 audit_run.py SCRIPT [ARGS...]
Every opened path is logged to $AUDIT_LOG.  Used for the archive-free steps of the C8 assembly (2026-10-07); the
project copy it runs in has no sealed directory either (slurm/rsync_exclude_C8ABC.txt)."""
import os
import runpy
import sys

FORBID = ['LRI_SRI_research_compendium', 'spec/comparison', 'archive_comparison', 'archive_C8_values', 'compare_brief',
          'records_100', 'F3_final_100', 'derive_invariants', 'compare_archive', 'RESULTS_C8_archive', 'RESULTS_archive']
opened = []


def hook(ev, args):
    if ev == 'open':
        p = args[0]
        if isinstance(p, (str, bytes, os.PathLike)):
            p = os.fsdecode(p)
            opened.append((p, args[1] if len(args) > 1 else None))
            for f in FORBID:
                if f in p:
                    sys.stderr.write(f'FORBIDDEN OPEN: {p}\n')
                    sys.stderr.flush()
                    os._exit(97)
    elif ev in ('os.listdir', 'os.scandir', 'glob.glob'):
        p = os.fsdecode(args[0]) if args and args[0] is not None else ''
        for f in FORBID:
            if f in p:
                sys.stderr.write(f'FORBIDDEN LIST: {p}\n')
                os._exit(98)


sys.addaudithook(hook)
script = os.path.abspath(sys.argv[1])
sys.argv = sys.argv[1:]
sys.path[0] = os.path.dirname(script)
try:
    runpy.run_path(script, run_name='__main__')
finally:
    with open(os.environ['AUDIT_LOG'], 'w') as fh:
        for p, m in opened:
            fh.write(f'{m}\t{p}\n')
