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
  scripts/manifest_tier2_memetic.tsv    780 jobs; line N == array task N
  scripts/tier2_oracle.csv              RC2 optima for the join
  scripts/tier2_skipped.txt             instances excluded, with reasons

  sbatch scripts/smoke_tier2_memetic.sbatch
  sbatch --array=1-780%30 scripts/tier2_memetic_array.sbatch

The maxsat conda env needs PyYAML (requirements.txt pins pyyaml>=6.0.1):

  python -c "import yaml; print(yaml.__version__)"

Regenerate the manifest on the workstation, not here:

  python -m src.bench.make_tier2_manifest
