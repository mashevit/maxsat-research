Cluster staging tree for the MaxSAT experiments.

Rsync this whole directory (including data/, which is gitignored but required)
to ~/maxsat-lab on the cluster, then submit from ~/maxsat-lab/scripts.

  rsync -av --exclude '__pycache__' cluster_staging_maxsat/ <user>@<cluster>:~/maxsat-lab/


RC2 hardness profiling (done -- see docs/RC2_STATUS.md)
-------------------------------------------------------
  scripts/full_mse23_array.sbatch          cap 600,  manifest_mse23_full.txt
  scripts/full_mse23_array_cap1800.sbatch  cap 1800, manifest_mse23_full.txt
  scripts/full_uuf250_array.sbatch         cap 900,  manifest_uuf250_1000c.txt
  scripts/full_uuf_array.sbatch            cap 600,  manifest_uuf_diff.txt

SATLIB .cnf files must have the trailing %/0 marker stripped before staging,
otherwise PySAT parses it as two empty clauses and the optimum shifts by 2:

  sed -i '/^%$/,$d' *.cnf


Tier-2 memetic EA (ready to run -- see docs/TIER2_MEMETIC_PLAN.md)
------------------------------------------------------------------
  scripts/smoke_tier2_memetic.sbatch    5 tasks, 10 s budget -- run this first
  scripts/tier2_memetic_array.sbatch    the array driver
  scripts/manifest_tier2_memetic.tsv    390 jobs; line N == array task N
  scripts/tier2_oracle.csv              RC2 optima for the join
  scripts/tier2_skipped.txt             instances excluded, with reasons

  sbatch scripts/smoke_tier2_memetic.sbatch
  sbatch --array=1-390%30 scripts/tier2_memetic_array.sbatch

The manifest is now a single 900 s budget (was 60 s + 300 s), which is why the
array is 390 tasks and --time is 00:20:00 rather than 00:15:00: a 900 s budget
plus the 60 s default GRACE does not fit in a 15 min wall limit.

To make each run stop the moment it reaches its oracle optimum -- turning
wall_time_s into a real time-to-optimum instead of "the budget was spent":

  sbatch --array=1-390%30 --export=ALL,STOP_AT_ORACLE=1 \
         scripts/tier2_memetic_array.sbatch

That is opt-in on purpose: an oracle-terminated run is a BENCHMARKING mode, not
a solver mode. Worst case without it is 26 x 3 x 900 x 5 = 351 000 solver-s
(~97.5 h, ~3.5 h wall at %30); with it, far less -- the EA reached the optimum
in 8.8 s on uuf250-0100 where RC2 needed 219 s.

IMPORTANT: src/evo/memetic.py and src/cli/run_memetic_shard.py in this tree are
INTENTIONALLY ahead of the repo copies under src/ (target-cost stop, 2026-08-05).
The §2.2 byte-identity diff loop will report DIFFERS for exactly those two files
and that is expected. Read DIVERGENCE.md before mirroring or re-copying either.


Tier-2 local-multistart ablation arms (the no-EA controls)
-----------------------------------------------------------------
  src/evo/multistart.py                             the solver, both arms
  scripts/make_local_multistart_manifest.py         manifest generator, both arms
  scripts/tier2_local_multistart_array.sbatch       the array driver, both arms

  configs/tier2/local_multistart_deeppolish.yaml    init: uniform
  scripts/manifest_tier2_local_multistart.tsv       130 jobs; line N+1 == array task N
  scripts/submit_tier2_local_multistart.sh          counts rows, derives the range

  configs/tier2/local_multistart_jw_deeppolish.yaml init: jw
  scripts/manifest_tier2_local_multistart_jw.tsv    130 jobs; same 26 instances, same 5 seeds
  scripts/submit_tier2_local_multistart_jw.sh       same, + MANIFEST/OUTDIR for this arm

The control for "does memetic_deeppolish need its evolutionary component?".
Independent random restarts, each polished by the SAME operator the EA applies
to every child (evo.operators.short_polish), stopping when the certified RC2
optimum is reached. 26 tier-2 instances x 5 seeds = 130 tasks at 900 s, per arm.

THREE ARMS, TWO FACTORS. The arms differ in exactly one knob each, so each
pairwise difference names one cause:

  memetic_deeppolish  - local_multistart_jw   population / crossover / EA
  local_multistart_jw - local_multistart      JW initialisation
  memetic_deeppolish  - local_multistart      the whole package

The middle arm is the reason the first difference is attributable to the
evolutionary operators at all: memetic_deeppolish seeds its population from the
Jeroslow-Wang prior, so memetic - local_multistart (uniform) confounds the
operators with the seeding. local_multistart_jw holds the seeding constant.

