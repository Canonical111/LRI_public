CXX ?= g++
# User-adjustable flags. The default command lines are token-identical to C7(3)'s (a6ce987 Makefile:18-19) apart from
# file names (PLAN.md C.8): -O3 then the strict flags, no -march. STRICT cannot be dropped: it is protected against
# command-line override, follows CPPFLAGS/OPTFLAGS/CXXFLAGS, and any user token that would override it (fast-math
# family, other -ffp-contract or -std values, -mfpmath, ...) is refused (tools/buildinfo.py check). On Expanse,
# ~/c8d3/env.sh sets LDFLAGS=-Wl,-rpath,$C8_GMP/lib for every build (HD9).
OPTFLAGS ?= -O3
CPPFLAGS ?=
CXXFLAGS ?=
LDFLAGS ?=
LDLIBS ?=
override STRICT = -std=c++17 -fopenmp -ffp-contract=off -fno-fast-math
PYTHON ?= python3
# Opt-in numerics profiles (PLAN A-FLAG) would be `make gmp NUMERICS=<profile>` -> bin/c8d3_gmp_<profile>; none exists.
ifneq ($(strip $(NUMERICS)),)
$(error NUMERICS=$(NUMERICS): no opt-in numerics profile is implemented (PLAN A-FLAG, Stage 4c); the default build is "exact")
endif
# Boost (C.8, F4): Boost < 1.70 is refused (on Expanse the system /usr/include Boost 1.66 is picked up when the Boost
# include path is missing: the boost modules set only BOOST_ROOT); builds require 1.77 (107700) unless
# BOOST_ACCEPT=<the probed BOOST_VERSION> is given, which the build record keeps. Boost >= 1.86 compiles since the
# A-L18 hunk (kernel.hpp calculate_shared).
BOOST_ACCEPT ?=
BOOST_PROBE = v=$$(printf '\#include <boost/version.hpp>\nBOOST_VERSION\n' | $(CXX) $(CPPFLAGS) -x c++ -E -P - 2>/dev/null | tail -n 1 | tr -d ' '); \
	case "$$v" in ''|*[!0-9]*) echo "C8: cannot find boost/version.hpp with '$(CXX) $(CPPFLAGS)'; load the Boost 1.77 headers (Expanse: source ~/c8d3/env.sh)" >&2; exit 2;; esac; \
	if [ "$$v" -lt 107000 ]; then echo "C8: Boost $$v is refused (< 1.70; on Expanse that is the system /usr/include Boost 1.66: the Boost include path is missing; source ~/c8d3/env.sh or add -I\$$BOOST_ROOT/include)" >&2; exit 2; fi; \
	if [ "$$v" -ne 107700 ] && [ "$$v" != "$(BOOST_ACCEPT)" ]; then echo "C8: Boost $$v: builds require 1.77 (107700); BOOST_ACCEPT=$$v accepts this version and the build record keeps it" >&2; exit 2; fi
