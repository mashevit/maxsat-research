# Provenance of `cluster_staging_maxsat_hard/`

**Created:** 2026-10-11, milestone H1 of
[`docs/current/HARD_CLAUSE_SOLVER_PLAN.md`](../docs/current/HARD_CLAUSE_SOLVER_PLAN.md).

**Purpose.** The staging tree for the hard-clause solver. It will add:
- Glucose initialisation on the hard clauses;
- operators that keep hard feasibility through polish, crossover and
  mutation;
- a `hard_multistart` arm built from the same components.

Its first instances are MSE 2023 / 2024 (`docs/current/MSE_EVALMAXSAT_3600.md`).
It is a **new algorithm**: its rows never share a stratum or a table with the
current solver's rows. The original tree `cluster_staging_maxsat/` is not
edited by this work.

## Source of the copy

- Repository commit **`4100ea7`** (`main`, clean working tree for
  `cluster_staging_maxsat/`, pushed to `origin`).
- Copied from `cluster_staging_maxsat/` at that commit. "Up-to-date solver"
  means the staging `src/`, which is ahead of the repo `src/`:
  - target-cost early stop;
  - opt-in deadline clipping;
  - new-format WCNF parsing;
  - `evo/multistart.py`;
  - `impl: v2` (incremental WalkSAT, `sat/walksat_v2.py`, `evo/impl_v2.py`);
  - the EvalMaxSAT driver with SIGTERM stop.

| copied | not copied |
|---|---|
| `src/` (all `.py`), `configs/tier2/` (12 configs), the solver and parser tests (`test_cnf_legacy_formats`, `test_cnf_new_format`, `test_walksat_v2`, `test_local_multistart`, `test_oracle_evalmaxsat`), the memetic runner array `scripts/tier2_memetic_array.sbatch` and its submit wrapper `scripts/submit_m2_memetic.sh` | `data/`, `results/`, calibration / RC2 / EvalMaxSAT scripts and manifests, the calibration-specific tests (`test_m2_prep`, `test_calib_*`, `test_rc2_row_state`, `test_satlib_bench_intake`), `*.bak`, `__pycache__` |

## Checks at creation [verified]

- **Byte identity:** all 43 copied files compared equal to their sources
  (`cmp`). `diff -rq` on `src/` (excluding `__pycache__`, `*.bak`) and on
  `configs/tier2/` reports no difference.
- **Tests, run from inside this tree** (`python -m pytest tests -q`):
  **111 passed, 12 skipped.** Every skip is a missing instance or
  manifest, because this tree has no `data/` yet: 5 MSE 2023 parser cases,
  1 live EvalMaxSAT SIGTERM case, 3 multistart-manifest cases, and their
  parametrised variants.
- **Imports:** `src.sat.cnf` and `src.cli.oracle_evalmaxsat` resolve to this
  tree, and `test_walksat_v2` / `test_local_multistart` put this tree's
  `src/` first on `sys.path`.

From here on this tree is allowed to diverge from its source. Every change is
recorded below, with its date and milestone. The list of file checksums at
creation is at the end; run `sha256sum -c` against it to see which files have
changed since.

## Changes since creation

*(none yet; H2 starts here)*

## sha256 at creation (commit 4100ea7)