Its seeding is not a lookalike: multistart.py calls
Population._new_assign_from_priors, the exact function Population.init_seeds
builds the EA's initial population with, once per restart off the run's own RNG.
It is a stochastic biased draw, NOT one deterministic JW assignment -- jw_priors
clips every prior into [0.05, 0.95] so no variable is ever pinned. A
deterministic seed would silently reduce the arm to a single polish repeated
until the budget ran out. tests/test_local_multistart.py section 8 asserts both.

  python3 scripts/make_local_multistart_manifest.py            # uniform arm
  python3 scripts/make_local_multistart_manifest.py --arm jw \
      --verify-against scripts/manifest_tier2_local_multistart.tsv

--verify-against re-checks, joined on instance_sha256 rather than on the
instance path, that both arms carry the same oracle_cost for all 26 instances.
Exits 3 on any mismatch: an ablation whose arms were given different oracles
measures nothing. Last run clean, 26/26.

  bash scripts/submit_tier2_local_multistart.sh       # uniform; counts rows, submits
  bash scripts/submit_tier2_local_multistart_jw.sh    # jw
  DRY_RUN=1 bash scripts/submit_tier2_local_multistart.sh   # print, don't submit

Both submitters drive the SAME tier2_local_multistart_array.sbatch, unchanged --
it reads MANIFEST and OUTDIR from the environment, and the jw submitter passes
them via --export (OUTDIR=results/tier2_local_multistart_jw/tasks). One array
driver, so the arms cannot drift in --time, GRACE or STOP_AT_ORACLE; a forked
copy could, and any such drift would look like a seeding effect. Consequently
the jw submitter REFUSES a passthrough `--export`: sbatch honours the last one,
so yours would drop MANIFEST/OUTDIR and run the jw array against the uniform
manifest, into the uniform arm's results tree. Set the variables in the
environment instead (STOP_AT_ORACLE=0 bash scripts/submit_..._jw.sh). It also
refuses a manifest whose config_id column is not local_multistart_jw_deeppolish.

or, equivalently:

  cd scripts && sbatch --array=0-129%30 tier2_local_multistart_array.sbatch
  cd scripts && sbatch --array=0-129%30 \
      --export=ALL,MANIFEST=scripts/manifest_tier2_local_multistart_jw.tsv,\
OUTDIR=results/tier2_local_multistart_jw/tasks \
      tier2_local_multistart_array.sbatch

Note the 0-based array, unlike the 1-based tier2_memetic_array.sbatch: task N
reads manifest line N+1. STOP_AT_ORACLE also defaults to 1 here, not 0 --
"restart until the optimum is reached" is this baseline's definition, not an
opt-in benchmarking mode. To compare against the memetic arm, that arm must
have been run with STOP_AT_ORACLE=1 as well.

Optional total-flip cutoff for a flip-budget comparison that does not depend on
machine speed (off by default; the 900 s wall budget still applies):

  sbatch --array=0-129%30 --export=ALL,MAX_TOTAL_FLIPS=5000000 \
         tier2_local_multistart_array.sbatch

Smoke it first -- one instance, short budget, no SLURM:

  python -m src.cli.run_memetic_shard \
      --instance data/unsat_uuf_diff/uuf250-03.cnf \
      --config configs/tier2/local_multistart_deeppolish.yaml \
      --config-id local_multistart_deeppolish \
      --seed 1 --budget-s 20 --grace-s 15 \
      --oracle-cost 1 --stop-at-oracle \
      --tier T2a --rc2-run uuf_diff_unsat --job-id smoke_t2lms \
      --out results/tier2_local_multistart_smoke/smoke_t2lms.jsonl

Swap the two --config/--config-id values for the jw arm. A 20 s smoke on
uuf250-0100 (oracle 1, not a measurement) gave cost 3 uniform / cost 2 jw /
cost 1 memetic, 40 restarts for each multistart arm -- the three arms are
distinguishable end to end and combine_tier2.py keeps them apart.

src/bench/combine_tier2.py needs no change for the third arm: it groups by
config_id throughout, so three arms in one shard directory produce three
summary.csv rows and three by_instance.csv rows with no pooling and nothing
dropped. Verified on a mixed three-config_id shard directory, integrity clean.

CAVEAT: under this preset the polish is bound by ls.time_limit_s (0.5 s, ~5,300
iterations on uuf250-03), not by the 12,500-flip ceiling. memetic_deeppolish has
the identical property so the arms stay comparable, but neither is
bit-reproducible across machines. See the docstring in src/evo/multistart.py.

The maxsat conda env needs PyYAML (requirements.txt pins pyyaml>=6.0.1):

  python -c "import yaml; print(yaml.__version__)"

Regenerate the manifest on the workstation, not here:

  python -m src.bench.make_tier2_manifest \
      --budgets 900 --out-dir cluster_staging_maxsat/scripts
