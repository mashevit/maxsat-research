# Census rows computed on the workstation (2026-10-28)

The 27 files of cluster census tasks 19 and 31 from the file each task was
stuck on (the reference kernel ran > 40 min there) to the end of the task.
Fetched from Zenodo 21358014 by HTTP range request, sha256 equal to
`../mse26_unpack/mse26_content.tsv` (27/27, and hard / soft / weighted counts
equal), censused with `scripts/mse26_census.py` at the fast kernel
(`kernelize`, COMPILED_MEMETIC_PLAN.md §10), `KERNEL_MAX_MIB = 50` instead of
100 (workstation memory), 300 s kernel cap. Timing columns are workstation
times. Merge with the cluster rows (`rows/` from the cluster) on the
workstation; the cluster rows win for any hash present in both.
