"""Independent exact verifier for the C6 period identities.

Every source row is regenerated from its analytic label.  The verifier does not
use the modular discovery program, numerical periods, or third-party packages.
The mathematical identities are proved in the accompanying note.
"""
from __future__ import annotations
from collections import defaultdict
from fractions import Fraction
from functools import lru_cache
from typing import Iterable

Q = Fraction
Word = tuple[int, ...]

@lru_cache(maxsize=60000)
def shuffle(left: Word, right: Word) -> dict[Word, int]:
    if not left:
        return {right: 1}
    if not right:
        return {left: 1}
    out: dict[Word, int] = defaultdict(int)
    for word, count in shuffle(left[1:], right).items():
        out[(left[0],) + word] += count
    for word, count in shuffle(left, right[1:]).items():
        out[(right[0],) + word] += count
    return dict(out)

def add_scaled(out: dict, row: dict, scale: Q = Q(1)) -> None:
    for word, coefficient in row.items():
        out[word] += scale * coefficient

def nonzero(row: dict) -> dict:
    return {word: coefficient for word, coefficient in row.items() if coefficient}

@lru_cache(maxsize=50000)
def fixed_letter_expansion(letters: tuple[tuple[int, int], ...]) -> dict[Word, int]:
    """Integrate the total differential for affine letters s*T+c.

    Entry (s,c) has s=0 or 1. Endpoints are T and 0. A nonconstant
    dlog contributes 1/(T-root); the resulting period letter is -root.
    All roots here are nonpositive integers. Integration constants follow
    the endpoint value at T=0, with tangential pure-zero words retained.
    """
    if not letters:
        return {(): 1}
    result: dict[Word, int] = defaultdict(int)
    endpoints = ((1, 0),) + letters + ((0, 0),)
    for position, (slope, shift) in enumerate(letters):
        reduced = fixed_letter_expansion(letters[:position] + letters[position + 1:])
        for neighbor, sign in ((endpoints[position], 1), (endpoints[position + 2], -1)):
            slope_difference = neighbor[0] - slope
            if slope_difference == 0:
                continue
            root = Q(shift - neighbor[1], slope_difference)
            if root.denominator != 1 or root > 0:
                raise ValueError(f"Invalid affine singularity: {root}")
            index = -int(root)
            for tail, coefficient in reduced.items():
                result[(index,) + tail] += sign * coefficient
    return nonzero(result)

def zeta_word(weight: int) -> dict[Word, Q]:
    if weight < 2 or weight > 5:
        raise ValueError("Only weights 2--5 are required")
    return {(2,) + (1,) * (weight - 1): -Q(2 ** (weight - 1), 2 ** (weight - 1) - 1)}

def binary_period(bits: Word) -> dict[Word, Q]:
    """Values from the beta-integral, shuffle/stuffle, and duality proof.

    At weight five, A=zeta(4,1)=2*zeta(5)-zeta(2)*zeta(3).
    Stuffle and the shuffle 01 with 001 then give zeta(3,2), zeta(2,3).
    The remaining depth-three/four words follow by binary duality.
    """
    low = {
        (0,1): Q(-1),
        (0,0,1): Q(-1), (0,1,1): Q(1),
        (0,0,0,1): Q(-1), (0,0,1,1): Q(1,4),
        (0,1,0,1): Q(3,4), (0,1,1,1): Q(-1),
    }
    if len(bits) <= 4:
        if bits not in low:
            raise ValueError(f"Nonconvergent binary word: {bits}")
        return {w: low[bits] * a for w, a in zeta_word(len(bits)).items()}
    # Pairs denote coefficients of (zeta(5), zeta(2)*zeta(3)).
    z41 = (Q(2), Q(-1))
    # From X+Y=(P-Z) and 3X+Y=P-6*z41.
    z32 = tuple((p - 6*a - (p-z))/2 for a,p,z in zip(z41,(Q(0),Q(1)),(Q(1),Q(0))))
    z23 = tuple(p-z-a for p,z,a in zip((Q(0),Q(1)),(Q(1),Q(0)),z32))
    values = {
        (0,0,0,0,1): (Q(-1),Q(0)),
        (0,0,0,1,1): z41,
        (0,0,1,0,1): z32,
        (0,1,0,0,1): z23,
        (0,0,1,1,1): tuple(-a for a in z41),
        (0,1,0,1,1): tuple(-a for a in z32),
        (0,1,1,0,1): tuple(-a for a in z23),
        (0,1,1,1,1): (Q(1),Q(0)),
    }
    if bits not in values:
        raise ValueError(f"Nonconvergent binary word: {bits}")
    a,b = values[bits]
    result: dict[Word,Q] = defaultdict(Q)
    add_scaled(result,zeta_word(5),a)
    for word, coefficient in shuffle((2,1),(2,1,1)).items():
        result[word] += b * Q(8,3) * coefficient
    return nonzero(result)

