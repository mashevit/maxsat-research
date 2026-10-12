# A question to put to a web LLM: is there published work on a flips-per-variable coefficient?

**Created:** 2026-10-12, at the user's request: "remember to give me
mission to ask web LLM if there was work about coefficient".
**Status:** a to-do item. It is *not* to be raised at the start of a
session (user, 2026-10-12: "just keep it in todo"). When the user takes it
up, they paste the prompt below into a web LLM with search or deep research,
and bring the answer back.
**Our own search so far:** N-2026-10-12-b,
`RESEARCH_NOTES_FLIP_LIMIT_SCALING.md`, which found no published c.

## Prompt (copy as is)

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

## What to do with the answer

- Check each cited source before using it. A web LLM can invent
  citations.
- Add a dated note to `RESEARCH_NOTES.md` that refers to
  `RESEARCH_NOTES_FLIP_LIMIT_SCALING.md`.
- If a usable value of c turns up, compare it with the grid in
  `HYPERPARAMETER_CALIBRATION_PLAN.md` §0b (c 12.5–200 at n 16,000;
  3.125–50 at n 64,000).
