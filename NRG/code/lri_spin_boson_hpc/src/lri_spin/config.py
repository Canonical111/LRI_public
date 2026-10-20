"""Numerical resolutions: identical physical truncation to the supplied solver."""
from dataclasses import dataclass, asdict
import math
import numpy as np

@dataclass(frozen=True)
class Config:
    s: float = 0.9
    Lambda: float = 2.0
    nb: int = 8
    keep: int = 32  # PER field-parity sector
    nsites: int = 70
    tunneling: float = 0.1
    nlevels: int = 8
    threads: int = 1

    def check(self):
        if not all(math.isfinite(float(v)) for v in (self.s, self.Lambda, self.tunneling)):
            raise ValueError('Nonfinite physical parameter')
        if not (0 < self.s <= 1 and self.Lambda > 1 and self.tunneling > 0):
            raise ValueError('Require 0<s<=1, Lambda>1, tunneling>0')
        for key in ('nb','keep','nsites','threads','nlevels'):
            v = getattr(self,key)
            if isinstance(v,bool) or not isinstance(v,(int,np.integer)) or v < (2 if key in ('nb','keep','nsites') else 1):
                raise ValueError(f'Invalid positive integer {key}: {v}')

    def asdict(self):
        return asdict(self)


def chain_coefficients(s, Lambda, nsites):
    # Byte-for-byte formulas from reference nrg.py: no modified discretization.
    q=1.0/Lambda; a=q**s
    c=(s+1)/(s+2)*(-np.expm1((s+2)*np.log(q)))/(-np.expm1((s+1)*np.log(q)))
    n=np.arange(nsites+1,dtype=float)
    A=(1-a*q**(n+1))**2/((1-a*q**(2*n+1))*(1-a*q**(2*n+2)))
    C=a*(1-q**n)**2/((1-a*q**(2*n))*(1-a*q**(2*n+1)))
    onsite=c*(A+C)
    hopping=np.zeros(nsites)
    hopping[1:]=c*np.sqrt(A[:-2]*C[1:-1]/q)
    return onsite[:nsites],hopping
