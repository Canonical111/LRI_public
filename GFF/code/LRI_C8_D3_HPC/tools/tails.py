"""Class-B merge of the native rows (PLAN.md C.3): the per-group files graph_tails.csv and graph_promotions.csv.

The worker writes per row (one task: a point range [begin, end) of one (replicate, graph)) the tail fields of
t = v_0*jac, the weight-free base integrand: tail_top (the TAILK = 16 largest |t| of the row, descending), tail_sum
(the long-double sum of |t| in point order) and tail_argmax (the global point index of the first largest |t|); and the
counters quad, mp, nondirect, nonmoderate, plus mp_checked, mp_hist (18 bins), mp_min_log10 and mp_alarm under
--mp-check on or stride16. Merging the rows of one (replicate, graph):
  * points    = sum of (end - begin);
  * tail_sum  = the exact Decimal sum of the rows' tail_sum strings (no rounding: an Inexact signal is an error);
  * tail_top  = the 16 largest values of the union of the rows' tail_top lists, descending, as the worker printed them;
  * tail_argmax = the argmax index of the union: the row whose tail_top[0] is largest, ties to the smaller point
    index (the worker's own rule: an equal value never displaces an earlier one);
  * the counters are summed; mp_min_log10 is the minimum of the rows' values ("-inf" sorts first; null without checks).
The 16 largest of a union equal the 16 largest of the whole stream, since each row keeps its own 16 largest; so a
chunked graph-replicate merges to the tail fields of one whole task (A-KER-6 (b)).
`production.py merge` writes the two files per group with its own streaming implementation (D.13, the final pass of
`_final_pass`), in the layout below; this module is the independent in-memory merge that the tests compare it with
(A-KER-6 (d): tests/class_b.py against a hand merge on real chunked rows; tests/workflow.py against the published
files of every group, with the fake worker on the Mac and the real worker on Expanse). graph_replicates.csv is
unchanged. The layouts (the ones the statistics tools read):
  graph_tails.csv       replicate,graph,points,tail_sum,tail_argmax,tail_n,tail_top_1..tail_top_16
  graph_promotions.csv  replicate,graph,quad,mp,nondirect,nonmoderate,mp_checked,mp_alarm,mp_min_log10,mp_hist_0..mp_hist_17
(mp_min_log10 is "null" without checked points; tail_n is the number of tail_top values, empty columns padding to 16.)
"""
from __future__ import annotations

import csv
import decimal
import io
from decimal import Decimal as D
from pathlib import Path

TAILK = 16
MPBINS = 18
TAIL_HEADER = ['replicate', 'graph', 'points', 'tail_sum', 'tail_argmax', 'tail_n', *[f'tail_top_{k}' for k in range(1, TAILK + 1)]]
PROMO_HEADER = ['replicate', 'graph', 'quad', 'mp', 'nondirect', 'nonmoderate', 'mp_checked', 'mp_alarm', 'mp_min_log10',
                *[f'mp_hist_{b}' for b in range(MPBINS)]]


def exact_sum(values) -> D:
    ctx = decimal.Context(prec=2000, traps=[decimal.Inexact, decimal.InvalidOperation])
    total = D(0)
    for v in values:
        total = ctx.add(total, D(v))
    return total


def merge_tails(rows) -> dict:
    """{(rep, graph): {points, tail_sum, tail_top, tail_argmax}} of rows carrying the tail fields."""
    out: dict = {}
    for r in rows:
        k = (r['rep'], r['graph'])
        m = out.setdefault(k, {'points': 0, 'sums': [], 'tops': [], 'best': None})
        m['points'] += r['end'] - r['begin']
        m['sums'].append(r['tail_sum'])
        m['tops'] += r['tail_top']
        if r['tail_top']:
            cand = (D(r['tail_top'][0]), r['tail_argmax'])
            b = m['best']
            if b is None or cand[0] > b[0] or (cand[0] == b[0] and cand[1] < b[1]):
                m['best'] = cand
    res = {}
    for k, m in out.items():
        top = sorted(m['tops'], key=D, reverse=True)[:TAILK]
        res[k] = {'points': m['points'], 'tail_sum': exact_sum(m['sums']), 'tail_top': top,
                  'tail_argmax': None if m['best'] is None else m['best'][1]}
    return res


def merge_promotions(rows) -> dict:
    out: dict = {}
    for r in rows:
        k = (r['rep'], r['graph'])
        m = out.setdefault(k, {'points': 0, 'quad': 0, 'mp': 0, 'nondirect': 0, 'nonmoderate': 0, 'mp_checked': 0,
                               'mp_hist': [0] * MPBINS, 'mp_alarm': 0, 'mp_min_log10': None})
        m['points'] += r['end'] - r['begin']
        for f in ('quad', 'mp', 'nondirect', 'nonmoderate'):
            m[f] += r[f]
        if 'mp_checked' in r:
            m['mp_checked'] += r['mp_checked']
            m['mp_alarm'] += r['mp_alarm']
            m['mp_hist'] = [a + b for a, b in zip(m['mp_hist'], r['mp_hist'], strict=True)]
            v = r['mp_min_log10']
            if v is not None and (m['mp_min_log10'] is None or D(str(v)) < D(m['mp_min_log10'])):
                m['mp_min_log10'] = str(D(str(v)))
    return out


def tails_csv(rows) -> str:
    f = io.StringIO()
    w = csv.writer(f, lineterminator='\n')
    w.writerow(TAIL_HEADER)
    for (rep, g), m in sorted(merge_tails(rows).items()):
        top = list(m['tail_top']) + [''] * (TAILK - len(m['tail_top']))
        w.writerow([rep, g, m['points'], str(m['tail_sum']), m['tail_argmax'], len(m['tail_top']), *top])
    return f.getvalue()


def promotions_csv(rows) -> str:
    f = io.StringIO()
    w = csv.writer(f, lineterminator='\n')
    w.writerow(PROMO_HEADER)
    for (rep, g), m in sorted(merge_promotions(rows).items()):
        w.writerow([rep, g, m['quad'], m['mp'], m['nondirect'], m['nonmoderate'], m['mp_checked'], m['mp_alarm'],
                    'null' if m['mp_min_log10'] is None else m['mp_min_log10'], *m['mp_hist']])
    return f.getvalue()


def write(path: Path, text: str) -> None:
    Path(path).write_text(text)