GMP_CMD = $(CXX) $(CPPFLAGS) $(OPTFLAGS) $(CXXFLAGS) $(STRICT) -DC7_USE_GMP src/c8d3_integrate.cpp $(LDFLAGS) -lquadmath -lgmp $(LDLIBS) -o bin/c8d3_gmp
DECIMAL_CMD = $(CXX) $(CPPFLAGS) $(OPTFLAGS) $(CXXFLAGS) $(STRICT) src/c8d3_integrate.cpp $(LDFLAGS) -lquadmath $(LDLIBS) -o bin/c8d3_decimal
# The inspector uses the worker's MP backend (gmp), so `--point` reproduces a gmp row's tail_top[0] bit for bit.
INSPECT_CMD = $(CXX) $(CPPFLAGS) $(OPTFLAGS) $(CXXFLAGS) $(STRICT) -DC7_USE_GMP src/c8d3_inspect.cpp $(LDFLAGS) -lquadmath -lgmp $(LDLIBS) -o bin/c8d3_inspect
# make c7ref (C.7, HD9): the unchanged C7(3) worker (reference/src = a6ce987 src/) with a6ce987's command lines,
# token-identical apart from the file names, for the same-toolchain replay gates (A-RPL-1, A-RPL-7 T5).
C7REF_GMP_CMD = $(CXX) $(CPPFLAGS) $(OPTFLAGS) $(CXXFLAGS) $(STRICT) -DC7_USE_GMP reference/src/c7d3_integrate.cpp $(LDFLAGS) -lquadmath -lgmp $(LDLIBS) -o bin/ref/c7d3_gmp
C7REF_DECIMAL_CMD = $(CXX) $(CPPFLAGS) $(OPTFLAGS) $(CXXFLAGS) $(STRICT) reference/src/c7d3_integrate.cpp $(LDFLAGS) -lquadmath $(LDLIBS) -o bin/ref/c7d3_decimal
# Diagnostic builds (C.5; `plan` refuses them: --describe says "diagnostic":true) and test-only builds (A-KER-5,
# A-KER-6 (a)): the default command plus one macro.
PROF_CMD = $(CXX) $(CPPFLAGS) $(OPTFLAGS) $(CXXFLAGS) $(STRICT) -DC7_USE_GMP -DC8_TIER_TIMERS src/c8d3_integrate.cpp $(LDFLAGS) -lquadmath -lgmp $(LDLIBS) -o bin/c8d3_gmp_prof
RATIOHIST_CMD = $(CXX) $(CPPFLAGS) $(OPTFLAGS) $(CXXFLAGS) $(STRICT) -DC7_USE_GMP -DC8_RATIO_HISTOGRAM src/c8d3_integrate.cpp $(LDFLAGS) -lquadmath -lgmp $(LDLIBS) -o bin/c8d3_gmp_ratiohist
NOTAIL_CMD = $(CXX) $(CPPFLAGS) $(OPTFLAGS) $(CXXFLAGS) $(STRICT) -DC7_USE_GMP -DC8_NO_TAIL_FIELDS src/c8d3_integrate.cpp $(LDFLAGS) -lquadmath -lgmp $(LDLIBS) -o bin/diag/c8d3_gmp_notail
ORDERTRACE_CMD = $(CXX) $(CPPFLAGS) $(OPTFLAGS) $(CXXFLAGS) $(STRICT) -DC7_USE_GMP -DC8_ORDER_TRACE src/c8d3_integrate.cpp $(LDFLAGS) -lquadmath -lgmp $(LDLIBS) -o bin/diag/c8d3_gmp_ordertrace
# Sanitizer builds (C.7, A-KER-4): the sanitizer flags plus STRICT; the coverage self-test binary adds the test-only
# macro C8_TEST_UNGUARDED_INDEX (kernel.hpp refuses it without _GLIBCXX_ASSERTIONS).
SAN_FLAGS = -O1 -g -fno-omit-frame-pointer -fsanitize=address,undefined -fno-sanitize-recover=all -D_GLIBCXX_ASSERTIONS -ftrivial-auto-var-init=pattern
GMP_SAN_CMD = $(CXX) $(CPPFLAGS) $(SAN_FLAGS) $(STRICT) -DC7_USE_GMP src/c8d3_integrate.cpp $(LDFLAGS) -lquadmath -lgmp $(LDLIBS) -o bin/c8d3_gmp_san
DECIMAL_SAN_CMD = $(CXX) $(CPPFLAGS) $(SAN_FLAGS) $(STRICT) src/c8d3_integrate.cpp $(LDFLAGS) -lquadmath $(LDLIBS) -o bin/c8d3_decimal_san
INSPECT_SAN_CMD = $(CXX) $(CPPFLAGS) $(SAN_FLAGS) $(STRICT) -DC7_USE_GMP src/c8d3_inspect.cpp $(LDFLAGS) -lquadmath -lgmp $(LDLIBS) -o bin/c8d3_inspect_san
UNGUARDED_SAN_CMD = $(CXX) $(CPPFLAGS) $(SAN_FLAGS) $(STRICT) -DC7_USE_GMP -DC8_TEST_UNGUARDED_INDEX src/c8d3_inspect.cpp $(LDFLAGS) -lquadmath -lgmp $(LDLIBS) -o bin/selftest/c8d3_inspect_unguarded_san
POINTS_GMP_SAN_CMD = $(CXX) $(CPPFLAGS) $(SAN_FLAGS) $(STRICT) -DC7_USE_GMP tests/point_checks.cpp $(LDFLAGS) -lquadmath -lgmp $(LDLIBS) -o bin/test/point_checks_gmp_san
POINTS_DECIMAL_SAN_CMD = $(CXX) $(CPPFLAGS) $(SAN_FLAGS) $(STRICT) tests/point_checks.cpp $(LDFLAGS) -lquadmath $(LDLIBS) -o bin/test/point_checks_decimal_san
NATIVE_SRC = src/kernel.hpp src/quadfast.hpp src/stream.hpp src/identity.hpp src/diagnostics.hpp Makefile
.PHONY: all decimal gmp inspect c7ref profile ratiohist quaddiff test-builds sanitize baseline inputs inputs-l8 link-l8 inputs-mini inputs-inspect check-inputs verify-inputs test test-python test-native test-native-full test-full test-replay test-points test-workflow check-delivery clean gen3 gen3-sanitize
all: gmp inputs
# Distinct filenames make changing the arithmetic backend explicit and auditable.
decimal: bin/c8d3_decimal
gmp: bin/c8d3_gmp inputs
inspect: bin/c8d3_inspect
c7ref: bin/ref/c7d3_gmp bin/ref/c7d3_decimal
profile: bin/c8d3_gmp_prof
ratiohist: bin/c8d3_gmp_ratiohist
# Test-only builds of the class-B and ordering checks (tests/class_b.py, tests/inspect_check.py).
test-builds: bin/diag/c8d3_gmp_notail bin/diag/c8d3_gmp_ordertrace
sanitize: bin/c8d3_gmp_san bin/c8d3_decimal_san bin/c8d3_inspect_san bin/selftest/c8d3_inspect_unguarded_san bin/test/point_checks_gmp_san bin/test/point_checks_decimal_san
# Stage 4b #4's proof (PLAN "Performance plan"; = C62d's R3a, H5): bin/c8d3_quad_differential checks src/quadfast.hpp's
# binary128 add, sub and mul against libgcc bit for bit (random pairs and edge lists); bin/c8d3_quad_ranges records the
# operand ranges of the kernel's binary128 tier through kernel.hpp's own sample(). Built with the worker's flags; never
# workers (no build record, a <binary>.build.txt with the command and compiler). tests/quad_differential.py drives both.
quaddiff: bin/c8d3_quad_differential bin/c8d3_quad_ranges
QUADDIFF_CMD = $(CXX) $(CPPFLAGS) $(OPTFLAGS) $(CXXFLAGS) $(STRICT) tests/quad_differential.cpp $(LDFLAGS) $(LDLIBS) -o bin/c8d3_quad_differential
QUADRANGES_CMD = $(CXX) $(CPPFLAGS) $(OPTFLAGS) $(CXXFLAGS) $(STRICT) -DC7_USE_GMP tests/quad_ranges.cpp $(LDFLAGS) -lquadmath -lgmp $(LDLIBS) -o bin/c8d3_quad_ranges
# A failed build-info step deletes the half-made binary, so the next make rebuilds both (.DELETE_ON_ERROR).
.DELETE_ON_ERROR:
FLAG_CHECK = $(PYTHON) -B tools/buildinfo.py check $(CPPFLAGS) $(OPTFLAGS) $(CXXFLAGS) $(LDFLAGS) $(LDLIBS)
# One rule shape for every native binary: flag check, Boost probe, the command, then bin/<binary>.buildinfo.json
# (tools/buildinfo.py write: command, compiler, Boost, --describe, sha256, backend, libprobe).
define NATIVE_BUILD
	@mkdir -p $(dir $@)
	@$(FLAG_CHECK)
	@$(BOOST_PROBE)
	$(1)
	@$(PYTHON) -B tools/buildinfo.py write $@ '$(CXX)' '$(CPPFLAGS)' '$(BOOST_ACCEPT)' -- $(1)
