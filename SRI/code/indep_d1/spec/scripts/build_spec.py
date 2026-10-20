#!/usr/bin/env python3
"""Assemble the DEFINITIONS-ONLY specification ../spec_definitions.json (and the deprecated
compatibility file ../spec.json) from the ARCHIVE-FREE pieces in ../out/.

This script reads only ../out/*.json produced by the archive-free scripts and the reviewer's
archive-free check outputs in ../review/.  It never reads ../comparison/ or the compendium.
Archive-derived numbers live only in ../comparison/archive_comparison.json (sealed).

Run order (archive-free pipeline, every step < 5 s on the Mac):
  derive_requirements.py -> two_kink_exact.py -> derive_invariants.py -> check_closed_forms.py
  -> sanity_finite_cutoff.py -> validation_targets.py -> build_spec.py -> make_spec_md.py
"""
import copy, hashlib, json
from pathlib import Path

SPEC = Path(__file__).resolve().parent.parent
SPEC_VERSION_DATE = '2026-10-02'   # bump together with meta.version when the definitions change
OUT = SPEC / 'out'
J = lambda n: json.load(open(OUT / n))

defs = J('input_definitions.json')
norm = J('normalized_atoms.json')
req = J('raw_requirements.json')
inv = J('invariants.json')
vt = J('validation_targets.json')
cfc = J('closed_form_consistency.json')
two = J('two_kink_exact.json')
REVIEW = {n: json.load(open(SPEC / 'review' / f'{n}.json'))
          for n in ('algebra_independent', 'old_inputs_from_note') if (SPEC / 'review' / f'{n}.json').exists()}

# ------------------------------------------------------------------ integrand definitions
INS = {  # d_v^a d_delta^b W_n / W_n at (v,delta)=(1,0)
    'base': '1', 'v': '2*S1', 'vv': '4*S1^2', 'vvv': '8*S1^3', 'd': 'S2', 'vd': 'S2 + 2*S1*S2',
    'vvd': '4*S1*S2 + 4*S1^2*S2', 'dd': 'S2^2 + (2/3)*S3', 'vdd': '(2/3)*S3 + 2*S2^2 + (4/3)*S1*S3 + 2*S1*S2^2'}
DV = {'base': (0, 0), 'v': (1, 0), 'vv': (2, 0), 'vvv': (3, 0), 'd': (0, 1), 'vd': (1, 1), 'vvd': (2, 1), 'dd': (0, 2), 'vdd': (1, 2)}
INV = {v: k for k, v in DV.items()}


def split(atom):
    base = atom.split('_')[0]
    kind = base.rstrip('0123456789')
    return kind, int(base[len(kind):])


def pmin_tight(atom):
    kind, n = split(atom); m = n // 2
    if kind in ('A', 'Z', 'EA'):
        return -m
    if kind in ('Q', 'EZ'):
        return -(m - 1)
    return 0 if m == 1 else -(m - 1)          # EQ


def integrand(atom):
    base, der = atom.split('_', 1)
    kind, n = split(atom)
    iv, idd = DV[der]
    dip = f'D_{n} * ' if kind.endswith('Q') else ''
    if not kind.startswith('E'):
        return f'int_{{Omega_{n}(eps)}} d^{n}X  {dip}[{INS[der]}] * W_{n}'
    from math import comb
    terms = [f'{comb(idd, j)}*{["e0", "e1", "e2"][j]}*[{INS[INV[(iv, idd - j)]]}]' for j in range(idd + 1)]
    return f'int_{{Omega_{n}(eps)}} d^{n}X  {dip}(' + ' + '.join(terms) + f') * W_{n}'


FAMILY = {'A': 'odd numerator A_n', 'Z': 'vacuum Z_n', 'Q': 'current (dipole) Q_n', 'EA': 'endpoint-source odd E A_n',
          'EZ': 'endpoint-source vacuum E Z_n', 'EQ': 'endpoint-source current E Q_n'}
raw_atoms = {}
for atom, info in req['total_tight'].items():
    kind, n = split(atom)
    der = atom.split('_', 1)[1]
    raw_atoms[atom] = {
        'kinks': n, 'family': FAMILY[kind], 'endpoint_source': kind.startswith('E'),
        'endpoint_factor_if_unreflected': (None if not kind.startswith('E') else
                                           ('U^odd: sum_i q_i[f(X_i)+f(1-X_i)]' if n % 2 else 'U^even: sum_i q_i[f(X_i)-f(1-X_i)]')),
        'derivative': der, 'd_v_order': DV[der][0], 'd_delta_order': DV[der][1],
        'integrand_at_v1_delta0': integrand(atom),
        'integration_dimension_after_translation': n - 1 if not kind.startswith('E') else n,
        'tight_leading_eps_power': pmin_tight(atom),
        'needed_eps_powers_minimal': info['eps_powers'],
        'needed_log_orders_by_power_minimal': info['log_orders_by_power'],
        'needed_log_orders_by_power_safe': req['total_safe'][atom]['log_orders_by_power'],
        'used_by_inputs': [k for k in defs if atom in defs[k]['raw_requirements_tight']],
        'exact_expansion_available': atom in two['atoms'],
    }

