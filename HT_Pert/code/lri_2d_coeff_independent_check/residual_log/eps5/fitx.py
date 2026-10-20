"""fitlib with extra divergent basis functions: 'L', 'LlL' = L ln L, 'Ll2' = L ln^2 L (plus fitlib's)."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import fitlib as F  # noqa: E402

_orig = F.basis


def basis(name, L):
    l = np.log(L)
    if name == "LlL":
        return L * l
    if name == "Ll2":
        return L * l * l
    if name == "Ll3":
        return L * l ** 3
    if name == "l3":
        return l ** 3
    return _orig(name, L)


F.basis = basis
fit = F.fit