endef
bin/c8d3_gmp: src/c8d3_integrate.cpp $(NATIVE_SRC)
	$(call NATIVE_BUILD,$(GMP_CMD))
bin/c8d3_quad_differential: tests/quad_differential.cpp src/quadfast.hpp Makefile
	@mkdir -p bin
	@$(FLAG_CHECK)
	$(QUADDIFF_CMD)
	@{ echo "command: $(QUADDIFF_CMD)"; echo "compiler: $$($(CXX) --version | head -1)"; } > $@.build.txt
bin/c8d3_quad_ranges: tests/quad_ranges.cpp $(NATIVE_SRC)
	@mkdir -p bin
	@$(FLAG_CHECK)
	@$(BOOST_PROBE)
	$(QUADRANGES_CMD)
	@{ echo "command: $(QUADRANGES_CMD)"; echo "compiler: $$($(CXX) --version | head -1)"; } > $@.build.txt
bin/c8d3_decimal: src/c8d3_integrate.cpp $(NATIVE_SRC)
	$(call NATIVE_BUILD,$(DECIMAL_CMD))
bin/c8d3_inspect: src/c8d3_inspect.cpp $(NATIVE_SRC)
	$(call NATIVE_BUILD,$(INSPECT_CMD))
bin/ref/c7d3_gmp: reference/src/c7d3_integrate.cpp reference/src/kernel.hpp Makefile
	$(call NATIVE_BUILD,$(C7REF_GMP_CMD))