# ------------------------------------------------------------------ requirements: tight, safe and the difference
def struct_zero(atom, p):
    b = atom.split('_')[0]
    return (b == 'Z2' and p not in (-1, 0)) or (b == 'Q2' and p not in (0, 1))
tight_set = {(a, int(p), k) for a, r in req['total_tight'].items() for p, ks in r['log_orders_by_power'].items() for k in ks}
safe_set = {(a, int(p), k) for a, r in req['total_safe'].items() for p, ks in r['log_orders_by_power'].items() for k in ks}
extras = sorted(safe_set - tight_set)
must_vanish = [f'{a} [eps^{p} l^{k}]' for a, p, k in extras if p < pmin_tight(a)]
genuine = [f'{a} [eps^{p} l^{k}]' for a, p, k in extras if p >= pmin_tight(a)]
two_kink_scalars = sum(1 for a, p, k in tight_set if a in two['atoms'])

EXTRAPOLATIONS = [
    {'id': 'lambda6',
     'statement': 'lambda6 := -2 K6_0 - 4 v d_v K6_0 + 2 v EK6_0  (K6_0 = [eps^0 l^0] of the normalized K6, EK6 its first source derivative).',
     'status': 'EXTRAPOLATION, not written in the note. The note writes h8 with +lambda6 (l.1150-1151) but defines only lambda2 and '
               'lambda4 (l.430-431). lambda6 is the pattern extension lambda_n = -2 K_n,0 - 4 v d_v K_n,0 + 2 v E K_n,0.',
     'jacobian_extension': 'Equivalently the note\'s finite-response Jacobian (l.448-462) is extended by one order: '
                           'J21 += sqrt2 b0 * 6 K6_0 g^5, J22 += lambda6 g^6, R1_2 += sqrt2 b0 K8_1 g^8. Solving J beta = R1 with this '
                           'extension gives exactly the h8 line of the note (review/recurrence_from_jacobian.py).',
     'affects': 'only h8, hence only the input K = -4 h8 (enters D4 with coefficient -3/128, C7 with -3/32). It requires the raw '
                'atoms EQ6_base, EQ4_*, EZ4_*, Q6_v and lower, through EK6_0 and d_v K6_0. C6 and every other input are unaffected.',
     'how_to_test': 'derive the h8 line (and lambda6) from first principles, e.g. by the framework team\'s independent RG map; an '
                    'archive cross-check exists only in the sealed comparison file.'},
    {'id': 'h8-is-in-the-note', 'statement': 'h8 = K8_1 - 2 Q2_0 b7 - 4 K4_0 b5 - 6 K6_0 b3 - lambda2 h6 - lambda4 h4 + lambda6',
     'status': 'written in the note (l.1150-1151, Sec. sec:C8setup); only lambda6 inside it is undefined there.'},
]

