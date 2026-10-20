#!/usr/bin/env python3
"""Write H6's HANDOFF_design.json (C62d -> C63d; DECISIONS A4 and the H6-interface line of 2026-10-04).

  write_handoff_design.py --package PKG --commit SHA --des5 DES5_SUMMARY.json --out FILE

DES5_SUMMARY.json is benchmarks/symmetry_2026-10-c8/stage5/des5/des5_summary.json; a compact per-target record of it goes
into real_data_runs. PKG must be a checkout whose tools/ and tests/ equal the commit named (checked: `git diff --quiet
SHA -- tools tests vendor` when PKG is a git work tree).

Every sha256 and byte count is computed here from the package tree at PKG (the c8 work tree at the commit named), so
the record cannot drift from the files. The interface text is the reading of tools/design.py, tools/production.py
(group_of, validate_merged, read_seed_file), tools/accounting.py and tools/ledger.py at those sha256s.
"""
import argparse, hashlib, json, subprocess
from pathlib import Path

RUNTIME = [
    ('tools/design.py', 'the tool (report, freeze, rates)'),
    ('tools/common.py', 'imported by design.py: digest, object_hash/canon, dump, load, utc, ROOT'),
    ('tools/production.py', 'imported by design.py: group_of, validate_merged, verify_base (c8-d2 pilots only), read_seed_file, '
                            'load_inventory, block_name, checkpoint_runtime, the planner constants'),
    ('tools/accounting.py', 'eta_node: account() over the ledger and sacct (--schema-prefix)'),
    ('tools/ledger.py', 'ledger records <prefix>-ledger-1 (check_campaign, read, jobs; WORK_ROLES lane, array, sweep)'),
    ('tools/assemble.py', 'vendored(): the order-8 complex-step Jacobian (jacobians) after the VENDORED.json pin check'),
    ('tools/prepare_inputs.py', 'imported by production.verify_base (c8-d2 pilots only)'),
    ('tools/lanes.py', 'imported lazily by production.py (never on design.py\'s path; in the import closure)'),
    ('tools/build_record.py', 'imported lazily by production.py (never on design.py\'s path; in the import closure)'),
    ('tools/VENDORED.json', 'the pin of vendor/c8_assembly/order8_assembly.py, read by assemble.vendored()'),
    ('vendor/c8_assembly/order8_assembly.py', 'C63d\'s order-8 assembly (H2), byte-identical to LRI_C8_shared/assembly/order8_assembly.py'),
]
TESTS = [
    ('tests/test_pipeline.py', 'A-DES-1/2/6, tails, A-ORC-9, O11 (c8-d3), A-ASM-6, R14/R19, A-FLAG-6; part1 in-process, part2/part3 on fake campaigns'),
    ('tests/pkgcopy.py', 'the scratch package copy the pipeline tests run in (fake bin/c8d2_gmp, inputs_mini)'),
    ('tests/fake_worker.py', 'the fake integrator used by the fake campaigns'),
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def entry(pkg: Path, rel: str, role: str) -> dict:
    f = pkg / rel
    return {'path': rel, 'sha256': sha(f), 'bytes': f.stat().st_size, 'role': role}


def compact_des5(d: dict) -> dict:
    """The J-DES-5 summary reduced to what C63d needs: per target the freeze and the plan's sizes, and the eta_node records."""
    out = {'job': 'symmetry 570114 (sharedq <NODE>, 2026-10-05), export 5d7586e9f1ab (design.py 034b51ee...)',
           'pilot': '<SCRATCH>/c8-d2/sweep2-5d7586e9f1ab (J-SWEEP-2: all 24,173 graphs, both campaigns, 2 x 512 points)',
           'evidence': 'LRI_C8_D2_HPC benchmarks/symmetry_2026-10-c8/stage5/des5/ (README, s5des5.570114.0/, des5_summary.json)',
           'eta_node': {k: round(v['eta_node'], 4) for k, v in d['accounting'].items()},
           'all_caps_hold': d['all_caps_hold'], 'all_plan_directories_deleted': d['all_plan_directories_deleted'], 'targets': {}}
    for t, r in d['targets'].items():
        f, p = r['freeze'], r['plan']
        out['targets'][t] = {'K': f['batches'], 'K_min': f['batches_minimum'], 'predicted_se': round(f['predicted_se_total'], 3),
                             'target_se': f['target_se'], 'allocated_core_hours_at_sweep_eta': round(f['allocated_core_hours_total'], 1),
                             'freeze_wall': f['freeze_time_v'].get('elapsed'), 'freeze_peak_rss_kb': f['freeze_time_v'].get('max_rss_kb'),
                             'plan_tasks': p['tasks'], 'plan_checkpoints': p['checkpoints'], 'plan_indices': p['indices'],
                             'plan_wall_seconds': p['plan_wall_seconds'], 'plan_peak_rss_bytes': p['plan_peak_rss_bytes'],
                             'tasks_sqlite_bytes': p['tasks_sqlite_bytes_total'], 'task_files': p['task_files'], 'manifest_bytes': p['manifest_bytes'],
                             'max_index_wall_seconds': round(p['max_index_wall_seconds']), 'merge_passes_max': p['merge_passes_max'],
                             'projected_files': p['projected_files'], 'all_caps_hold': p['all_caps_hold']}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument('--package', type=Path, required=True); ap.add_argument('--commit', required=True)
    ap.add_argument('--des5', type=Path, required=True); ap.add_argument('--out', type=Path, required=True); a = ap.parse_args()
    pkg = a.package.resolve(); des5 = compact_des5(json.loads(a.des5.read_text()))
    if (pkg / '.git').exists():
        r = subprocess.run(['git', '-C', str(pkg), 'diff', '--quiet', a.commit, '--', 'tools', 'tests', 'vendor'])
        if r.returncode != 0:
            raise SystemExit(f'{pkg}: tools/, tests/ or vendor/ differ from {a.commit}; write the HANDOFF from a checkout of that commit')
    shared = pkg.parent / 'LRI_C8_shared/assembly/order8_assembly.py'
    oa = sha(pkg / 'vendor/c8_assembly/order8_assembly.py')
    doc = {
        'schema': 'c8-design-handoff-1',
        'handoff': 'H6',
        'sender': 'C62d (LRI_C8_D2_HPC)',
        'recipient': 'C63d (LRI_C8_D3_HPC)',
        'date': '2026-10-05',
        'agreed': 'DECISIONS.md A4 (2026-10-03) and the "H6 interface" acknowledgment line (2026-10-04, item 5 of NOTE_C62d_to_C63d_2026-10-04.md)',
        'package': {'path': str(pkg), 'branch': 'c8', 'commit_at_handoff': a.commit,
                    'tool_last_changed_in': '5ddf8ee (Stage 5 G4c fix D1: design.py rates --rule one-step)',
                    'note': 'local commits only (no remote). Every file below is at the sha256 given; vendor it as a tree (see layout).'},
        'tool': entry(pkg, 'tools/design.py', 'the pilot -> Neyman design tool (report, freeze, rates)'),
        'runtime_files': [entry(pkg, r, d) for r, d in RUNTIME],
        'runtime_assembly_equals_shared_copy': {'sha256': oa, 'shared_copy': str(shared), 'equal': shared.exists() and sha(shared) == oa},
        'layout': [
            'Keep the tree: tools/*.py side by side (design.py puts its own directory first on sys.path and imports the others '
            'by module name); ROOT = the parent of tools/ (common.ROOT).',
            'assemble.vendored() reads ROOT/tools/VENDORED.json and imports ROOT/vendor/c8_assembly/order8_assembly.py only '
            'when its sha256 equals the pin there (2127196f...: your own H2 file).',
            'Python >= 3.10 with numpy and scipy (scipy.special.gammaln only in the P8 penalty of report); tested with '
            'numpy 2.3.5 / scipy 1.17.0 (symmetry and Expanse venvs) and numpy 1.23.5 (Mac). Neither design.py nor the '
            'vendored assembly imports mpmath or sympy (the assembly uses numpy and the standard library\'s fractions).',
        ],
        'cli': {
            'report': 'design.py report --pilot RUN [--nested RUN_N] [--bundle B] [--target-se S] [--budget-core-hours B] [--json FILE] '
                      '[--tails-out FILE] [--eta-node X (test-only)] [--test-only] COMMON',
            'freeze': 'design.py freeze --pilot RUN --out BUNDLE (--target-rel R | --target-se S | --budget-core-hours B) [--test-only] [--batches K] '
                      '[--spent-core-hours X] [--total-cap Y] [--seeds-log FILE (default $C8_SEEDS)] [--rates-bundle PROVISIONAL] '
                      '[--eta-node X (test-only)] COMMON',
            'rates': 'design.py rates --pilot RUN --source-bundle B (--rule one-step [--step 0.1] [--band 0.10] [--min-graphs 100] [--boot 1000] | '
                     '--spec FILE) --out PROVISIONAL [--dimension D] [--schema-prefix P] [--half-d H] [--inventory F] [--two-loop F]',
            'COMMON': {'--dimension': 2, '--schema-prefix': 'c8-d2', '--half-d': 1.0, '--two-loop': "the pilot's inputs/two_loop.json (required for another prefix)",
                       '--inventory': "the pilot's inputs/inventory.json (required for another prefix)", '--selection': 'optional selection.json (L8 to-integrate sets)',
                       '--min-points': 4096, '--min-replicates': 32, '--max-replicates': 128, '--variance-margin': 1.5, '--task-seconds': 60.0,
                       '--min-chunk': 256, '--max-task-seconds': 120.0, '--threads': 8, '--checkpoint-tasks': 'max(16 x threads, 256)',
                       '--index-hours': 1.5, '--max-tasks': 50000000, '--max-checkpoints': 200000, '--c8-magnitude': 46000.0,
                       '--impute': 'addends (or median)'},
            'c8_d3_invocation': '--dimension 3 --schema-prefix c8-d3 --half-d 1.5 --two-loop inputs/two_loop.json --inventory inputs/inventory.json '
                                '--selection inputs/selection.json (your E.5); the three reuse parameters must agree (prefix c8-d<D>, half-d D/2)',
            'exit_codes': {'0': 'done (freeze/rates print a JSON summary; report prints the table)', '2': 'refused (ValueError/FileExistsError; '
                           'the message names the reason; nothing is published)', '1': 'unexpected error (traceback)'},
        },
        'schema_prefix_rule': {
            'campaign_manifest': '<prefix>-production-1, with "dimension" D and "order" 8',
            'group_config': '<prefix>-group-1', 'merged': '<prefix>-merged-1', 'ledger': '<prefix>-ledger-1 (every record)',
            'accounting': '<prefix>-accounting-1', 'bundle': '<prefix>-design-1 (design.json and design_meta.json)',
            'rates_map': '<prefix>-rates-1', 'report': '<prefix>-design-report-1',
            'rule': 'the prefix names the pilot campaign\'s own schema; a ledger record of another prefix is refused (freeze/report exit 2, '
                    'accounting.py exit 2, ledger.py exit 64), never skipped. A c8-d3 campaign is accounted from its own c8-d3-ledger-1 ledger. '
                    'A c8-d2 plan refuses a bundle of another prefix.',
        },
        'input_interface': {
            'how_a_foreign_pilot_is_read': 'For prefix != c8-d2, design.py reads the campaign through this interface only (no verify_base): '
                                           'manifest, group configs at their manifest pins, validated merged tables, its own ledger, and the '
                                           'inputs you pass, which must be the files the pilot\'s inputs manifest lists.',
            'RUN/manifest.json': {'schema': '<prefix>-production-1',
                                  'fields_read': ['schema', 'dimension', 'order', 'seed', 'executable_sha256', 'numerics', 'rates_identity',
                                                  'inputs_manifest_sha256', 'test_only', 'backend', 'threads', 'allocation',
                                                  'groups[] {name, sha256 (of groups/<name>/config.json)}',
                                                  'jobs[] {group, shard, blocks} (accounting: the checkpoint scan)'],
                                  'manifest_sha256': 'sha256 of the file bytes (merged.json must name it)'},
            'RUN/groups/<name>/config.json': {'schema': '<prefix>-group-1', 'read_at': "the manifest's groups[].sha256 pin (read_verified)",
                                              'fields_read': ['schema', 'campaign (a|b)', 'sector (free|power)', 'L (3..8)', 'replicates',
                                                              'counts {graph id as string: points per replicate}'],
                                              'config_hash': 'object_hash(config) = sha256 of json.dumps(config, sort_keys=True, separators=(",", ":"), allow_nan=False)'},
            'RUN/groups/<name>/merged.json': {'schema': '<prefix>-merged-1', 'required': 'every group merged (else refused: "not merged")',
                                              'checks': ['complete is true', 'manifest_sha256 == sha256(manifest.json)', 'config_hash == object_hash(config)',
                                                         'sector, L, campaign equal the config', 'rates_identity, numerics equal the manifest',
                                                         'payload_sha256 == object_hash(merged.json without payload_sha256)',
                                                         'graph_replicates_sha256, graph_tails_sha256, graph_costs_sha256 == sha256 of the three CSV files',
                                                         'len(batches) == replicates == config.replicates'],
                                              'fields_used': ['row_seconds_sum and thread_seconds_sum (eta_omp,g = row/thread, capped at 1)',
                                                              'thread_seconds_sum (accounting: busy thread-seconds)']},
            'RUN/groups/<name>/graph_replicates.csv': {'header': 'replicate,graph,jet_0,...,jet_{2(9-L)-1}',
                                                       'rows': 'one per (replicate, graph); the jets of that graph summed over its points (floats as text)',
                                                       'use': 'sigma_g^2 = n_g Var_rep(J_8 . jet_g) at the pilot means; the pilot means (equal-weight campaigns); report statistics; rates rule'},
            'RUN/groups/<name>/graph_costs.csv': {'header': 'graph,points,row_seconds,tasks,quad,mp',
                                                  'use': 'graph and row_seconds (summed over the replicates): c_g = row_seconds / (replicates x points per replicate)'},
            'RUN/groups/<name>/graph_tails.csv': {'header': 'replicate,graph,points,tail_sum,tail_argmax,tail_n,top_1,...,top_16',
                                                  'use': 'graph, points, tail_n, top_1..top_<tail_n> (|t| descending), tail_sum: the Hill xi, largest share, '
                                                         'screen/confirm (L8 only), undefined reasons (report)'},
            'RUN/submissions.jsonl': {'schema': '<prefix>-ledger-1 (one JSON object per line)',
                                      'fields_read': ['schema', 'jobid', 'role (sweep|plan|lane|array|merge)', 'restart_count', 'type (attempt|note: not a job)',
                                                      'array (the array spec, role array)'],
                                      'written_by': 'tools/slurm_submit.py, or ledger.py register RUN --role sweep|plan [--schema-prefix P] for self-registered work'},
            'RUN/groups/<name>/checkpoints/s<shard:06d>_p<part:06d>.json': {
                'fields_read': ['runtime.fingerprint.slurm {SLURM_JOB_ID, SLURM_ARRAY_JOB_ID, SLURM_ARRAY_TASK_ID, SLURM_RESTART_COUNT} (the first key of the file)',
                                'native {integration_seconds, threads} (only for groups without merged.json; not on design.py\'s path, which requires every group merged)'],
                'rule': 'a checkpoint naming a job not in the ledger stops freeze/report ("allocation unknown"); checkpoints without a Slurm id only for --test-only'},
            'slurm_commands': 'accounting.py runs sacct -X --duplicates for the ledger jobs (ElapsedRaw x AllocCPUS / ThreadsPerCore from scontrol show node); '
                              'incomplete accounting makes eta_node unavailable and freeze/report refuse',
            'inputs_for_another_prefix': {
                '--inventory': 'inventory.json: {sector: {str(L): [rows {id, primitive (L8 free), addends or cost}]}}; every graph gets a base count',
                '--two-loop': 'two_loop.json with key "B2" (the B2 jet)',
                '--selection': 'selection.json with key "L8": {free: [ids], power: [ids]} (optional; restricts L8)',
                'pin_rule': 'the manifest.json beside --inventory must have sha256 == the pilot manifest\'s inputs_manifest_sha256 and list the sha256 '
                            'of inventory.json, two_loop.json (and selection.json when given) under its "sha256" key',
            },
            'seed_log': '--seeds-log or $C8_SEEDS: a c8-d2-seeds-1 log {"seeds": [{"seed": int, ...}]} or a JSON list of integers '
                        '(production.read_seed_file); the bundle forbids the pilot seed and every listed seed',
        },
        'outputs': {
            'bundle': {'layout': ['design.json', 'design_meta.json', 'counts/<campaign>_<sector>_L<L>.txt (one line "<graph> <base count>" per inventory graph, 24 files)'],
                       'publication': 'atomic (staging directory + rename); an existing --out is refused (never overwritten)',
                       'design.json': ['schema <prefix>-design-1', 'kind design', 'strata {13 strata: sector, L, primitive, s, V1, C1, graphs, piloted}',
                                       'replicates {<sector>_L<L>: r}', 'batches K, batches_minimum', 'predicted {variance_per_batch, se_raw_per_batch, se_raw_total, '
                                       'se_total, cost_per_batch_core_hours, cost_total_core_hours, imputed_variance_share, variance_margin}',
                                       'caps {ok, tasks_per_campaign, checkpoints, max_replicates, predicted_max_task_seconds, worst_task, '
                                       'predicted_max_index_wall_seconds, task_ok}', 'eta_node', 'eta_omp {<group>: value}'],
                       'design_meta.json': ['schema', 'kind meta', 'test_only', 'provisional false', 'design_sha256', 'counts_sha256 {file: sha256}',
                                            'pilot {campaign, manifest_sha256, seed, executable_sha256, numerics, rates_identity, inputs_manifest_sha256, '
                                            'test_only, backend, threads, allocation, two_loop_sha256, accepted_tool_changes, dimension, schema_prefix, half_d, verified_by}',
                                            'numerics', 'rates_identity', 'inputs_manifest_sha256', 'executable_sha256', 'backend', 'forbidden_seeds', 'batches',
                                            'target {se, rel, c8_magnitude}', 'budget_core_hours', 'spent_core_hours', 'total_cap', 'eta_node', 'eta_node_source',
                                            'imputed {variance_share, graphs, impute}', 'predictions', 'parameters {dimension, schema_prefix, half_d, two_loop, '
                                            'min_points, min_replicates, max_replicates, variance_margin}', 'rates_bundle', 'rule', 'frozen_utc'],
                       'identity': 'the sha256 of design_meta.json is the bundle identity (production.py plan --design records it)'},
            'provisional_rates_bundle': 'design.py rates: rates.json (<prefix>-rates-1) + design_meta.json with provisional true, rates_identity = '
                                        'sha256(rates.json), source_design_meta_sha256, rate_rule; no counts, no design.json (every plan refuses it)',
            'report_json': '<prefix>-design-report-1: targets[] (target_rel, target_se, batches, predicted_se_with_margin, predicted_se_raw, '
                           'allocated_core_hours, replicates, s, imputed_variance_share), extra[], strata{}, sector_P8, tails{}, bundle, eta_node, eta_source',
            'tails_csv': 'campaign,sector,L,graph,points,replicates,xi_hat,largest_share,use,status',
        },
        'tests': {
            'files': [entry(pkg, r, d) for r, d in TESTS],
            'run': 'from a git archive export of the commit (the tests need the whole package: tests/pkgcopy.py builds a scratch copy): '
                   'python3 -B tests/test_pipeline.py --only part1,part2 --output FILE (part3 adds the non-test R7 chain); Mac: C8_ALLOW_NO_L8=1',
            'c8_d3_coverage': [
                {'test': 'A-DES-6_d3_vendored_B2_subsample_imputation_nested_alpha (part1)',
                 'covers': 'freeze_core of a synthetic d = 3 pilot with the vendored inputs_d3/two_loop.json at the HANDOFF_assembly sha256 '
                           '(--dimension 3 --half-d 1.5 --schema-prefix c8-d3): a c8-d3-design-1 bundle of 24 count files; refusals of '
                           'mismatched dimension/half-d/prefix; the 1/8 L8 subsample imputation (imputed share = the hand value); nested alpha within 0.02'},
                {'test': 'O11_C8-3_command_line_freeze_report_rates_on_a_c8-d3_pilot_its_c8-d3_ledger_eta_node_schemas_follow_prefix_refusals (part2)',
                 'covers': 'the command line on a c8-d3 view of a merged fake pilot (schemas c8-d3-production-1/-group-1/-merged-1, dimension 3, '
                           'every pin re-made, its own inputs manifest, its own c8-d3-ledger-1 ledger registered with ledger.py --schema-prefix c8-d3): '
                           'freeze and report take eta_node from that ledger through accounting.py (= the c8-d2 value); the J8 differs from the d = 2 '
                           'one; rates on it; refusals: a c8-d2 ledger under the c8-d3 campaign, one c8-d2 record in a c8-d3 ledger, a c8-d3 ledger '
                           'under a c8-d2 campaign, registration with the wrong prefix, a d = 2 plan of the c8-d3 bundle'},
            ],
            'all_sub_tests': ['A-DES-1_full_size_freeze_counts_replicates_budget_infeasible_K_atomic_seeds_caps', 'A-DES-2_report_table_and_independent_bundle_SE',
                              'A-DES-6_d3_vendored_B2_subsample_imputation_nested_alpha', 'A-DES_tails_L8_thresholds_L7_diagnostics_undefined_sector_P8_L8_4096',
                              'A-FLAG-6_G4c_one_step_rule_branches_W_r_bootstrap_hand_values_refusals', 'O09_sweep_finalization_resumes_reuses_its_model_refuses_another',
                              'A-ORC-9_bootstrap_sweep_ledger_accounting_eta_node_design_allocation_unknown', 'A-ORC-9_local_checkpoints_accepted_only_by_test_only_freeze',
                              'A-DES-2_on_the_fake_pilot_bundle_recomputed_independently',
                              'O11_C8-3_command_line_freeze_report_rates_on_a_c8-d3_pilot_its_c8-d3_ledger_eta_node_schemas_follow_prefix_refusals',
                              'A-ASM-6_combine_final_partial_chi2_hand_verify_result_and_rejections',
                              'A-FLAG-6_rates_per_graph_spec_equal_refused_source_unchanged_tool_change_recorded',
                              'A-FLAG-6_sweep_under_the_map_feeds_a_fresh_freeze_recomputed_another_map_refused',
                              'A-FLAG-6_G4c_rates_rule_one_step_cli_map_record_recomputed_refusals',
                              'R14_R19_provisional_bundle_map_measurement_fresh_freeze_recomputed_source_allocation_misses',
                              'A-FLAG-6_G4c_non_test_plan_accepts_fresh_R7_bundle_with_approval_and_map_cost_model_refuses_without'],
            'last_results': [
                'Mac (numpy 1.23.5), 5ddf8ee: 16/16 (benchmarks/expanse_2026-10-c8/stage5/g4cfix/mac/)',
                'symmetry J-VAL-1 570027 (amdq <NODE>, numpy 2.3.5), export 5d7586e9f1ab: 16/16, parts 1-3 '
                '(benchmarks/symmetry_2026-10-c8/stage5/s5val1.570027.0/records/test_pipeline.json)',
                'Expanse J-EXP-1 follow-up 54676898, export 07ff5c1975e5 (= 5d7586e tools): test_pipeline exit 0 '
                '(benchmarks/expanse_2026-10-c8/stage5/exp/s5eexp1b.54676898.0/exits.txt)',
            ],
        },
        'real_data_runs': {
            'J-SMK-3 (symmetry, 2026-10-05)': 'freeze --test-only on the merged L8 smoke with sacct accounting, plan --design, run, merge, assemble, '
                                              'combine --partial and final (benchmarks/symmetry_2026-10-c8/stage5/README.md)',
            'J-DES-5 (symmetry, 2026-10-05)': des5,
        },
        'known_issues': [
            'F11 (found by J-DES-5, not fixed in this design.py): split() gives a (sector, L) the replicates of its LARGEST stratum multiplier. '
            'The free L8 primitives are their own cheap stratum; at a loose target their multiplier can be several times that of the other '
            'free L8 graphs (1e-3 on C62d\'s sweep: 176.8 against 35.1), so the dominant stratum runs at r = 128 where 32 would do: the 1e-3 '
            'bundle over-delivers (SE 32.6 against 46) at about 2.3x the cost of r taken from the group\'s costliest stratum. Tighter targets '
            '(5e-4 and below) are within 1.10x of the continuous Neyman optimum. The bundle\'s predicted SE is right; only its cost is high. A '
            'fix changes design.py, and C62d will then send a new HANDOFF version with the new sha256.',
            'The G5 fixes owed in C62d\'s package (F7 lane cleanup, F8 recovery merge, F9 rchar logging) change production.py, lanes.py and '
            'assemble.py, which are in design.py\'s runtime closure above (production.py and assemble.py are imported on its path). Their '
            'sha256s will change; C62d will re-issue this HANDOFF after its Stage-6 inspection. The interface below is not expected to change.',
        ],
        'notes': [
            'eta_node comes from the pilot\'s own ledger over the work roles (lane, array, sweep): a short or tail-heavy job gives a low eta_node '
            'and a high allocated cost (J-SWEEP-2 on symmetry: 0.306; the J-SMK-4 lane campaign: 0.915). freeze has no override outside --test-only.',
            'With 2 replicates per graph (a sweep), kurtosis, skewness, max|z| and P8 are undefined (None) in report; a pilot with 8 replicates gives them.',
            'design.py pins the numerics and rates identity of its pilot: a plan under another profile or map refuses the bundle.',
            'The tests above need C62d\'s whole package (fixtures, fake worker); vendoring design.py and its runtime files is enough to run it on your campaigns.',
        ],
    }
    a.out.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n')
    print(a.out, sha(a.out))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
