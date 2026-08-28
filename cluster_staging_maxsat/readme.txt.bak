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

The maxsat conda env needs PyYAML (requirements.txt pins pyyaml>=6.0.1):

  python -c "import yaml; print(yaml.__version__)"

Regenerate the manifest on the workstation, not here:

  python -m src.bench.make_tier2_manifest \
      --budgets 900 --out-dir cluster_staging_maxsat/scripts