AMBIG = [
    {'id': 'matching-wording', 'issue': 'Note l.464 ("restore the canonical/matching contributions using eq:matching") and l.558 '
     '("The explicit finite-tail factor (fugmatch) is needed for p") could suggest an extra matching term in the inputs. In this spec '
     'no fugmatch term is added to any single-log input: p = d_delta C3_1 + 4, where +4 = 2v d_delta j1 is the endpoint integral; '
     'fugmatch changes only l^4, l^3 (appendix l.2270-2289).',
     'resolution': 'confirmed against the note\'s closed forms of a, p, A, E (review/three_kink_independent.py) and of c '
                   '(review/old_inputs_from_note.py). The b check of review/old_inputs_from_note.py is NOT independent in this '
                   'archive-free spec: EA3_base [eps^0 l^0] = -26 + 10 z2 is itself solved from the note\'s b (note-implied target '
                   'EA3.0.l0), so the definition of b is tested only when a project route computes EA3_base [eps^0 l^0] and finds '
                   'that value (gate-review note 2026-10-02). For the 4-8 kink inputs the prescription is not tested against any note '
                   'closed form; a first-principles derivation of the finite-delta matching remains open.'},
    {'id': 'derivative-vs-taylor', 'issue': 'Note eq:insertions writes [delta^2]W = (S3/3 + S2^2/2) W (Taylor coefficient); the raw '
     'atoms *_dd, *_vdd of this spec are FULL second derivatives (S2^2 + 2/3 S3 ...). The dictionary (V = b3_dd/2, gamma = b3_vdd/2, '
     'Q = -2 h4_dd) uses full derivatives; the second-tail validation targets refer to Taylor coefficients (A3_dd/2).',
     'resolution': 'full derivatives everywhere; Taylor factors only in the dictionary and where a target says /2'},
    {'id': 'reflection', 'issue': 'The note defines E with U^odd/U^even; the reflected form 2 sum q_i f_delta(X_i) gives identical values '
     'for first source derivatives (also under delta and v derivatives). Second source derivatives (not needed) would need the '
     'unreflected form (note l.283).', 'resolution': 'either form for every atom in this spec'},
    {'id': 'EA1', 'issue': 'E A1 is not a moment integral: EA1 = j1 = -2/(1+delta) analytically (v-independent). It enters EC3, EC5 and '
     'generates the integer constants of a, p, E, V, gamma.', 'resolution': 'use the analytic value; dropping it shifts b by +4'},
    {'id': 'safe-vs-tight-bounds', 'issue': 'The generic leading-power bound -floor(n/2) (Q2: 0) is safe; the tight bounds of this spec '
     'rest on power counting (RAW_MOMENT_REQUIREMENTS.tight_bounds_argument). With the safe bound K8 formally needs Z4_base at eps^+2 '
     'and Q4_base at eps^-2.', 'resolution': 'supply the safe set; the assembler (--windows both) asserts the below-bound scalars vanish '
     'and that tight and safe assemblies agree'},
    {'id': 'h-vs-eta-names', 'issue': 'Archived notes/scripts call h4,h6 eta4,eta6 (not the endpoint source eta); some call normalized '
     'responses C_n,K_n (not thermal C_n).', 'resolution': 'naming only'},
    {'id': 'v-meaning', 'issue': 'In the recurrence v = b0^2 is the auxiliary reference charge (also the charge in W_n); the essential '
     'v = B^2 = b0^2 eps^delta. The Taylor variable z = v-1 of F,H is identified with b0^2-1 at the matching scale l=0.',
     'resolution': 'definitional'},
    {'id': 'derive_D4-writes', 'issue': 'The archived derive_D4.py writes into the compendium (../verification/algebra relative to '
     'itself); it was NOT run. scripts/derive_invariants.py re-derives B_old^{D4} and D4 independently.', 'resolution': 'use the '
     'assemblies of this spec'},
    {'id': 'lambda6', 'issue': 'lambda6 is not defined in the note.', 'resolution': 'see EXTRAPOLATIONS'},
]

matching = {
    'B': 'B = (b0 - sqrt2 h) eps^(delta/2) -> v = B^2 = b0^2 e^(delta l): produces the tree term -delta in H (beta_v = -delta v); '
         'no extra single-log contribution.',
    'Y': 'Y = g_aux exp[l + b0^2 (1 - e^(delta l))/delta] = g_aux [1 - delta l^2/2 + delta^2 (l^4/8 - l^3/6) + ...] at b0=1; at '
         'delta=0, Y = g_aux e^{-(b0^2-1) l}: produces the tree term z in F; modifies only higher logarithms (appendix: aux '
         '-1/3 l^4 + 5/3 l^3 + 2 z2 l^2 - p l  ->  physical -4/3 l^4 + 13/6 l^3 + 2 z2 l^2 - p l : the single log is unchanged).',
    'in_the_inputs': 'Every input is computed from eq:subtraction (+h8) alone; finite-delta and charge dependence enter ONLY through '
                     '(i) the moments, (ii) j1 = -2/(1+delta) [constants: a:-4, p:+4, E:+4, V:-4, gamma:-4 and products], (iii) j3, j5, '
                     'lambda2,4,6 built from E and d_v of finite parts, (iv) explicit v factors. No additional fugmatch term is added '
                     'to any input. Confirmed for the three-kink sector against the note closed forms (AMBIGUITIES: matching-wording).',
    'in_validation_targets': 'Higher-log predictions use the nonautonomous auxiliary flow with v_a = v0 e^(delta l), u_a = g^2 (1 - delta '
                             'l^2 + delta^2 (l^4/2 - l^3/3)), eta = sqrt2 b0 h - 2 h^2, A1(eta) = B(1+eta,1+eta).',
}

