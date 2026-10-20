"""Fixed, state-averaged local subspaces for the unchanged product Hamiltonian.

Only this opt-in path uses a fixed primitive span. The original DressedSolver,
LocalProblem, window equations, and raw execution path are not modified.
"""
from __future__ import annotations
import math
import time
import numpy as np
from scipy.linalg import block_diag, eigh
from .local import LocalProblem
from .solver import DressedSolver


class FixedLocal(LocalProblem):
    """Project each primitive operator independently into a fixed parity isometry."""
    def __init__(self, isometry, scale):
        u = np.asarray(isometry, dtype=np.float64)
        if u.ndim != 2 or u.shape[1] % 2:
            raise ValueError('The local isometry must have two equally sized parity blocks')
        osc, count = u.shape
        nz = count // 2
        if not np.all(np.isfinite(u)) or not math.isfinite(scale) or scale <= 0:
            raise ValueError('Non-finite local basis or invalid primitive scale')
        if np.max(np.abs(u.T @ u - np.eye(count))) > 2e-10:
            raise ValueError('Nonorthonormal local isometry')
        if max(np.max(np.abs(u[1::2, :nz])), np.max(np.abs(u[::2, nz:]))) > 1e-12:
            raise ValueError('Local isometry violates field parity')
        super().__init__(nz, osc)
        self.fixed_U = u.copy()
        self.fixed_scale = float(scale)
        self.physq = {j: self.fixed_scale**j * u.T @ self.q[j] @ u for j in (1, 2, 3, 4)}
        self.kinetic = u.T @ self.pp @ u / (4 * self.fixed_scale**2)
        d = osc + 4
        creation = np.diag(np.sqrt(np.arange(1, d)), k=-1)
        annihilator = (self.fixed_scale*(creation+creation.T) - (creation-creation.T)/self.fixed_scale)/2
        self.a0fixed = u.T @ annihilator[:osc, :osc] @ u
        self._cache = None

    def evaluate(self, delta, theta):
        theta = np.asarray(theta, dtype=np.float64)
        if theta.shape != (2,) or not np.all(np.isfinite(theta)) or abs(theta[1]) > 25:
            raise ValueError('Invalid coupling coordinates')
        e = math.exp(float(theta[1]))
        g = 192*e**3/delta**2
        a = 4*e*e*theta[0]/delta
        r = a + g/2 - delta/4
        h = delta*self.kinetic + a*self.physq[2] + g*self.physq[4]/12
        rotations, energy = [], []
        z = self.nz
        for parity in (0, 1):
            ix = slice(parity*z, (parity+1)*z)
            w, rotation = eigh(h[ix, ix], check_finite=False)
            rotations.append(rotation)
            energy.extend(w)
        rotation = block_diag(*rotations)
        energy = np.asarray(energy)
        shift = energy[0]
        w = energy - shift
        x = {j: rotation.T @ self.physq[j] @ rotation for j in (1, 2, 3, 4)}
        eye = np.eye(2*z)
        vertices = np.array([(2*a-delta/2)*x[1] + g*x[3]/3,
                             (a-delta/4)*eye + g*x[2]/2,
                             g*x[1]/3, g*eye/12])
        u = self.fixed_U @ rotation
        self._cache = (float(delta), theta.copy(), rotation, x, float(a), float(g))
        # This is a projected eigensolve residual, NOT an omitted-span bound.
        residual = float(np.max(np.linalg.norm(h@rotation - rotation*energy, axis=0)))
        return w, vertices, u, {
            'r': float(r), 'g': float(g), 'A': float(a),
            'local_scale': self.fixed_scale, 'zero_basis_scale': 1.,
            'local_auxiliary_residual': residual,
            'local_auxiliary_residual_scope': 'eigensolve inside the fixed local span; not its truncation error',
            'local_edge_max': float(np.max(np.sum(u[-8:]**2, axis=0))),
            'local_basis_mode': 'density',
        }

    def derivatives(self, delta, theta):
        """Physical derivatives at fixed span, expressed in the current eigenbasis.

        Off-diagonal dH matrix elements are essential; differentiating only the
        local eigenvalues would omit the response carried by the full density.
        """
        self.evaluate(delta, theta)
        _, _, _, x, a, g = self._cache
        eye = np.eye(2*self.nz)
        result = []
        for da, dg in ((4*math.exp(2*float(theta[1]))/delta, 0.), (2*a, 3*g)):
            dh = da*x[2] + dg*x[4]/12
            dh = dh - dh[0, 0]*eye  # same theta-dependent local vacuum shift
            dl = np.array([2*da*x[1]+dg*x[3]/3,
                           da*eye+dg*x[2]/2, dg*x[1]/3, dg*eye/12])
            result.append((dh, dl))
        return result

    def a0(self, delta, theta):
        self.evaluate(delta, theta)
        rotation = self._cache[2]
        return rotation.T @ self.a0fixed @ rotation