bin/ref/c7d3_decimal: reference/src/c7d3_integrate.cpp reference/src/kernel.hpp Makefile
	$(call NATIVE_BUILD,$(C7REF_DECIMAL_CMD))
bin/c8d3_gmp_prof: src/c8d3_integrate.cpp $(NATIVE_SRC)
	$(call NATIVE_BUILD,$(PROF_CMD))
bin/c8d3_gmp_ratiohist: src/c8d3_integrate.cpp $(NATIVE_SRC)
	$(call NATIVE_BUILD,$(RATIOHIST_CMD))
bin/diag/c8d3_gmp_notail: src/c8d3_integrate.cpp $(NATIVE_SRC)
	$(call NATIVE_BUILD,$(NOTAIL_CMD))
bin/diag/c8d3_gmp_ordertrace: src/c8d3_integrate.cpp $(NATIVE_SRC)
	$(call NATIVE_BUILD,$(ORDERTRACE_CMD))
bin/c8d3_gmp_san: src/c8d3_integrate.cpp $(NATIVE_SRC)
	$(call NATIVE_BUILD,$(GMP_SAN_CMD))
bin/c8d3_decimal_san: src/c8d3_integrate.cpp $(NATIVE_SRC)
	$(call NATIVE_BUILD,$(DECIMAL_SAN_CMD))
bin/c8d3_inspect_san: src/c8d3_inspect.cpp $(NATIVE_SRC)
	$(call NATIVE_BUILD,$(INSPECT_SAN_CMD))
bin/selftest/c8d3_inspect_unguarded_san: src/c8d3_inspect.cpp $(NATIVE_SRC)
	$(call NATIVE_BUILD,$(UNGUARDED_SAN_CMD))
bin/test/point_checks_gmp_san: tests/point_checks.cpp $(NATIVE_SRC)
	$(call NATIVE_BUILD,$(POINTS_GMP_SAN_CMD))