recurrence = {
    'j1': '-2/(1+delta)', 'j3': '-2 d_v C3_0 + EC3_0', 'j5': '-2 d_v C5_0 + EC5_0',
    'lambda2': '-2 Q2_0 - 4 v d_v Q2_0 + 2 v EQ2_0', 'lambda4': '-2 K4_0 - 4 v d_v K4_0 + 2 v EK4_0',
    'lambda6': '-2 K6_0 - 4 v d_v K6_0 + 2 v EK6_0   [EXTRAPOLATION: not defined in the note; see EXTRAPOLATIONS]',
    'b3': 'C3_1 + 2 v j1', 'h4': 'K4_1 - 2 Q2_0 b3 + lambda2', 'b5': 'C5_1 - 3 C3_0 b3 - 2 v j1 h4 + 2 v j3',
    'h6': 'K6_1 - 2 Q2_0 b5 - 4 K4_0 b3 - lambda2 h4 + lambda4',
    'b7': 'C7_1 - 3 C3_0 b5 - 5 C5_0 b3 - 2 v j1 h6 - 2 v j3 h4 + 2 v j5',
    'h8': 'K8_1 - 2 Q2_0 b7 - 4 K4_0 b5 - 6 K6_0 b3 - lambda2 h6 - lambda4 h4 + lambda6',
    'sources': 'note eq:subtraction (l.427-444) for j1..lambda4 and b3..b7; h8 from note l.1150-1151; lambda6 extrapolated.',
    'notes': 'all quantities are functions of (v,delta); v = b0^2 (explicit factors come from d_h = sqrt2 b0 (-2 d_v + E) and '
             'b_dim = b0 - sqrt2 h); derivatives act on the FULL recurrence (explicit v, j1(delta), lambda_n) before setting '
             '(v,delta)=(1,0). Derived from the response-Jacobian equation J beta = R1 (note l.448-464), checked by '
             'review/recurrence_from_jacobian.py. h4,h6 are called eta4,eta6 in some archived notes.',
}

