#!/usr/bin/env python3
"""pp_tokens.py NEW OLD OUT.json: the preprocessed translation units of src/c8d2_integrate.cpp (g++ -E -P with the
Makefile's flags; default, -DC8_USE_GMP, and -DC8_ORDER_TRACE as a sanity control), 601b102 vs ffbc8af. The sources
differ in comments, one line break and the #ifdef C8_ORDER_TRACE blocks, and -P keeps some line breaks, so the byte
streams differ where the programs do not. The units count as the same program when (1) they are equal with every
whitespace character removed, and (2) every place where their whitespace-split words differ is whitespace inserted or
removed right next to one of ; { } ( ) , (single-character punctuators that never join a neighbour into another
token), so the C++ token sequences are identical. With -DC8_ORDER_TRACE (1) must fail (sanity)."""
import difflib, hashlib, json, re, subprocess, sys
from pathlib import Path
NEW, OLD, OUT = map(Path, sys.argv[1:4])
FLAGS = ['-O3', '-std=c++17', '-fopenmp', '-ffp-contract=off', '-fno-fast-math']
SAFE = set(';{}(),')
res = {}
for name, defs in (('decimal', []), ('gmp', ['-DC8_USE_GMP']), ('order_trace', ['-DC8_ORDER_TRACE'])):
    txt = {}
    for tag, root in (('new', NEW), ('old', OLD)):
        txt[tag] = subprocess.run(['g++', '-E', '-P', *FLAGS, *defs, str(root / 'src/c8d2_integrate.cpp')], capture_output=True, cwd=root, check=True).stdout.decode()
    nows = {k: re.sub(r'\s+', '', v) for k, v in txt.items()}
    same_nows = nows['new'] == nows['old']
    a, b = txt['old'].split(), txt['new'].split()
    p = 0  # common prefix and suffix first: the differences are local, and difflib is quadratic on 6e5 words
    while p < min(len(a), len(b)) and a[p] == b[p]:
        p += 1
    q = 0
    while q < min(len(a), len(b)) - p and a[-1 - q] == b[-1 - q]:
        q += 1
    a, b = a[p:len(a) - q], b[p:len(b) - q]
    diffs, safe = [], True
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op == 'equal':
            continue
        A, Bw = a[i1:i2], b[j1:j2]
        ok = ''.join(A) == ''.join(Bw)
        if ok:  # every word boundary that exists on one side only must touch a safe punctuator
            def cuts(ws):
                out, n = set(), 0
                for w in ws[:-1]:
                    n += len(w); out.add(n)
                return out
            s = ''.join(A)
            for c in cuts(A) ^ cuts(Bw):
                if not (s[c - 1] in SAFE or s[c] in SAFE):
                    ok = False
        safe &= ok
        diffs.append(dict(op=op, at_word=p + i1, old=A[:12], new=Bw[:12], whitespace_only_next_to_punctuator=ok))
    res[name] = dict(bytes_new=len(txt['new']), bytes_old=len(txt['old']), equal_without_whitespace=same_nows,
                     sha256_no_whitespace_new=hashlib.sha256(nows['new'].encode()).hexdigest(), word_differences=diffs[:10],
                     n_word_differences=len(diffs), same_tokens=same_nows and safe)
res['passed'] = res['decimal']['same_tokens'] and res['gmp']['same_tokens'] and not res['order_trace']['equal_without_whitespace']
res['gxx'] = subprocess.run(['g++', '--version'], capture_output=True, text=True).stdout.splitlines()[0]
OUT.write_text(json.dumps(res, indent=1) + '\n'); print(json.dumps(res, indent=1)[:4000]); sys.exit(0 if res['passed'] else 1)