bin/test/point_checks_decimal_san: tests/point_checks.cpp $(NATIVE_SRC)
	$(call NATIVE_BUILD,$(POINTS_DECIMAL_SAN_CMD))
# gen3 (PLAN.md A.1, C.7): the d=3 rate conversion, its sanitizer builds and the size probe. The command lines are
# fixed (only CXX may change): A.1's command for regenerate_rates; A.1's command plus the sanitizer flags and STRICT for
# regenerate_rates_san; the same plus the test-only macro C8_TEST_UNGUARDED_INDEX for the coverage self-test binary.
# No compiler warning is allowed (A.1): a build that prints one fails and leaves no binary. Each binary gets
# <binary>.build.txt with its exact command and the compiler version. GEN3_BIN and SELFTEST_BIN move the outputs
# (gen3/test_gen3.py builds into a temporary directory).
GEN3_BIN ?= bin/gen3
SELFTEST_BIN ?= bin/selftest
GEN3_SAN_FLAGS = -O1 -g -fno-omit-frame-pointer -fsanitize=address,undefined -fno-sanitize-recover=all -D_GLIBCXX_ASSERTIONS -ftrivial-auto-var-init=pattern
GEN3_CMD = $(CXX) -O2 -std=c++17 -fopenmp -Wall -Wextra gen3/regenerate_rates.cpp -o $(GEN3_BIN)/regenerate_rates
GEN3_SAN_CMD = $(CXX) -O2 -std=c++17 -fopenmp -Wall -Wextra $(GEN3_SAN_FLAGS) $(STRICT) gen3/regenerate_rates.cpp -o $(GEN3_BIN)/regenerate_rates_san
GEN3_UNGUARDED_CMD = $(CXX) -O2 -std=c++17 -fopenmp -Wall -Wextra $(GEN3_SAN_FLAGS) $(STRICT) -DC8_TEST_UNGUARDED_INDEX gen3/regenerate_rates.cpp -o $(SELFTEST_BIN)/regenerate_rates_unguarded_san
SIZE_PROBE_CMD = $(CXX) -O2 -std=c++17 -fopenmp gen3/size_probe.cpp -o $(GEN3_BIN)/size_probe
define GEN3_BUILD
	@mkdir -p $(dir $@)
	$(1) 2> $@.warnings || { cat $@.warnings >&2; rm -f $@ $@.warnings; exit 1; }
	@if [ -s $@.warnings ]; then cat $@.warnings >&2; rm -f $@ $@.warnings; echo "gen3: $@: compiler warnings are not allowed (PLAN.md A.1)" >&2; exit 1; fi
	@rm -f $@.warnings
	@{ echo "command: $(1)"; echo "compiler: $$($(CXX) --version | head -n 1)"; } > $@.build.txt
endef
gen3: $(GEN3_BIN)/regenerate_rates $(GEN3_BIN)/size_probe
gen3-sanitize: $(GEN3_BIN)/regenerate_rates_san $(SELFTEST_BIN)/regenerate_rates_unguarded_san
$(GEN3_BIN)/regenerate_rates: gen3/regenerate_rates.cpp Makefile
	$(call GEN3_BUILD,$(GEN3_CMD))
$(GEN3_BIN)/regenerate_rates_san: gen3/regenerate_rates.cpp Makefile
	$(call GEN3_BUILD,$(GEN3_SAN_CMD))
$(SELFTEST_BIN)/regenerate_rates_unguarded_san: gen3/regenerate_rates.cpp Makefile
	$(call GEN3_BUILD,$(GEN3_UNGUARDED_CMD))
$(GEN3_BIN)/size_probe: gen3/size_probe.cpp Makefile
	$(call GEN3_BUILD,$(SIZE_PROBE_CMD))
