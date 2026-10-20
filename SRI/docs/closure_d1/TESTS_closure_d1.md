# Tests of closure_d1 (2026-10-15)

Simulated export of the whole SRI/ tree (maint/sim_export.sh; 2474 files, 64.46 MiB packed), unpacked on symmetry in
/local1/<USER>/<job>/SRI, acceptance Python (read-only venv): `make test replay PKG=closure_d1`, `make check-values`,
`make note`.

| job | node | result |
|---|---|---|
| 575977 sri-pub-closure-intel | sharedq, Intel Xeon Gold 6148 | test and replay: 4 PASS, 1 INFO (snapshot; 29,523 words, 2,035 nonzero, 0 violations; radial identity n = 1..11; O_g O_g coefficients 1, sqrt2, 1); check-values 27 PASS; check_note PASS |
| 575978 sri-pub-closure-amd | amddebugq, AMD EPYC 7532 | identical |

Mac (Python 3.10 and 3.13): the same table, under 1 s.
