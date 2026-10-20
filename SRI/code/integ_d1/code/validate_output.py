"""Validate one engine output (fix rounds 1-2): strict completeness (cluster_assemble.read_out) and, if given, the
fingerprint in the header: input hash, engine build id, the exact argument string (without -o) and the sector range.
usage: python validate_output.py OUT [INPUT_SHA256 BUILD_ID ARGS...]   exit 0 = valid"""
import sys, os, shlex
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cluster_assemble import read_out, OutputError
try:
    hdr, secs = read_out(sys.argv[1])
    fp = hdr.get('fingerprint')
    if len(sys.argv) > 2:
        if fp is None:
            raise OutputError('no fingerprint in the output header')
        if fp.get('input_sha256') != sys.argv[2]:
            raise OutputError('input hash in the output header differs from the expected one')
        if len(sys.argv) > 3 and fp.get('build') != sys.argv[3]:
            raise OutputError(f'engine build {fp.get("build")} differs from the expected {sys.argv[3]}')
        if len(sys.argv) > 4:
            got = shlex.split(hdr.get('args') or '')
            if '-o' in got:
                i = got.index('-o'); del got[i:i + 2]
            want = sys.argv[4:]
            if got != want:
                raise OutputError(f'argument list in the output header {got} differs from the requested {want}')
            if '-sec' in want:
                i = want.index('-sec'); s0, s1 = int(want[i + 1]), int(want[i + 2])
            else:
                s0, s1 = 0, int(fp['nsec_input'])
            if (int(fp['sec0']), int(fp['sec1'])) != (s0, s1):
                raise OutputError('sector range in the header differs from the requested one')
        if set(range(int(fp['sec0']), int(fp['sec1']))) != set(secs):
            raise OutputError('sector set differs from the header range')
except (OutputError, OSError, KeyError, ValueError) as e:
    print('INVALID', e); sys.exit(1)
print('valid', len(secs), 'sectors')