DEFINITIONS = {
    'f_delta': 'f_delta(r) = (r^delta - 1)/delta  (kappa=1), f_0 = log r;  d^j f/d delta^j at 0 = log^(j+1)(r)/(j+1)',
    'charges': 'q_i = (-1)^(i+1), i = 1..n (alternating, first kink +1); q_i q_j = (-1)^(i+j)',
    'domain': 'Omega_n(eps) = {0 < X_1 < ... < X_n < 1 : X_{i+1} - X_i >= eps}; NO wall-endpoint core',
    'kernel': 'W_n(v,delta;X) = exp[ 2 v sum_{i<j} q_i q_j f_delta(X_j - X_i) ];  at (1,0): W_n = prod_{i<j} (X_j-X_i)^(2 q_i q_j)',
    'dipole': 'D_{2m} = sum_{j=1}^m (X_{2j} - X_{2j-1})',
    'raw_moments': {
        'A_{2m+1}': 'int_{Omega_{2m+1}} W', 'Z_{2m}': 'int_{Omega_{2m}} W', 'Q_{2m}': 'int_{Omega_{2m}} D_{2m} W',
        'A_1': '1 (external normalization), its source derivative E A_1 = j_1 = int_0^1 [f(X)+f(1-X)] dX = -2/(1+delta) (v-independent)',
        'E M_n': 'first endpoint-source derivative at eta=0: integrand multiplied by e(delta) = sum_i q_i [f_delta(X_i) +/- f_delta(1-X_i)] '
                 '(+ for odd n = U^odd, - for even n = U^even); after integration identical to the reflected form e(delta) = 2 sum_i q_i '
                 'f_delta(X_i) (reflection X -> 1-X maps Omega_n to itself, preserves W_n and D_{2m}, and q_{n+1-i} = -q_i (n even) / '
                 '+q_i (n odd)). Reflection is NOT valid for second source derivatives (note l.283); none are needed for C6/C7.',
        'E derivative pieces (reflected)': 'e0 = 2 sum q_i log X_i ; e1 = d_delta e = sum q_i log^2 X_i ; e2 = d_delta^2 e = (2/3) sum q_i '
                                           'log^3 X_i  (at delta=0). Unreflected: e0 = sum q_i[log X_i +/- log(1-X_i)], e1 = (1/2) sum '
                                           'q_i[log^2 X_i +/- log^2(1-X_i)], e2 = (1/3) sum q_i[log^3 X_i +/- log^3(1-X_i)]',
        'derivative_insertions (multiply W_n at (1,0))': INS,
        'S_j': 'S_j = sum_{i<k} q_i q_k log^j(X_k - X_i)',
        'derivative_naming': 'atom M_<der>: der in base,v,vv,vvv,d,vd,vvd,dd,vdd = full partial derivative d_v^a d_delta^b (NOT Taylor '
                             'coefficient) at (v,delta)=(1,0), taken on the integrand (also acting on the endpoint factor e(delta) for E '
                             'moments) BEFORE the eps expansion',
        'eps_expansion': 'each raw atom is a finite-cutoff function M(eps) = sum_{p>=pmin} sum_{k>=0} c_{p,k} eps^p l^k; positive powers '
                         'p>0 are genuine and must be kept',
        'coordinate_reductions (optional, value-preserving)': 'non-E moments: integrate the first position -> translation factor (1 - span), '
                                                              'X_j = j*eps + T_j, 0<T_1<..<T_{n-1}<1-(n-1)eps; E moments keep all n absolute '
                                                              'positions X_j = (j-1) eps + T_j',
    },
    'raw_atoms': raw_atoms,
    'normalized_responses': {
        'C3': 'A3 - Z2', 'C5': 'A5 - A3 Z2 + Z2^2 - Z4', 'C7': 'A7 - A5 Z2 + A3 (Z2^2 - Z4) - Z2^3 + 2 Z2 Z4 - Z6',
        'K2 (=Q2)': 'Q2', 'K4': 'Q4 - Q2 Z2', 'K6': 'Q6 - Q4 Z2 + Q2 (Z2^2 - Z4)', 'K8': 'Q8 - Q6 Z2 + Q4 (Z2^2 - Z4) + Q2 (-Z2^3 + 2 Z2 Z4 - Z6)',
        'EC3': 'EA3 - EA1 Z2 - EZ2', 'EC5': 'EA5 - EA3 Z2 - A3 EZ2 + EA1 (Z2^2 - Z4) + 2 Z2 EZ2 - EZ4',
        'EK2 (=EQ2)': 'EQ2', 'EK4': 'EQ4 - EQ2 Z2 - Q2 EZ2', 'EK6': 'EQ6 - EQ4 Z2 - Q4 EZ2 + EQ2 (Z2^2 - Z4) + Q2 (2 Z2 EZ2 - EZ4)',
        'origin': 'coefficients of (A1 + A3 g^2 + ...)/(1 + Z2 g^2 + ...) and (Q2 g^2 + ...)/(1 + Z2 g^2 + ...); E differentiates EVERY factor '
                  'incl. A1 (EA1 = -2/(1+delta)); checked symbolically in derive_requirements.py (note eq:normalization, eq:K8norm)',
    },
    'coefficient_extraction': 'I_m := [eps^0 l^m] I for m = 0,1; products in the normalized responses are formed with the FULL eps/log '
                              'expansions of the factors BEFORE extraction (Z2 ~ 1/eps multiplies eps^1 terms).',
    'derivative_of_coefficients': 'd_v^a d_delta^b I_m := [eps^0 l^m] (d_v^a d_delta^b I)|_(1,0), with d_v^a d_delta^b acting on the '
                                  'normalized product by Leibniz and on each raw moment at integrand level (atom names C3_1[v1d0] etc.).',
    'recurrence': recurrence,
    'beta_jets': {'F': inv['beta_jets']['F'], 'H': inv['beta_jets']['H'],
                  'meaning': 'beta_u = 2 u F, beta_z = (1+z) H, u = g^2, z = v - 1; F = z + sum_k b_{2k+1}(v,delta) u^k, H = -delta - 4 '
                             'sum_k h_{2k}(v,delta) u^k with h2 = -1; Taylor-expand b, h around (v,delta) = (1,0).'},
    'inputs': {k: {kk: v[kk] for kk in ('group', 'definition', 'expansion_in_normalized_atoms', 'n_terms', 'normalized_atoms',
                                         'constant_part', 'max_kinks')}
               | {'raw_atoms_minimal': {a: r['log_orders_by_power'] for a, r in v['raw_requirements_tight'].items()},
                  'raw_atoms_safe': {a: r['log_orders_by_power'] for a, r in v['raw_requirements_safe'].items()},
                  'uses_lambda6_extrapolation': k == 'K'}
               for k, v in defs.items()},
    'normalized_atoms': {k: {kk: v[kk] for kk in ('meaning', 'leibniz_expansion', 'raw_windows_tight', 'raw_windows_safe')}
                         for k, v in norm.items()},
    'matching_and_canonical_terms': matching,
    'assemblies': {
        'D2': inv['D2'], 'T2': inv['T2'], 'D3': inv['D3'], 'T3': inv['T3'], 'D4': inv['D4'],
        'C6 = 4 T3': inv['C6_polynomial'], 'B_old (C6)': inv['B_old_C6'], 'C6 new part': '2V + R + 3J/8 - L/8 + M/4 + N/16',
        'B_old^{D4}': inv['B_old_D4'], 'D4 new part': '-3 alpha/32 + beta/4 - gamma/2 + Phi/16 - Psi/8 - Omega/32 - Q/8 - P/16 - 3K/128',
        'conversion': inv['conversion'],
        'C7': '4 D4 - T3 - T2^2 + C3 C5/2 ; C7 - 4 D4 = ' + cfc['C7 - 4 D4 (known additive)'],
        'fixed_point': inv['fixed_point_det_order'],
    },
}

