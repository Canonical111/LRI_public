# integ_d1: C^SR_8 from the integrable point, magnetization scheme (d = 1)

At s = 1 the kink gas of the chain is the Anderson-Yuval-Hamann gas of the anisotropic Kondo model, which the Bethe
ansatz solves. This package computes the eighth coefficient C^SR_8 of the expansion about the short-range end in a
scheme built on that point: the couplings are defined by the magnetization of the infinite chain in a field (the
magnetization scheme), the delta = 0 part of the flow comes exactly from the Bethe-ansatz magnetization, and the
remaining coefficients are clusters of up to four bubbles (eight kinks) continued analytically in the kink charge to
v = 1. It needs no nine-kink integral, in particular not A9, and shares no input with the compendium (`dual_d1`) or the
independent re-derivation (`indep_d1`).

Paper: printed in the "Checks" paragraph of Sec. 3.2 (since paper 2c5f6b56): \SRCeightMag = 247.38 +- 0.13, with
\SRintegClosedDev = 7e-26 (largest relative difference of C3..C7 from the closed forms) and \SRCeightMagDiff = 2.5e-5
(difference from the compendium's record). Note:
SRI/note, Sec. 2.7 (sec:integ) and Appendix I (app:integ).

Result: **C^SR_8 = 247.381179745789 +- 0.131** (record `results/C8_record_v2.json`), quoted 247.38118 +- 0.13.

* The uncertainty is an empirical numerical estimate, not a standard deviation and not a bound: the linear sum of
  3/4 x 0.174 from the four-bubble coefficient f_301 (|fine - coarse| 0.016 + |fine - radius| 0.022 + validated
  roundoff 0.137), 3.3e-7 from f_202 and 3.6e-15 from all other inputs. It cannot exclude an error common to the
  three runs.
* The same assembly reproduces the closed forms of C^SR_3..C^SR_7 to 7e-26 relative.
* Comparison (made only after the record was frozen and the last code inspection approved): the compendium's record
  247.3812048049935 differs by -2.5e-5; the independent re-derivation 242.825 +- 2.371 (indep_d1) by +4.556, 1.92
  times its own uncertainty. This indicates that the low independent value is the one in error; the re-derivation's
  own input comparison locates the difference in A9[eps^0 l^1].
* Two check criteria were amended after their data were seen (REVIEWS.md); the failing first records stay frozen and
  ship here.

| part | what |
|---|---|
| `code/` | the pipeline, verbatim at commit 8bd5a22: Bethe-ansatz flow (`ba_numeric.py`, `ba_numeric4.py`), one-bubble flow (`one_bubble.py`), the scheme's C_n from flow coefficients (`mscheme_invariants.py`, `mscheme_numeric.py`, `c8_dependency.py`), the sector generator (`cluster_gen.py`), the C++ cluster engine (`cluster_engine.cpp`, `dd.h`, `sha256.h`: sectors, circle/segment continuation in v, double-double arithmetic, OpenMP) and the independent sector checker (`sector_check.cpp`), the step-0 maps (`m*_step0.py`), the gates (`m1_gate.py` ... `m4b_gate.py`, `m4b_cx_check.py`, `m3_sector_check.py`), the assembly (`c8_assemble.py`), provenance and build registry (`provenance.py`, `builds.py`), tests (`test_*.py`), task and batch tools (`m*_chunks.py`, `submit_q.sh`, `*.sbatch`), and the gauge analysis of the s = 1 flow (`series_tools.py`, `normal_form.py`, `linear_action.py`, `rank_exact.py`) |
| `results/` | the frozen records with their registry (`frozen_records.json`) and provenance sidecars, the step-0 maps, the build registry, the designs fixed before data (`m4_inputs/`), the engine inputs (`m3_inputs/`), and the raw engine outputs every record is rebuilt from (`m2_runs/`, `m3_runs/`, `m4_runs/`; each `.out` with its runner fingerprint `.out.fp`) |
| `public/` | `make` targets (`../public.mk`), the replay and test tools, the git stand-in (`gitstub.py`, `git_blobs.json`), the engine source of the f_202 build (`historic/b2ab7c6/`), `SNAPSHOT.sha256`, `REPLAY_FULL.md` |

`make -f public.mk test` (minutes on 8 cores, g++ with OpenMP) and `make -f public.mk replay` (about a minute, one
core) need no cluster. `replay` rebuilds every record from M2 to C8 from the shipped engine outputs with the verbatim
gates and checks them byte for byte, reruns the comparison stage, checks every number of the note's App. I and
compares \SRCeightMag with `../../results/quoted_numbers.json`. The production runs (about 2.7e4 core-hours on the
symmetry cluster) are described in `public/REPLAY_FULL.md` (`make -f public.mk replay-full`).

The public tree has no git history, but the verbatim tools ask git whether design files and a provenance sidecar equal
the blobs committed before the data, and recompute engine build ids from the sources at their commits.
`public/gitstub.py` answers exactly those queries from `public/git_blobs.json` (and fails on any other): this shows
that the files are the committed blobs, not that they were committed in the stated order, which the code inspections
checked on the history (REVIEWS.md).

Assumptions (the note's App. I.8): the same two-coupling description of the gas as the prescription of the compendium
(tested order by order by the analyticity relations), the identification Delta_eps = Delta_- of the note, the
Bethe-ansatz equations of the anisotropic Kondo model and its identification with the gas at s = 1. The calculation
does not test whether the gas, or the dual, describes the critical chain, and at 5e-4 relative it can neither identify
nor certify the rational coefficients of the C8 conjecture.
