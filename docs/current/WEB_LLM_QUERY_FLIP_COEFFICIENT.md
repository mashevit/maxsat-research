# Questions to put to a web LLM: published work on a flips-per-variable coefficient, and hyperparameter frameworks

**Created:** 2026-10-12, at the user's request: "remember to give me
mission to ask web LLM if there was work about coefficient".
**Status:** a to-do item. It is *not* to be raised at the start of a
session (user, 2026-10-12: "just keep it in todo"). When the user takes it
up, they paste the prompt below into a web LLM with search or deep research,
and bring the answer back.
**Our own search so far:** N-2026-10-12-b,
`RESEARCH_NOTES_FLIP_LIMIT_SCALING.md`, which found no published c.

**Added 2026-10-14:** Prompt 2, on hyperparameter frameworks (user: "check
if there are relevant hyperparameter frameworks, and write in to do I will
check with external llm"). Same status: a to-do, not a session opener.
**Stance to keep in mind when reading the answers** (user, 2026-10-14): in
the frameworks the parameter is set automatically; we want c as an
empirical, concrete result of our own grid
(`HYPERPARAMETER_CALIBRATION_PLAN.md` §0c.1). The answers inform the
protocol and the related-work section; they do not replace the grid.

## Prompt 1: published values of c (copy as is)

> I am calibrating a memetic algorithm for unweighted MaxSAT (random
> Max-2-SAT, n = 16,000 and 64,000 variables, clause/variable ratio
> 1.1–1.2, i.e. just above the 2-SAT threshold, unsatisfiable, optimum
> 9–14 unsatisfied clauses). Each child is polished by a WalkSAT-style local
> search with a per-call flip limit. I want to set that limit as
> flips = max(12500, c · n), where n is the number of variables.
>
> Is there published work (papers, theses, solver documentation, competition
> reports) that gives or calibrates a coefficient like c: a local-search
> length per call, or a cutoff, proportional to the number of variables? I
> am interested in:
> 1. memetic or hybrid genetic algorithms for SAT/MaxSAT (e.g. GASAT,
>    FlipGA, Boughaci, Lardeux/Saubion/Hao) and how they size the local
>    search per offspring;
> 2. iterated local search or tabu search for MaxSAT with n-scaled
>    parameters (IRoTS uses an n²/4 no-improvement window; are there
>    others?);
> 3. empirical or theoretical scaling of the optimal restart cut-off
>    (Maxflips) with n (I know Parkes & Walser 1996: about n^2.39 for WSAT
>    at the 3-SAT threshold; Gent & Walsh 1993/1995);
> 4. statistical-physics results on local search time per variable (e.g.
>    Semerjian & Monasson; Seitz, Alava & Orponen) for random 2-SAT or
>    Max-2-SAT *above* the threshold;
> 5. any MaxSAT Evaluation incomplete-track solver (SATLike, NuWLS,
>    Loandra's local search, etc.) that sets its local-search steps as a
>    multiple of n.
>
> For every source give: full citation, the exact rule or value (quote it),
> the problem class and sizes tested, and a link. Say clearly when you
> could not verify a claim in the source itself. Do not invent citations.

## Prompt 2: hyperparameter frameworks and size-dependent parameters (copy as is)

> I am calibrating one parameter of a memetic MaxSAT solver: the per-call
> flip limit of its WalkSAT-style local search, set as
> flips = max(12500, c · n) with n the number of variables. Targets are
> random Max-2-SAT instances at n = 16,000 and 64,000 with proven optima;
> each run is 900 s on a Slurm cluster, and no controller process may run
> on the login node. I plan to choose c by a fixed, pre-registered grid
> (200k–3.2M flips per call, 3 instances × 3 seeds per size) and report
> the whole measured curve.
>
> 1. Which algorithm-configuration or hyperparameter frameworks (irace,
>    SMAC3, ParamILS, GGA/GGA++, Optuna, BOHB/DEHB, ISAC, Hydra, others)
>    support, or have been used for, a parameter that is a *function of
>    instance size* rather than one value? Quote how it is expressed
>    (e.g. a conditional or scaled parameter, instance features, a fitted
>    model).
> 2. Papers that fit or tune a *scaling law* of a parameter in instance
>    size and extrapolate it to larger instances. I know Styles, Hoos &
>    Müller (LION 2012), Mascia, Birattari & Stützle (LION 2013), Mu,
>    Hoos & Stützle (2016). What else, especially after 2016? I have seen
>    a reference to linear, piecewise and log-log models of optimal
>    parameter value against instance size (about 2021); give its exact
>    citation if it exists.
> 3. Has any of these frameworks been applied to MaxSAT or SAT local
>    search to tune a flip limit, cutoff, restart length or number of
>    steps (e.g. Ye, Luo & Cai, AAAI 2025, which tunes MaxSAT local search
>    with SMAC)? What values or rules came out, and did they scale with n?
> 4. Methodological advice in this literature on choosing a parameter
>    from a small grid with few instances and seeds (racing statistics,
>    capping, held-out instances, overfitting to training sizes).
>
> For every source give the full citation, the exact rule or result
> (quote it), the problem class and instance sizes, and a link. Say
> clearly when you could not verify a claim in the source itself. Do not
> invent citations.

## What to do with the answer

- Check each cited source before using it. A web LLM can invent
  citations.
- Add a dated note to `RESEARCH_NOTES.md` that refers to
  `RESEARCH_NOTES_FLIP_LIMIT_SCALING.md`.
- For Prompt 2: add verified sources to
  `RESEARCH_NOTES_HYPERPARAMETER_TUNING.md` (§2–§4) with a dated note.
- If a usable value of c turns up, compare it with the grid in
  `HYPERPARAMETER_CALIBRATION_PLAN.md` §0b (c 12.5–200 at n 16,000;
  3.125–50 at n 64,000).