RAW_REQ = {
    'summary': f'Tight (minimal) set: {len(req["total_tight"])} raw atoms (2..8 kinks), {len(tight_set)} scalars [eps^p l^k] with p in '
               f'{{{min(p for _, p, _ in tight_set)}..{max(p for _, p, _ in tight_set)}}}, k in {{0,1}}. Safe set: {len(safe_set)} scalars '
               f'(+{len(extras)}: {len(must_vanish)} below the tight bound, which must vanish, and {len(genuine)} genuine positive-power '
               f'coefficients that multiply them). Only l^0 and l^1 of a raw coefficient can reach [eps^0 l^0], [eps^0 l^1] of a product; '
               f'a raw moment entering linearly needs only l^m. {two_kink_scalars} of the tight scalars belong to Z2_*/Q2_* and are known '
               f'exactly (out/two_kink_exact.json). For the higher-log validation targets the same eps windows are needed with the full '
               f'log polynomial.',
    'counts': {'raw_atoms': len(req['total_tight']), 'tight_scalars': len(tight_set), 'safe_scalars': len(safe_set),
               'safe_extras': len(extras), 'must_vanish': len(must_vanish), 'genuine_extras': len(genuine),
               'two_kink_exact_scalars_in_tight_set': two_kink_scalars},
    'tight_bounds': req['tight_bounds'],
    'tight_bounds_argument': 'Power counting of the hard-core collapse (eps -> 0). The leading eps^-j comes from j pairs collapsed to gaps '
                             'O(eps), each pair contributing O(1/eps) through its r^-2 kernel. A_{2m+1}, Z_{2m}: all m pairs collapse -> '
                             'eps^-m (the lone charge of A, the endpoint factor of EA are O(1)). Q_{2m}: the dipole D_{2m} is O(eps) when '
                             'all pairs collapse, O(1) when one pair is open -> eps^-(m-1). EZ_{2m}: the reflected endpoint factor 2 sum '
                             'q_i log X_i is O(eps/X) per collapsed pair -> eps^-(m-1). EQ_{2m}: dipole and endpoint factors each cost one '
                             'power when all pairs collapse, both are O(1) with one pair open -> eps^-(m-1) for m >= 2 and eps^0 for EQ2. '
                             'The safe bound -floor(n/2) (Q2: 0) does not use this; the assembler checks the difference.',
    'safe_bounds': req['safe_bounds'],
    'safe_minus_tight': {'below_tight_bound_must_vanish': must_vanish, 'genuine_positive_power_extras': genuine},
    'policy': 'Integration teams supply every TIGHT scalar plus the below-bound scalars (they must come out zero within precision). '
              'scripts/assemble_from_raw.py --windows both (the default) refuses missing scalars, asserts the below-bound ones vanish '
              '(--zero-tol) and requires the tight and safe assemblies to agree (--agree-tol). The genuine positive-power extras are '
              'looked up only if their partner is non-zero (a convention error), in which case a missing one is an error.',
    'tight': {a: {'eps_powers': r['eps_powers'], 'log_orders_by_power': r['log_orders_by_power']} for a, r in req['total_tight'].items()},
    'safe': {a: {'eps_powers': r['eps_powers'], 'log_orders_by_power': r['log_orders_by_power']} for a, r in req['total_safe'].items()},
    'by_kink_number': {str(n): sorted([a for a, r in raw_atoms.items() if r['kinks'] == n]) for n in range(2, 9)},
    'hardest': ['A7_v [eps^0 l^1] (6-dim, Omega)', 'Q8_base [eps^0 l^1] (7-dim, K)', 'A7_base [eps^0 l^1] (J,K)',
                'EQ6_base [eps^0 l^0] (6-dim absolute, K only, via lambda6)', 'Q6_{base,v,d} (5-dim; P, N, K)',
                'Z6_{base,v} (Z6_base at eps^-1 and eps^0)', 'A5_{vd,vv,d,v,base}', 'EA5_{base,v} [eps^0 l^0] (5-dim absolute)'],
}

CLAIMS = {
    'remark': 'The claims under test (closed forms given in the task and in the note). The decimals are OUR evaluations of these closed '
              'forms (scripts/derive_invariants.py), not archive numbers.',
    'C6': {'closed_form': inv['claims_closed_form']['C6'], 'value': inv['claims_value_60']['C6'], 'note': 'eq:C6exact (l.709-710)'},
    'T3': {'closed_form': 'C6/4', 'value': inv['claims_value_60']['T3']},
    'D4': {'closed_form': inv['claims_closed_form']['D4'], 'value': inv['claims_value_60']['D4'], 'note': 'eq:D4-final (l.1013-1018)'},
    'C7': {'closed_form': inv['claims_closed_form']['C7'], 'value': inv['claims_value_60']['C7'], 'note': 'eq:C7known (l.1008-1010)'},
    'established_lower_order': {k: {'closed_form': inv['claims_closed_form'][k], 'value': inv['claims_value_60'][k]}
                                for k in ('D2', 'T2', 'C3', 'C4', 'D3', 'C5')},
}