# The C8(3) inputs (PLAN B, HD4; C8(3) Stage 2a): the order-8 low-loop files (copied from the vendored inputs_d3/ after
# the HANDOFF hash check, then the vendored prepare_low8.py --d 3 in compare mode), the order-7 files, the L3-L7 packs,
# the inventory and the manifest. From Stage 2b on (the manifest carries the d3 pin) it rebuilds the Stage-2b state from
# the package's own copies (selection.json, h1/, d3/): L7 complete, the L8 rows re-derived from the L8 packs when they
# are present, carried forward (checked) when not. Deterministic; unchanged files are left alone; the L8 packs are
# never written here.
inputs:
	$(PYTHON) -B tools/prepare_inputs.py build
# Stage 2b (PLAN A.2 step 6, J-IN-1): the L8 packs and the complete L7 from the published d=3 payload. Refuses without
# D3PIN (the sha256 of MANIFEST_d3.json, the A.5 gate record's pin), then runs gen3/verify_d3.py --pin before reading any
# member. The L8 packs go to the content-addressed store $(STORE)/packs/<sha256>.pack and are hard-linked into
# inputs/packs/. H1 (default $(STORE)/h1/<H1 sha12>) is the H1 copy; GATE_RECORD (optional) is checked against D3PIN.
inputs-l8:
	@test -n "$(D3PIN)" || { echo "make inputs-l8: D3PIN=<sha256 of MANIFEST_d3.json> is required (the A.5 gate record's pin; PLAN A.2 step 6); nothing was read" >&2; exit 2; }
	@test -n "$(D3PAYLOAD)" || { echo "make inputs-l8: D3PAYLOAD=<the published d3_payload tree> is required" >&2; exit 2; }
	@test -n "$(STORE)" || { echo "make inputs-l8: STORE=<\$$C8_STORE> is required (the L8 pack store)" >&2; exit 2; }
	$(PYTHON) -B tools/prepare_inputs.py l8 --d3payload "$(D3PAYLOAD)" --d3pin "$(D3PIN)" --store "$(STORE)" $(if $(H1),--h1 "$(H1)") $(if $(GATE_RECORD),--gate-record "$(GATE_RECORD)") $(if $(VERIFY_OUTPUT),--verify-output "$(VERIFY_OUTPUT)") $(if $(L8_RECORD),--output "$(L8_RECORD)")
# Hard-link the store's L8 packs (the ones inputs/manifest.json pins) into inputs/packs/ of this export.
link-l8:
	@test -n "$(STORE)" || { echo "make link-l8: STORE=<\$$C8_STORE> is required" >&2; exit 2; }
	$(PYTHON) -B tools/prepare_inputs.py link-l8 --store "$(STORE)"
# The Stage-3 baseline (PLAN A-RPL-8, tag c8-stage3; Stage 3b): bin/baseline/c8d3_{gmp,decimal} and their build records,
# the binaries J-SWEEP-1 measured, copied from $(STORE)/baseline/<sha12>/ (written by slurm/native_job.sh sweep1) and
# verified against reference/baseline_c8_stage3.json; refuses (65) a missing or different file.
baseline:
	@test -n "$(STORE)" || { echo "make baseline: STORE=<\$$C8_STORE> is required (the baseline store)" >&2; exit 2; }
	$(PYTHON) -B tools/baseline.py install --store "$(STORE)"
# tests/fixtures/inputs_mini/ (PLAN B): the 8 smallest real L8 kernels per sector, after make inputs-inspect (needs the
# L8 packs); a generated-data file set, committed.
inputs-mini:
	$(PYTHON) -B tools/prepare_inputs.py mini
# What `plan` checks: every pinned input and the vendored files (C8_ALLOW_NO_L8=1 skips missing L8 packs, test-only).
verify-inputs:
	$(PYTHON) -B tools/prepare_inputs.py verify
# The inspect fields of inputs/inventory.json (PLAN B, A-KER-5; L <= 7 in Stage 3a, L8 in Stage 2b): c8d3_inspect over
# every member of the packs and gen3's size probe (fmax), into inputs/inspect.json; then `make inputs` merges them.
# Runs on Expanse (native build); its outputs are committed as a generated-data commit.
inputs-inspect: bin/c8d3_inspect $(GEN3_BIN)/size_probe
	$(PYTHON) -B tools/inspect_inputs.py build
	$(PYTHON) -B tools/prepare_inputs.py build
