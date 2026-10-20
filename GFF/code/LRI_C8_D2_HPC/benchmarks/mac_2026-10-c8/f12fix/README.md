# F12 fix: the Mac suite (2026-10-05)

Branch `c8` after b82ff65, on the Mac (arm64, anaconda Python 3.10.11, numpy 1.23.5, scipy 1.10.0, pytest 7.1.2),
`C8_ALLOW_NO_L8=1 OPENBLAS_NUM_THREADS=1`. No cluster job ran. No file under `src/` changed.

**The change (F12, `docs/HPC.md`).** `tools/production.py`: `read_member(fd, offset, length)` reads exactly `length`
bytes with `os.pread` in a loop over short reads (no Python buffer, chunks of at most 1 GiB); `stage_graphs` opens the
pack with `os.open`, reads each member with it, checks the same sha256 on the same bytes, writes the same files, and
returns `(root, bytes read, members)`; the claim records the bytes read as its own `staged_members` bytes; the
`claim_io` schema is `c8-d2-claim-io-2`. `tools/stage_runtime.py`'s member copy reads the same way.
`tools/claim_io.py` reports the runs per pack read path (`pack_reads`) and names schema-1 (buffered) records in `notes`.

## Results

`suite_exits.txt`: command, exit status, seconds.

| Command | Result |
|---|---|
| `tests/check_venv.py` | passed (numpy, mpmath, sympy below their minimums on the Mac: reported, not failed without `--strict`) |
| `tests/unit_orchestration.py` | 41 tests, 53 sub-tests, all passed in 422 s (`unit_orchestration.json`); new: `pack_reads` (F12); `staging`, `claim` and `claim_io` extended |
| `tests/test_pipeline.py` | 16/16 |
| `tests/ast_scan.py` | 27 files, 0 findings |
| `gen/test_regress.py`, `gen/test_verify_inventory.py` | 42/42, 25/25 |
| `tests/merge_scale.py --rows 20000` | passed |
| `tests/check_vendored.py`, `--standalone` | 17/17, 14/14 |
| `tests/vendored_isolated.py` | 10/10 (it exports the committed HEAD b82ff65: the vendored assembly, which this change does not touch) |
| `tests/test_delivery_verifier.py`, `tests/check_inputs.py` | passed; 11/11 (2 skipped: no L8 packs on the Mac) |
| `tests/test_profiling.py`, `tests/test_gmp_prefix.py`, `tests/test_numerics_flags.py`, `tests/test_dd_profile.py` | 15, 7, 8, 8 passed |
| `tests/sanitize.py --capture-check` | passed |
| `tests/assembly_checks.py --exact`, `tests/compat_2026.py` | 37/37, passed |
| `tests/verify_result_tamper.py` | 69/69 (`verify_result_tamper.json`) |

**`pack_reads` (new).** A fake pack of 48 members with gaps (every fifth adjacent), 1 B to 1.2 MB (around and above
the 524,288-byte BeeGFS buffer), a block naming 30 of them (five twice). Every `os.pread` counted: 30 reads,
3,748,335 bytes = the members' bytes, each read inside a member; the staged files equal the members and their sha256;
with at most 4,097 bytes per call (929 short reads) the same bytes; `read_member` stops at the end of the file; a pack
cut inside a member is refused with no descriptor left open. Control: the pre-fix read through a `BufferedReader`
with a 524,288-byte buffer over a counting raw file reads 8,388,608 bytes (1.24 extra bytes per staged byte on these
members), exactly the replay model of `benchmarks/symmetry_2026-10-c8/stage5/fix/scripts/claim_io_overread.py`.
On Linux (J-VAL-1) the test also requires rchar across `stage_graphs` to equal the members' bytes; on the Mac there is
no `/proc/self/io` (`st_blksize` here is 4,096).

**`claim` (A-ORC-13 spy).** The spy now also wraps `os.open`, `os.close` and `os.pread`: in both campaigns the claim
opens the pack only with `os.open` (audit mode `None`) and the bytes it reads from it equal its own `staged_members`
bytes. **`staging`:** `stage_runtime.stage` reads exactly the index's members' bytes from the shared pack (117,280).
**`claim_io`:** the record's schema is `c8-d2-claim-io-2`; the tool counts the read paths and names schema-1 records.

**The tests fail on the pre-fix read** (`prefix_sensitivity.txt`): with the buffered read swapped back in, `pack_reads`
and `staging` see no byte through `os.pread`, and `claim` sees the pack opened through `io.open`.

## Owed on the clusters

On symmetry: J-VAL-1 on the fixed commit (`make test`; it runs `pack_reads`' rchar check) and the A-ORC-13 real-Slurm
rerun with the fixed tools (a new export and plan, `fxio.slurm`'s 22-claim subset, about 15 core-hours, then
`tools/claim_io.py`, which must pass with every record `exact`). On Expanse (`docs/HPC.md`, "Sites: symmetry first"):
the J-EXP-1 rerun, the seed sync, the deletion of the 30 obsolete exports.