```
dc1c0242205d09f608a812b2457a8f7d13a22de0854401c4bba87a40c28cd577  configs/tier2/local_multistart_deeppolish.yaml
c879020c94924bffbb9fd2a0fcbf6dbd8cc9a5377f3308380a78779e0384f85c  configs/tier2/local_multistart_jw_deeppolish.yaml
42b7ea6cd3c6217ada742ef0a8ca64ab7f907f8f54051b0e8a57478985345436  configs/tier2/local_multistart_jw_longpolish.yaml
7f5e989f9585d6605d59b22e5a5991251ba7f61730a5138101760be8bd01ebd2  configs/tier2/memetic_base.yaml
cf6c3ad9665a9d64571d009e71f95df6f3ee530d25b7991a5f3c3e169c034990  configs/tier2/memetic_deeppolish.yaml
d5c7479c4767761bc88b2c0fe229cbddb1ed58c7f4237402e5cb4db3ebac8118  configs/tier2/memetic_deeppolish_p10_ls2p5.yaml
9a9609302b4f45d054cf2466d563f7aaf020ca19cb141cd61f416f00467e0280  configs/tier2/memetic_deeppolish_p10_ls3p5.yaml
07771a4659a8a7c75145d3ad40cd82748e3a789ab47a4fc004f0b3fd6ad18657  configs/tier2/memetic_deeppolish_p40_ls0p5_clip.yaml
71bebcdb485b23a49ad8ad97265b15e4b0e518f5b74de99b3286f5659e1febf6  configs/tier2/memetic_deeppolish_p40_ls2p5.yaml
27c7cceea5a36aeea6d510b720034dc8f65739c96d9234aa0da7aa359a70a702  configs/tier2/memetic_deeppolish_p40_ls3p5.yaml
c62cf9a636c7db9aa9106d95688dcd76fc4d4e4a23ef88f49c65613fed803bb3  configs/tier2/memetic_deeppolish_p40_ls3p5_v2.yaml
a0bf896edbc760af3a9f722fa5fe4d874dd45da97a9d65184442508bba923664  configs/tier2/memetic_pop150.yaml
9a124f33d817a87d28f638349c9d5534c2cfeaf97a9455de61a353874d9246ee  scripts/submit_m2_memetic.sh
770a8059683512239244c74b26dc17c5589aaa5585871f250f6f90f03171a4e8  scripts/tier2_memetic_array.sbatch
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  src/__init__.py
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  src/cli/__init__.py
53ec767780a3e9d0a985be0bbb1447cc21ae46d7856ad75ac845ed73930a17d4  src/cli/oracle_evalmaxsat.py
e553897ead46850ad451b42977455630fdd838cf828f52095c09b942ce49e894  src/cli/profile_hardness.py
e580d6aef699db00bbb3430421c887d8fe2d5b1bd96df3a65bdafa2ec6952921  src/cli/run_memetic_shard.py
8befed8df0a0871229a48c09b1f630e25485868ac3347dc0d9309b42d2016885  src/cli/run_opt_rc2.py
4a2db95d3a15bca676a9892bf3c0107ba5a82a09dd22380d25b590c065442e4c  src/cli/solve_rc2_anytime.py
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  src/evo/__init__.py
6a9db9d50119d0f7ad2602531c409e7825e05c822fffcaaced8de1052f8710fb  src/evo/impl_v2.py
4ab37452b1fb17a213ad023557962b04aaf8a1bc939ea20d60600bb2912aedd2  src/evo/memetic.py
bf1f7521781461a8cbb1cd96f55e541670f1083fa3fc1ff1c322c6bcd1c7fb90  src/evo/multistart.py
ae18473a95ef8edf4ca7661a5319169b30759776b14e39e4f965be29e4af5623  src/evo/operators.py
c066028d3b9477af5210edd23db8d4a9709682f4d16cd9a156266413412cf043  src/evo/population.py
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  src/llm/__init__.py
257d20a9f89a012a0a7a2432ed1bd0cb03c29ca3d12308e53a4ec6e2a7a7b6fc  src/llm/advisor.py
13080195be63e97f4310957874261d20992f75ce7e41f1d85cfe717afdc03efb  src/llm/prompt.py
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  src/llm/providers/__init__.py
ff9ef635d4e00b71015fee78133fe597727623b4b33fc7e12609545751d0716a  src/llm/providers/noop.py
d5a1c12f02c95a005edc0581dd50d41c0cd54583d998546f006d7f87de191ad9  src/llm/providers/ollama.py
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  src/sat/__init__.py
9d81d9bfd3ae3e2a344a1327717b359a33d7e8d0d29ccf500285742d49d3d821  src/sat/cnf.py
25114c7df1b605cd98c21ae30b9b90a306cf16b158d49fe2a73440cca18d9149  src/sat/state.py
5e2635699a93bcd6491f1f2b21dc1e93953befb142b0dfd84782790b61b70958  src/sat/walksat.py
d47a4e86b3a804b783aec9411dc900d1a1be5abcd1cf5431072602608cb310b2  src/sat/walksat_v2.py
9dd391064726f61d614e73852881af556c903dc20b6497487675a9e848178acd  tests/test_cnf_legacy_formats.py
489ce5393835dd83b960940d8f3f2a82a33a5c9dcf84e55be56dd9d9795817cc  tests/test_cnf_new_format.py
7865f6841b0db6d037f01ef0f7041b02aab213cadeaba720eff2f369bcd3b03e  tests/test_local_multistart.py
cc914c59d38fb582a84e04a78059226a40ef10b6485ccf3018a19eb95f423b60  tests/test_oracle_evalmaxsat.py
a2ec8d843ec659afebb68a699c9e127cf8d8b9c516a9fb883a645d30af8c4cc6  tests/test_walksat_v2.py
```