CHECKS = {
    'remark': 'Checks that use NO archive data. Archive comparisons (definitions reproduce the 25 archived inputs, assembler on archived '
              'raw coefficients, targets vs archived series) are sealed in comparison/archive_comparison.json.',
    'normalization_from_generating_functions': 'derive_requirements.py: C3..C7, K2..K8, EC3, EC5, EK2..EK6 equal the note formulas '
                                               '(symbolic assertions)',
    'algebra': inv['checks'],
    'closed_form_consistency': cfc,
    'two_kink_exact': two['checks'],
    'validation_internal': vt['internal_checks'],
    'reviewer_archive_free_checks': {
        'recurrence_from_jacobian': 'review/recurrence_from_jacobian.py: b3..h8 recurrence = order-by-order solution of J beta = R1 '
                                    '(extended one order, EXTRAPOLATIONS lambda6)',
        'algebra_independent': ({k: v for k, v in REVIEW['algebra_independent'].items() if isinstance(v, bool)}
                                if 'algebra_independent' in REVIEW else 'not run'),
        'old_inputs_from_note': REVIEW.get('old_inputs_from_note', 'not run'),
        'three_kink_independent': 'review/three_kink_independent.py: a, p, A, E from scratch equal the note closed forms to 1e-28; note '
                                  'log coefficients of C3, d_v C3, d_delta C3 and the A3_dd/2 higher logs reproduced',
    },
}

meta = {
    'title': 'Definitions-only specification for an independent re-derivation of the C6/C7 inputs of the d=1 LRI short-range-end expansion',
    'version': 2,
    'created': SPEC_VERSION_DATE,          # fixed, so that a rerun on another day is byte-identical
    'status': 'CURRENT. This is the file production code and integration teams read.',
    'archive_free': 'Contains NO archive-derived number. Every value is a note statement, an exact derivation, a note-implied value '
                    'or a project-internal computation (see VALIDATION_TARGETS.provenance_tags). Archive numbers are sealed in '
                    'comparison/archive_comparison.json, which production code never reads.',
    'companion_files': {'sealed_archive_comparison': 'comparison/archive_comparison.json',
                        'deprecated_compatibility_copy': 'spec.json (same definitions, old key layout, archive blocks removed)',
                        'readable': 'spec.md', 'hashes': 'SHA256SUMS'},
    'compendium': '<PROJECT>/LRI_SRI_research_compendium (read-only)',
    'primary_definition_source': 'note/LRI_perturbation_compendium.tex, Secs. 3-6 (l.173-500), 7-8, 13-14 (l.1006-1160), appendix A (l.2095-2291)',
    'definition_cross_check_sources': [
        'code/archived/LRI_1d_complete/stages/C6_integrals/reproducibility/assemble_C6.py',
        'code/archived/C8_rational_completion/workspace/old_C7/C7_completion/engine/assemble_C7.py',
        'code/archived/R6_Task_A_completion/engine/run_moment.py (read for insertion formulas only; the reviewer re-derived every insertion)',
        'code/archived/C6_closed_form/proof/derive_trace.py, code/archived/C7_closed_form_proof/code/derive_D4.py',
        'documentation/archived/LRI_1d_complete/stages/C6_integrals/C6_thermal_note.tex, documentation/archived/C7_completion/note/C7_thermal_completion.tex'],
    'independence': 'No archive integration/evaluation engine imported or called. Archive scripts above were READ (not run) to cross-check '
                    'the definitions; no archive number enters this file.',
    'generated_from': {f'out/{n}': hashlib.sha256((OUT / n).read_bytes()).hexdigest()
                       for n in ('input_definitions.json', 'normalized_atoms.json', 'raw_requirements.json', 'invariants.json',
                                 'closed_form_consistency.json', 'two_kink_exact.json', 'validation_targets.json',
                                 'sanity_finite_cutoff.json')},
    'sections': ['CLAIMS_UNDER_TEST', 'CONVENTIONS', 'DEFINITIONS', 'EXTRAPOLATIONS', 'RAW_MOMENT_REQUIREMENTS', 'VALIDATION_TARGETS',
                 'SPEC_CHECKS_ARCHIVE_FREE', 'AMBIGUITIES_AND_DISCREPANCIES'],
}
CONVENTIONS = {
    'thermal': 'delta = 1-s, x = Delta_sigma = delta/2, t = sqrt(x), Delta_eps = 1 + sum_n C_n t^n',
    'invariants': 'T(delta) = delta/2 + T2 delta^2 + T3 delta^3 + ..., D(delta) = -2 delta + D2 delta^2 + D3 delta^3 + D4 delta^4 + ...; '
                  'Delta_pm = 1 + T/2 pm sqrt(T^2/4 - D), Delta_eps = Delta_-',
    'conversion': inv['conversion'],
    'cutoff': 'eps = dimensionless hard core on CONSECUTIVE kink gaps only; l = log(eps); unit interval; kappa = 1',
    'zeta_symbols': 'z2..z6 = zeta(2)..zeta(6); L2 = log 2; L3 = log 3; Li2h = Li2(-1/2); Li4h = Li4(1/2)',
}

