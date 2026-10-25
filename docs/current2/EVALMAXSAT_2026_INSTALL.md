# EvalMaxSAT 2026 on the cluster: the official competition binary (milestone 1, 2026-10-25)

> "do option 1, use static binary if you reason we dont need local
> compilation" (user, 2026-10-25)

**Status:** prepared and smoke-tested on the workstation. Not uploaded.
**Note:** N-2026-10-25-f. **Context:** `MSE_PUBLISHED_EXACT_RESULTS.md` §5–§6.

## 1. Why the static binary, not a build [verified]

- **What the record holds.** `solver-EvalMaxSAT.zip` from Zenodo 21358014
  (md5 `58cdc54a…` = Zenodo's) contains:
  - the competition binary `EvalMaxSAT/bin/EvalMaxSAT_bin`, sha256
    `63e46c2d08d7def0…`, ELF x86-64, **statically linked**, built with
    GCC 15.2.0;
  - the launch scripts `EXACT-UW` and `EXACT-W`, both `./EvalMaxSAT_bin $1`,
    so no options were used;
  - the source and `doc/EvalMaxSAT_2026.pdf`.
- **What the binary links:** Boost multiprecision with GMP rationals and
  MPFR, SoPlex and CaDiCaL (from its symbols).
- **What a source build would need:**
  - gcc ≥ 13 (C++23; the authors used 15.2), cmake ≥ 3.14;
  - Boost ≥ 1.65, GMP + GMPXX, MPFR, zlib, all as static libraries;
  - GitHub access for SoPlex v8.0.1.
  - The workstation configure stopped at GMP. A different compiler can also
    change the search path.
- **The binary is what MSE 2026 timed.** Our times then differ from the
  published ones only by hardware, which is the point of using the 2026
  version.

## 2. Same interface as our wrapper [verified: source + workstation smoke]

- `main.cpp` prints the new-format `v` line and exits 30 on an optimum.
- On SIGTERM it prints the incumbent and exits 10.
- It reads plain or gzip `.wcnf` (zlib), **not `.xz`**, so instances must
  be decompressed.
- It no longer prints `c Total time`, so `solver_time_s` is empty. We use
  wall time.

**Workstation smoke** (`oracle_evalmaxsat.py`, the two cluster smoke
instances, records in `tmp/smoke_ems26/`):

| instance | cap | result | time | exit |
|---|---:|---|---:|---:|
| ja-maxham-00000385 | 300 s | optimal 37, verified | 78 s | 30 |
| setcover-sts-data.135 | 30 s | SIGTERM, incumbent 110 verified | 30 s | 10 |

MSE 2023 for the same two: ja-maxham EvalMaxSAT 71 s (optimum 37);
sts-data.135 unsolved by every solver in 1 h, so it still tests the stop.

## 3. Install and smoke on the cluster

**Upload:** the 3 files of `tmp/upload_ems26/` into `~`:
- `solver-EvalMaxSAT.zip`;
- `install_evalmaxsat2026.sh`;
- `ems26__submit_evalmaxsat_mse.sh`.

**What the install does** (shell only; runs nothing):
- checks the zip's md5 against Zenodo's;
- extracts only the binary into `~/evalmaxsat2026/` and checks its sha256;
- replaces `~/cluster_staging_maxsat_evo/scripts/submit_evalmaxsat_mse.sh`.

**The submit script change:** `CHECK_SMOKE` now reads `OUTDIR`, so the 2026
smoke writes to its own folder and does not mix with the old binary's.

**Install safeguards:**
- It refuses a submit script that is none of the committed versions
  (`FORCE=1` overrides).
- It never overwrites an existing backup.

Tested on a mock home with python tripwires:
- dry run, apply and rerun (`HAVE`);
- the older committed version;
- an unknown version (FATAL, then FORCE).

**Commands** (login node, then the smoke runs on compute nodes):

```bash
cd ~
bash install_evalmaxsat2026.sh            # dry run: ZIP_OK, would: ..., REPLACE ...
bash install_evalmaxsat2026.sh --apply    # BIN_OK, REPLACE ..., INSTALL_OK
cd ~/cluster_staging_maxsat_evo/scripts && mkdir -p logs
E=$HOME/evalmaxsat2026/EvalMaxSAT_bin; O=results/smoke_evalmaxsat_2026
DRY_RUN=1 SMOKE=1 OUTDIR=$O EVALMAXSAT_BIN=$E bash submit_evalmaxsat_mse.sh    # checks + the sbatch line
SMOKE=1 OUTDIR=$O EVALMAXSAT_BIN=$E bash submit_evalmaxsat_mse.sh              # 2 tasks, 600 s cap, ~11 min
CHECK_SMOKE=1 OUTDIR=$O bash submit_evalmaxsat_mse.sh                          # after it: SMOKE OK
grep -h bin_sha256 ../$O/task_*.env.json | head -2                             # 63e46c2d08d7def0...
```

**Expected:**
- task 1: verified optimum 37;
- task 2: stopped by SIGTERM, verified incumbent.

## 4. Memory requests for the MSE 2026 manifests (user rule, 2026-10-25)

> "for the manifests - if the data from mse26 reports close to 8/16/32/64
> ram - demand on cluster bigger ram. both for memetic and EvalMaxSat"

**Proposed rule** (for milestone 3; to confirm when the manifests are
built):
- Use the per-instance peak memory **EvalMaxSAT itself** reported in MSE
  2026 (`mem.usage`, KB, in `mse26_exact_*_rawdata.csv`).
- Request the smallest of 8 / 16 / 32 / 64 GB whose 75 % still covers that
  peak. "Close to a bin" thus means within 25 % of it.
- A memout in 2026 (their limit appears to be about 32 GB) goes to 64 GB.
- **Both the EvalMaxSAT and the memetic manifests** are split by this bin.
  Each bin is one `sbatch --mem=…` submission.
- A task that still dies for a system reason is rerun one bin up (notes
  §14).

**What it gives on MSE 2026** [verified: rawdata]:

| track | 8 GB | 16 GB | 32 GB | 64 GB |
|---|---:|---:|---:|---:|
| unweighted (607) | 545 | 20 | 18 | 24 |
| weighted (609) | 529 | 11 | 16 | 53 |

**Why not the maximum over all solvers:** a few generic solvers (CPMpy
HiGHS / OR-Tools) use far more memory. That proxy would put 461 instances
at 64 GB.

**[inference] For the memetic,** EvalMaxSAT's peak is only a proxy of how
heavy an instance is. The memetic's own memory grows with the clause tables
(the lean rule caps the worst), and the escalation rule catches the rest.