# Byte-identical regeneration and the G2a input checks (A-IN-1, A-IN-2, A-IN-4 for L <= 7).
check-inputs:
	$(if $(wildcard inputs/packs/free_L8.pack),,C8_ALLOW_NO_L8=1) $(PYTHON) -B tests/check_inputs.py
# Pure Python, no native build (Stage 3a, PLAN F; about 25 min on the Mac): orchestration with the fake worker and the
# fake Slurm, the fake pipeline end to end, the assembly and statistics checks, the inputs (docs/HPC.md "Tests (Mac)").
test-python: check-inputs
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/unit_orchestration.py
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/blocks_test.py
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/test_pipeline.py
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/test_submit.py
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/test_ledger.py
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/cost_refresh_test.py
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/thru_report_test.py
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/drill_select_test.py
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/prefix_check.py
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/members_test.py
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/inputs_l8_test.py
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/merge_scale.py
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/assembly_checks.py --exact
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/compat_run1.py
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/verify_result_tamper.py
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/test_pilot_report.py
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/design_fallback_test.py
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/test_profiling.py
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/test_opt.py
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/ast_scan.py
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/archived_replay.py
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/test_delivery_verifier.py
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/integration_3a.py
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/native_static.py
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/forced_tiers.py --selftest
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/check_build.py --selftest
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/workflow.py --fake
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/staging.py --fake
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/pack_reads_test.py
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/margin_probe8_test.py
# The native gates (PLAN A-KER, A-RPL; tests/validate.py and the native test drivers). test-native runs the subset
# (the first 8 and 8 heaviest kernels per (sector, L)); test-native-full runs every kernel (J-VAL-2).
test-native: gmp decimal c7ref inspect test-builds
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/validate.py
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/class_b.py
test-native-full: gmp decimal c7ref inspect test-builds
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/validate.py --full
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/class_b.py
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/inspect_check.py
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/check_points.py
test: all test-python test-native
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/workflow.py
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/staging.py
test-full: all decimal test-python test-native-full
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/workflow.py
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/staging.py
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/compat_run1.py
test-points: all decimal
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/check_points.py
test-workflow: all
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/workflow.py
# Replays the two archived d=3 production campaigns (168,528 rows) with the C8 worker in order-7 mode (A-RPL-7).
test-replay: all
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/archived_stream_replay.py
check-delivery:
	$(PYTHON) -B tools/verify_delivery.py --strict
clean:
	rm -f $(addprefix bin/,c8d3_gmp c8d3_decimal c8d3_inspect c8d3_gmp_prof c8d3_gmp_ratiohist c8d3_gmp_san c8d3_decimal_san c8d3_inspect_san)
	rm -f bin/c8d3_quad_differential bin/c8d3_quad_differential.build.txt bin/c8d3_quad_ranges bin/c8d3_quad_ranges.build.txt
	rm -f $(addprefix bin/,ref/c7d3_gmp ref/c7d3_decimal diag/c8d3_gmp_notail diag/c8d3_gmp_ordertrace selftest/c8d3_inspect_unguarded_san test/point_checks_gmp_san test/point_checks_decimal_san)
	rm -f bin/*.buildinfo.json bin/ref/*.buildinfo.json bin/diag/*.buildinfo.json bin/selftest/*.buildinfo.json bin/test/*.buildinfo.json
	rm -f $(addprefix $(GEN3_BIN)/,regenerate_rates regenerate_rates_san size_probe) $(SELFTEST_BIN)/regenerate_rates_unguarded_san
	rm -f $(addsuffix .build.txt,$(addprefix $(GEN3_BIN)/,regenerate_rates regenerate_rates_san size_probe) $(SELFTEST_BIN)/regenerate_rates_unguarded_san)