spec_def = {'meta': meta, 'CLAIMS_UNDER_TEST': CLAIMS, 'CONVENTIONS': CONVENTIONS, 'DEFINITIONS': DEFINITIONS,
            'EXTRAPOLATIONS': EXTRAPOLATIONS, 'RAW_MOMENT_REQUIREMENTS': RAW_REQ, 'VALIDATION_TARGETS': vt,
            'SPEC_CHECKS_ARCHIVE_FREE': CHECKS, 'AMBIGUITIES_AND_DISCREPANCIES': AMBIG}
json.dump(spec_def, open(SPEC / 'spec_definitions.json', 'w'), indent=1)

# ------------------------------------------------------------------ deprecated compatibility file (old key layout)
old = copy.deepcopy(spec_def)
legacy = {
    'DEPRECATED': 'spec.json is DEPRECATED (kept for backward compatibility only). Use spec_definitions.json. The former '
                  'VALUES_ARCHIVE_COMPARISON_ONLY block and the archive comparisons in VALIDATION_TARGETS/SPEC_CHECKS were MOVED to the '
                  'sealed comparison/archive_comparison.json; this file contains no archive-derived number.',
    'meta': old['meta'] | {'status': 'DEPRECATED compatibility copy of spec_definitions.json (old key layout)',
                           'sections': ['CONVENTIONS', 'DEFINITIONS', 'RAW_MOMENT_REQUIREMENTS', 'VALUES_ARCHIVE_COMPARISON_ONLY',
                                        'VALIDATION_TARGETS', 'SPEC_CHECKS', 'AMBIGUITIES_AND_DISCREPANCIES']},
    'CONVENTIONS': old['CONVENTIONS'],
    'DEFINITIONS': old['DEFINITIONS'] | {'extrapolations': old['EXTRAPOLATIONS']},
    'RAW_MOMENT_REQUIREMENTS': old['RAW_MOMENT_REQUIREMENTS'] | {'minimal': old['RAW_MOMENT_REQUIREMENTS']['tight']},
    'VALUES_ARCHIVE_COMPARISON_ONLY': {'MOVED': 'comparison/archive_comparison.json (sealed; comparison step only)'},
    'VALIDATION_TARGETS': old['VALIDATION_TARGETS'] | {'finite_cutoff_full_moments': {
        'definition': old['VALIDATION_TARGETS']['finite_cutoff']['definition'],
        'values': old['VALIDATION_TARGETS']['finite_cutoff']['independent_values'],
        'MOVED': 'archived finite-cutoff values -> comparison/archive_comparison.json (archive_finite_cutoff_values)'}},
    'SPEC_CHECKS': old['SPEC_CHECKS_ARCHIVE_FREE'],
    'AMBIGUITIES_AND_DISCREPANCIES': old['AMBIGUITIES_AND_DISCREPANCIES'],
    'CLAIMS_UNDER_TEST': old['CLAIMS_UNDER_TEST'],
}
json.dump(legacy, open(SPEC / 'spec.json', 'w'), indent=1)

# ------------------------------------------------------------------ C8 extension (version 3, 2026-10-03)
# Added AFTER spec.json (deprecated, C6/C7 layout) is written, so spec.json and every C6/C7 block stay byte-identical.
if (OUT / 'C8').is_dir():
    import c8_block
    spec_def['meta']['version'] = 3
    spec_def['meta']['C8_extension'] = (f'{c8_block.C8_DATE}: block C8_EXTENSION added (the ten new inputs of C8 = 8 T4); the C6/C7 '
                                        'blocks are unchanged. See README.md "C8 extension".')
    spec_def['meta']['sections'] = spec_def['meta']['sections'] + ['C8_EXTENSION']
    spec_def['meta']['companion_files']['sealed_archive_comparison_C8'] = 'comparison_C8/ (sealed; SHA256SUMS inside)'
    spec_def['C8_EXTENSION'] = c8_block.build()
    json.dump(spec_def, open(SPEC / 'spec_definitions.json', 'w'), indent=1)

# ------------------------------------------------------------------ hashes
lines = []
for rel in (['spec_definitions.json', 'spec.json'] + [f'out/{p.name}' for p in sorted(OUT.glob('*.json')) if not p.is_symlink()]
            + [f'out/C8/{p.name}' for p in sorted((OUT / 'C8').glob('*.json'))]):
    lines.append(f'{hashlib.sha256((SPEC / rel).read_bytes()).hexdigest()}  {rel}')
(SPEC / 'SHA256SUMS').write_text('\n'.join(lines) + '\n')
print('spec_definitions.json', (SPEC / 'spec_definitions.json').stat().st_size, 'bytes;', 'spec.json (deprecated)',
      (SPEC / 'spec.json').stat().st_size, 'bytes')
print(RAW_REQ['summary'])
print(lines[0])