def multiply_by_word(row: dict, multiplier: Word) -> dict:
    result: dict[Word,Q] = defaultdict(Q)
    for word, coefficient in row.items():
        for shuffled, count in shuffle(word,multiplier).items():
            result[shuffled] += coefficient * count
    return nonzero(result)

def generate_relation(label: dict) -> dict[Word,Q]:
    kind = label['kind']
    result: dict[Word,Q] = defaultdict(Q)
    if kind == 'confluence':
        bits = tuple(label['bits'])
        intercepts = tuple(label['a'])
        if len(bits) != len(intercepts) or bits[0] != 0 or bits[-1] != 1:
            raise ValueError("Invalid confluence endpoints")
        if any(b not in (0,1) or not isinstance(a,int) or a < (1 if b else 0)
               for b,a in zip(bits,intercepts)):
            raise ValueError("Invalid confluence intercept")
        affine = tuple((b,a if b else -a) for b,a in zip(bits,intercepts))
        add_scaled(result,fixed_letter_expansion(affine))
        add_scaled(result,binary_period(bits),Q(-1))
    elif kind == 'Rzero':
        if label['a'] not in (0,1):
            raise ValueError("Only R_0 and R_1 vanish here")
        result[(label['a'],)] = Q(1)
    elif kind == 'logproduct':
        a,b = label['a'],label['b']
        if not isinstance(a,int) or not isinstance(b,int) or a <= 0 or b <= 0:
            raise ValueError("Logarithm arguments must be positive integers")
        result[(a*b,)] += 1
        result[(a,)] -= 1
        result[(b,)] -= 1
    elif kind == 'scaling':
        d,word = label['d'],tuple(label['word'])
        if not isinstance(d,int) or d <= 0 or not word or word[-1] <= 0 or any(a<0 for a in word):
            raise ValueError("Invalid scaling relation or divergent lower endpoint")
        result[tuple(d*a for a in word)] += 1
        for cut in range(len(word)+1):
            add_scaled(result,shuffle((d,)*cut,word[cut:]),Q(-1))
    else:
        raise ValueError(f"Unknown relation: {kind}")
    multiplier = tuple(label.get('times',()))
    if any(not isinstance(a,int) or a<0 for a in multiplier):
        raise ValueError("Invalid multiplier word")
    return multiply_by_word(nonzero(result),multiplier)

def verify_certificate(data: dict) -> dict:
    weight = int(data['weight'])
    residual: dict[Word,Q] = defaultdict(Q)
    target = {}
    for word, coefficient in data['target']:
        word = tuple(word)
        if len(word) != weight or word in target:
            raise ValueError("Invalid or repeated target word")
        target[word] = Q(coefficient)
        residual[word] += target[word]
    for record in data['certificate']:
        coefficient = Q(record['coefficient'])
        source = generate_relation(record['relation'])
        if any(len(word) != weight for word in source):
            raise ValueError("Inhomogeneous source relation")
        add_scaled(residual,source,-coefficient)
    residual = nonzero(residual)
    if residual:
        raise AssertionError(f"Weight {weight}: {len(residual)} nonzero residual words: {list(residual.items())[:3]}")
    return {'weight':weight,'target_words':len(target),
            'certificate_rows':len(data['certificate']),'exact_residual_words':0}