def rotate_warm(vector, op, field, old, new):
    """Whole coordinate rotation within the SAME primitive span (not just signs)."""
    z = op.nz
    x = np.asarray(vector).reshape(op.nB, z).copy()
    for parity in (0, 1):
        ix = slice(parity*z, (parity+1)*z)
        rows = (op.kpar ^ field) == parity
        x[rows] = x[rows] @ (old[:, ix].T @ new[:, ix])
    return x.ravel()


def state_contractions(op, vector, field):
    z = op.nz
    x = np.asarray(vector).reshape(op.nB, z)
    rho = np.zeros((2*z, 2*z))
    for parity in (0, 1):
        ix = slice(parity*z, (parity+1)*z)
        rows = (op.kpar ^ field) == parity
        rho[ix, ix] = x[rows].T @ x[rows]
    return rho, op.contractions(vector, field)[1]


class DensitySolver(DressedSolver):
    """Original bath/window solver with the opt-in fixed local basis and Jacobian."""
    def __init__(self, bath_cut, isometry, scale, **kwargs):
        u = np.asarray(isometry, dtype=np.float64)
        if kwargs.get('zero_scale', 1.) != 1.:
            raise ValueError('A saved density basis already fixes its primitive scale; --zero-scale must be 1')
        super().__init__(bath_cut, u.shape[1]//2, u.shape[0], **kwargs)
        self.local_problem = FixedLocal(u, scale)

    def prepare(self, theta):
        if self.op is None:
            raise RuntimeError('Call set_delta first')
        start = time.perf_counter()
        w, vertices, u, info = self.local_problem.evaluate(self.delta, theta)
        if self._warm_U is not None:
            for field, vector in list(self.warm.items()):
                self.warm[field] = rotate_warm(vector, self.op, field, self._warm_U, u)
            if self.win is not None:
                for key, vector in list(self.win.warm.items()):
                    op = self.op if key == 'top' else self.win.ops[key]
                    self.win.warm[key] = rotate_warm(vector, op, 0, self._warm_U, u)
        self._warm_U = u.copy()
        self.timings['local'] += time.perf_counter() - start
        return w, vertices, u, info

    def response_jacobian(self, theta, out, Uref, step_scale=1e-5):
        start = time.perf_counter()
        op = self.op
        refs = ((0, 0), (1, 0), (1, 1))
        con = [state_contractions(op, out[f][1][:, j], f) for f, j in refs]
        state = out.get('window')
        if state is not None:
            levels = [op.level_weights(out[f][1][:, j]) for f, j in refs]
            vac = {lev: state_contractions(self.win.ops[lev], d['vector'], 0)
                   for lev, d in state['vac'].items() if lev != 'top'}
            top = state_contractions(op, state['vac']['top']['vector'], 0)
        jac = np.empty((2, 2))
        for j, (dh, dl) in enumerate(self.local_problem.derivatives(self.delta, theta)):
            def expectation(c):
                return float(np.sum(c[0]*dh) + np.sum(c[1]*dl))
            dp = np.array([expectation(c) for c in con])
            if state is not None:
                dd = self.win.derivative(state, {lev: expectation(c) for lev, c in vac.items()},
                                         expectation(top), state['vac']['top']['weights'])
                dp += np.array([p@dd for p in levels])
            jac[:, j] = dp[1:] - dp[0]
        self.timings['jacobian'] += time.perf_counter() - start
        return jac

    def solve(self, *args, **kwargs):
        row = super().solve(*args, **kwargs)
        row['solver'] = 'factorized operator; fixed density span; full-density Hellmann-Feynman/window Jacobian'
        row['local_retained_edge_weights_scope'] = 'top two eigenstates inside the retained span; not discarded density weight'
        return row


def select_density_basis(solver, theta, keep):
    """Use only top vacuum, sigma, shadow and every lower even-cutoff vacuum.

    This function never requests the thermal state. It returns only small local
    data and calibration diagnostics; all coupled-state vectors stay transient.
    """
    if not 2 <= keep <= solver.nz:
        raise ValueError('Require 2 <= keep <= teacher local states per parity')
    if solver.window != 'vacuum' or solver.window_mode != 'consistent' or solver.bath_cut % 2:
        raise ValueError('Density training currently supports even bath cutoffs with the consistent vacuum window')
    w, vertices, u, info = solver.prepare(theta)
    out = {}
    state, window = solver.window_spectrum(w, vertices, 1, out)
    odd_e, odd_v, _, _ = solver.sector_solve(solver.op, w, vertices, 1, 2, solver.warm, 1, True)
    even_e, even_v = out[0]
    rho = [np.zeros((solver.nz, solver.nz)), np.zeros((solver.nz, solver.nz))]
    maxres = 0.
    targets = []

    def add(op, vector, field, weight, label, energy):
        nonlocal maxres
        x = vector.reshape(op.nB, op.nz)
        if abs(float(vector@vector)-1.) > 1e-9:
            raise ValueError('Training state normalization failed')
        for parity in (0, 1):
            xq = x[(op.kpar ^ field) == parity]
            rho[parity] += weight * (xq.T @ xq)
        res = float(np.linalg.norm(op.linear_operator(w, vertices, field)@vector-energy*vector))
        maxres = max(maxres, res)
        targets.append({'name': label, 'weight': float(weight), 'residual': res})

    add(solver.op, even_v[:, 0], 0, 1/6, 'top vacuum', float(even_e[0]))
    add(solver.op, odd_v[:, 0], 1, 1/6, 'sigma', float(odd_e[0]))
    add(solver.op, odd_v[:, 1], 1, 1/6, 'shadow', float(odd_e[1]))
    m = solver.bath_cut//2
    for lev, data in state['vac'].items():
        if lev != 'top':
            add(solver.win.ops[lev], data['vector'], 0, 1/(2*m), f'vacuum N<={lev}', state['Ev'][lev])
    rho[0][0, 0] += 1/(2*m)
    targets.append({'name': 'local vacuum N=0', 'weight': float(1/(2*m)), 'residual': 0.})
    if maxres > solver.residual_tol:
        raise ValueError(f'Training-state eigenvector gate: {maxres:g}')
    if abs(sum(np.trace(p) for p in rho)-1.) > 1e-9:
        raise ValueError('Training density trace is not one')
    selected, eigenvalues, discarded = [], [], []
    for matrix in rho:
        d, v = eigh((matrix+matrix.T)/2, check_finite=False)
        order = np.argsort(d)[::-1]
        d, v = d[order], v[:, order]
        if d.min() < -1e-10:
            raise ValueError('Training density is not positive semidefinite')
        # Deterministic sign gauge; no eigenvalue/physical amplitude is pruned.
        for col in range(v.shape[1]):
            if v[np.argmax(np.abs(v[:, col])), col] < 0:
                v[:, col] *= -1
        selected.append(v[:, :keep])
        eigenvalues.append(d.tolist())
        discarded.append(float(d[keep:].sum()))
    chosen = u @ block_diag(*selected)
    # Exact parity zeros should stay exact in the stored representation.
    chosen[1::2, :keep] = 0.
    chosen[::2, keep:] = 0.
    residual = [float(odd_e[0]-even_e[0]-solver.delta),
                float(odd_e[1]-even_e[0]-(1-solver.delta))]
    meta = {'targets': targets, 'density_eigenvalues': eigenvalues,
            'discarded_by_parity': discarded, 'thermal_target': False,
            'teacher_primary_residual': residual, 'max_training_eigenvector_residual': maxres,
            'window_max_fixed_point_residual': max([window['top_fixed_point_residual'],
                *window['sublevel_fixed_point_residuals'].values()]),
            'selection': 'state average: top calibration states weight 1/6 each; lower/zero vacua weight 1/(2m) each'}
    return chosen, info['local_scale'], meta
