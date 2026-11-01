# The memetic vs Aperture (MSE 2026 anytime winner) on the shared instances

> "check if our solver has some better results on some instances than the winning solver from technion thesis its name is Aperture" (user, 2026-11-01)

**Status.** A descriptive comparison, not pre-registered (2026-11-01, N-2026-11-01-i).
Script: `cluster_staging_maxsat_strong/scripts/mse26_vs_aperture.py`. Output:
`results/mse26_vs_aperture.txt`, with per-instance rows in `results/mse26_vs_aperture.tsv`.

**Short answer.**
- **Yes**, on a few instances. The memetic beats **every** Aperture variant on **7**
  of the 135 shared instances at 1707 s, and on 6 of them with at least 2 of its 3
  seeds. Six of the seven are maximum-colorful-subtree.
- Against Aperture-KBG, the variant that won 4 of the 6 tracks, the memetic is
  better on **19** instances (15 with ≥ 2 seeds, 9 with all 3).
- **Overall, Aperture is much stronger.** Aperture-KBG is better than all 3 memetic
  seeds on 80 / 135. It reaches the optimum on 75 / 135; the memetic does so on
  37 with ≥ 1 seed and 19 with all 3.
- The memetic is never better than the best verified result of *all* anytime
  solvers. It ties that best on 37 instances.

## 1. Aperture and the data

