# MSE best-known filter — summary

Filtered MSE best-known cost tables against the local instances in
`data/raw/mse_2024/`. Both output CSVs now cover every local instance:
known costs come from upstream MSE tables; unknowns are marked
`best_cost = -1`, following the convention CSV B already uses.

## Sources

| Upload                | Identified as                                                   | Upstream                                                            | Rows total |
|-----------------------|-----------------------------------------------------------------|---------------------------------------------------------------------|-----------:|
| `best_costs.csv`      | MSE 2023 anytime "best known" (all benchmarks in the complete set) | <https://maxsat-evaluations.github.io/2023/results/anytime/best_costs.csv> (confirmed identical) | 2780 |
| `best_costs__1_.csv`  | MSE 2024 best-known (all four track flags carried per row)      | (inferred from per-row weighted/unweighted/anytime flags)           | 1124 |

## Match matrix (basename equality)

|                              | best_costs.csv (2023) | best_costs__1_.csv (2024) |
|------------------------------|----------------------:|--------------------------:|
| `mse23-uw-small/` (75 files) | **73 / 75 = 97.3%**   | 17 / 75 = 22.7%           |
| `mse24-small/`   (91 files)  | 19 / 91 = 20.9%       | **91 / 91 = 100%**        |

Diagonal is decisive. Off-diagonal hits are families that recur across
years (e.g. `gen-hyper-tw`, `judgment-aggregation-ja-maxham`), not
mis-routing.

> The earlier 73 + 87 = 160 file count I quoted was wrong. The actual
> tree listing has 75 + 91 = 166 `.wcnf` files (footer says "167 files"
> because the 0-byte `mse_2024_tree.txt` itself is counted).

## Outputs

- `bestknown_mse23.csv` — **75 rows** (one per local file in
  `mse23-uw-small/`). Schema:
  `instance, best_cost, source, source_csv`. Two rows have
  `best_cost = -1` and `source_csv = absent_from_best_costs.csv`.

- `bestknown_mse24.csv` — **91 rows** (one per local file in
  `mse24-small/`). Schema:
  `instance, best_cost, weighted, unweighted, anytime, source, source_csv`.
  Three rows had `best_cost = -1` already in the upstream MSE 2024 CSV.

- `unmatched.txt` — provenance note for the two forced-to-`-1` mse23
  basenames.

## Instances with unknown best-known cost (5 total)

These can't have `ratio` computed against them in stratification. They
should be assigned a tier on a non-ratio basis — most naturally T3
(treated as hard by definition, since no participating MSE solver
established a known cost).

### mse23 — absent from `best_costs.csv`

- `pseudoBoolean-normalized-par32-3.opb.msat.wcnf`
- `pseudoBoolean-normalized-par32-5.opb.msat.wcnf`

Confirmed not in the MSE 2023 anytime `best_costs.csv` (the upstream
of CSV A). Web search for these specific instance names yielded no
published best-known cost. The most plausible explanation is that
they originate from the MSE 2023 **exact**-track corpus or from the
MaxSATRegressionSuite (a fuzzer-generated set of small instances used
to test solver robustness), neither of which publishes anytime
best-known costs in the form CSV A uses. The `par32` family itself is
a well-known hard SAT-competition lineage (parity-learning instances);
worth keeping in the corpus.

### mse24 — `best_cost = -1` upstream

- `lisbon-wedding_wt-lisbon-wedding-1-19.wcnf`
- `lisbon-wedding_wt-lisbon-wedding-3-18.wcnf`
- `pseudoBoolean_wt-normalized-mps-v2-20-10-mod010.opb.msat.wcnf`

For these, the MSE 2024 organizers themselves recorded "best cost not
known" — meaning no participating solver in MSE 2024 returned a usable
solution within the time budget.

## Note on `mse24-small/` being single-track

All 91 rows carry `(weighted=True, unweighted=False, anytime=True)`.
The `-un-` substring inside some filenames (e.g.
`decision-tree-heart-cleveland-un-formula_…`) is part of the *family*
name, not a track flag. No per-row track filter needed for that folder
in downstream stratification.