- **Aperture.** Alexander Nadel, Yam Slonimski and Ofer Strichman (Technion).
  - Slonimski built it for his master's degree, supervised by Strichman.
  - It is an anytime, complete and incremental MaxSAT solver in C++, and the
    successor of TT-Open-WBO-Inc.
  - It was presented as work in progress at SOFT'26, and the developers say it was
    accepted to FMCAD 2026.
  - It took first place in **4 of the 6 MSE 2026 anytime tracks**.
  - Sources: the SOFT'26 paper
    (https://web-genobioinfo.toulouse.inrae.fr/~degivry/soft2026/NadelSlonimskiStrichmanSoft2026.pdf)
    and A. Nadel's LinkedIn post. The thesis itself was not found.
- **The published rankings (average anytime score; Aperture's best variant and the
  track winner):**

  | track | 60 s | 300 s | 1707 s |
  |---|---|---|---|
  | unweighted | PASMaxSAT-c 0.861 (Aperture-GBG 3rd, 0.856) | **Aperture-KBG** 0.907 | PASMaxSAT-c 0.948 (Aperture-KBG 2nd, 0.946) |
  | weighted | **Aperture-KBG** 0.914 | **Aperture-KBG** 0.942 | **Aperture-KBG** 0.963 |

  This matches the developers' count: Aperture-KBG wins 4 of the 6 (bold). Variants: unweighted KBG, GBG, IBI;
  weighted KBG, KBI, GBG.
- **Data.**
  - `results.zip` from Zenodo 21358014, the same record as our exact-track
    data. Its md5 `6207677e…` matches Zenodo.
  - The six anytime rawdata and ranking CSVs are copied to
    `data/raw/mse_results/mse26/anytime/`, with a `SHA256SUMS` file. The exact-track
    rawdata inside the zip is byte-identical to our existing copy.
- **Shared instances: 135** (unweighted 52, weighted 83).
  - These are the anytime-track instances that are also among the 947 exact-track
    instances with a published optimum that batch 3c ran.
  - 127 of them are in the ρ primary population.
  - The anytime track has 386 instances. Most of the others have no proven
    optimum, so the memetic was not run on them. **The shared 135 are therefore
    the easier, proven part of the anytime set.**

## 2. How costs are compared

- **Aperture.** We take the reported cost from a run whose answer is
  SATISFIABLE / OPTIMUM FOUND and whose result is verified (`verified == 1`).
  Any other run counts as no result (∞).
  - Unverified costs exist only for PX-TT-Open-WBO-Inc: 74 runs below the proven
    optimum, all `verified = 0`. They are excluded.
  - No verified anytime cost is below the published optimum.
- **Memetic.**
  - Each seed is scored by the best cost of its run. A run that ended in an error
    or with a violated hard clause counts as ∞.
  - Budget: 1,800 s process CPU (Aperture: 1,707 s wall).
  - The memetic stops early **only** when it hits the published optimum.
    Knowing the target therefore changes only when a successful run stops, not
    the cost it reports. A non-optimal cost is what the memetic had at the end of
    the full budget, without seeing the target.
  - At 60 and 300 s the memetic logged no cost over time. We only know whether
    it had reached the optimum by then (CPU time to the hit ≤ t). So at 60 and
    300 s, "memetic better" means it reached the optimum by t and Aperture's cost
    at t was above the optimum.
- **"Aperture-best"** = the lowest of the three variants' costs per instance. This
  is a stronger reference than any single Aperture run.
- **Seeds.** The memetic has 3 seeds; Aperture has 1 run per variant. We report
  "better with ≥ 1, ≥ 2, all 3 seeds". **≥ 2 seeds (a majority) is the fair
  reading**; ≥ 1 seed favours the memetic.

## 3. Results

| 135 shared instances | 60 s | 300 s | 1707 s |
|---|---|---|---|
| Aperture-KBG reaches the optimum | 42 | 52 | 75 |
| Aperture-best reaches the optimum | 55 | 72 | 90 |
| memetic reaches the optimum, ≥ 1 seed / all 3 | 11 / 7 | 20 / 10 | 37 / 19 |
| **memetic better than Aperture-KBG**, ≥ 1 / ≥ 2 / 3 seeds | 3 / 2 / 2 | 5 / 2 / 2 | **19 / 15 / 9** |
| **memetic better than Aperture-best**, ≥ 1 / ≥ 2 / 3 seeds | 1 / 0 / 0 | 1 / 1 / 1 | **7 / 6 / 1** |
| Aperture-KBG better than all 3 seeds / than ≥ 2 seeds | — | — | 80 / 92 |
| Aperture-best better than all 3 seeds / than ≥ 2 seeds | — | — | 89 / 102 |

### 3.1 Where the memetic beats every Aperture variant (1707 s)

| track | instance | family | optimum | Aperture-best | memetic s1 / s2 / s3 | seeds better |
|---|---|---|---:|---:|---|---:|
| W | `c11a2e14` | maximum-colorful-subtree | 1418 | 1425 | 1421 / 1423 / 1421 | 3 |
| W | `1198839e` | maximum-colorful-subtree | 3562 | 3575 | 3572 / 3581 / 3571 | 2 |
| W | `aba43574` | maximum-colorful-subtree | 827 | 832 | 828 / 837 / 831 | 2 |
| W | `bc8befbb` | maximum-colorful-subtree | 8001 | 8008 | 8006 / 8007 / 8009 | 2 |
| W | `c8d65621` | maximum-colorful-subtree | 4095 | 4102 | 4097 / 4102 / **4095** (optimum at 1,454 s) | 2 |
| W | `cd32041c` | maximum-colorful-subtree | 7603 | 7614 | 7612 / 7617 / 7610 | 2 |
| UW | `43c16877` | inconsistency-measurement | 45 | 49 | 52 / 51 / 48 | 1 |

- **maximum-colorful-subtree.** It is the one family where the memetic is
  consistently ahead of Aperture: better on 6 of the 14 shared instances.
  - Only on `c8d65621` (seed 3) does the memetic reach the optimum. On the other
    five it only gets closer than Aperture.
  - Other anytime solvers do better than both on these instances. Their verified
    best reaches the optimum on five of the six and is 1 above it on
    `1198839e` (3563, BouMS-CaDiCaL). Among them are CPMpy_HiGHS, Loandra,
    BouMS and the NuWLS variants.
  - On the other 8 instances of the family, Aperture is as good or better. On
    `b3843303` its best ties the memetic's best seed (761).

### 3.2 Where the memetic beats Aperture-KBG (1707 s; 19 instances)

The 7 above, plus 12 more:

| track | instance | family | optimum | Aperture-KBG | memetic s1 / s2 / s3 | seeds better |
|---|---|---|---:|---:|---|---:|
| UW | `1138c348` | scheduling | 28 | 30 | **28 / 28 / 28** (7–35 s) | 3 |
| UW | `4adad251` | inconsistency-measurement | 44 | 50 | 49 / 47 / 49 | 3 |
| UW | `ee0b9a4e` | inconsistency-measurement | 48 | 53 | 51 / 51 / 53 | 2 |
| UW | `daf935ca` | asp-optimization | 94 | 95 | 95 / **94** / 95 | 1 |
| W | `b22a7099` | pareto-optimal-interpretation-synthesis | 147 | 211 | **147 / 147 / 147** (191–671 s) | 3 |
| W | `fee78180` | pareto-optimal-interpretation-synthesis | 311 | 313 | **311 / 311 / 311** (35–112 s) | 3 |
| W | `0287e2fb` | switching-activity-maximization | 2 | 12 | 10 / **2** / 6 | 3 |
| W | `98b3b51d` | two-echelon-vehicle-routing | 2097619 | 2097711 | 2097635 / 2097667 / 2097651 | 3 |
| W | `188146bb` | two-echelon-vehicle-routing | 2097727 | 2097811 | 2097763 / 2097795 / 2097799 | 3 |
| W | `65e6df32` | two-echelon-vehicle-routing | 2097719 | 2097775 | 2097763 / 2097799 / 2097795 | 1 |
| W | `06049417` | two-echelon-vehicle-routing | 2097703 | 2097795 | 2097795 / 2097759 / 2097795 | 1 |
| W | `4c44f623` | asp-optimization | 379 | 451 | 425 / 449 / 474 | 2 |

Bold = the seed reached the optimum. On these 12, another Aperture variant (KBI,
GBG or IBI) is at least as good as the memetic's seeds, so they do not appear in
§3.1.

### 3.3 Earlier time limits (60 s, 300 s)

- **Against Aperture-best,** only `fee78180` (pareto-optimal-interpretation-synthesis).
  The memetic reaches the optimum 311 at 35 s (seed 1), and with all 3 seeds by
  112 s. Aperture-best is still at 313 at 60, 300 and 1707 s.
- **Against Aperture-KBG** at 60 s: `1138c348`, `2a906778` (optimizing-bdds; the
  memetic reaches 62 at 11–30 s, KBG is at 70) and `fee78180`. At 300 s:
  `1138c348`, `fee78180`, `b22a7099`, `0287e2fb`, `f24a38d9`
  (single-machine-scheduling, one seed at 240 s).

## 4. What this supports [inference]

- **The memetic is not competitive with Aperture as a solver.** Aperture-KBG
  reaches twice as many optima (75 vs 37, even counting a memetic success on any
  of its 3 seeds). It beats all 3 memetic seeds on 59 % of the shared instances,
  against 7 % the other way (9 / 135).
- **There are isolated wins worth mentioning.**
  - maximum-colorful-subtree (6 / 14 instances better than every Aperture
    variant).
  - Two pareto-optimal-interpretation-synthesis instances and one scheduling
    instance, where the memetic reaches the optimum quickly with all seeds and
    Aperture-KBG does not reach it even at 1707 s.
- **This is the same picture as with EvalMaxSAT (complementarity, §4.2 of
  `MSE26_RHO_RESULTS_3.md`).** A weaker solver with a few instances where it is
  ahead. Here it is weaker still: on none of the 135 instances is the memetic
  better than the best verified result of all anytime solvers. So it adds
  nothing to the anytime virtual best solver on these instances.
- **Caveats.**
  - Different hardware (MSE cluster vs ours).
  - Different budgets: 1,707 s wall vs 1,800 s CPU, roughly equal for a
    single-threaded run.
  - 3 memetic seeds vs 1 run per Aperture variant.
  - Only the 135 proven instances of the anytime set are compared.
  - The memetic has no cost trajectory, so 60 and 300 s are compared only through
    "optimum reached".
  - One shared instance (`6a0db8fd`, xai-mindset) has all 3 memetic seeds stopped
    by the watchdog; it counts as ∞.

## 5. Reproduce

```bash
cd cluster_staging_maxsat_strong
python3 scripts/mse26_vs_aperture.py > results/mse26_vs_aperture.txt   # also writes results/mse26_vs_aperture.tsv
```

Inputs:
- `data/raw/mse_results/mse26/anytime/*.csv` (published, `SHA256SUMS`);
- `data/raw/mse_results/mse26/benchmark-metadata.csv`;
- `results/mse26_rho_r3_fail/instances.csv`;
- `results/mse26_memetic/tasks/*.jsonl`.
