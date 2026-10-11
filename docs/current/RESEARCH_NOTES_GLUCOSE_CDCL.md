# How Glucose works: decisions, conflicts, phases and assumptions

**Date:** 2026-10-11. **Why this note exists:** the hard-clause solver
(`cluster_staging_maxsat_hard/`, `impl: hard`) uses PySAT's Glucose4 for three
things:
- initialisation;
- repair `R`;
- feasible moves `M`.

Its behaviour, especially why repairs stay *near* the given assignment, why
singleton cores are proofs, and why single calls can be slow, follows from
how a CDCL solver makes decisions. This note collects the explanation given
in the session of 2026-10-11 (user questions: "explain simply how glucoze4 is
implemented", "explain a little in more details about the decisions concept
in glucoze").

**Status labels.** General CDCL / Glucose behaviour is textbook material
[background]. Statements about our code are [verified] where a test or a
measurement backs them. One point about PySAT's phase interface is
[inference] (§5).

Related: `HARD_CLAUSE_SOLVER_PLAN.md` §6a–§6b; research notes N-2026-10-11-l
(H3) and N-2026-10-11-m (singleton cores vs RC2).

---

## 1. What Glucose is

Glucose is a **SAT solver**. Given a set of clauses, it either finds an
assignment that satisfies all of them or proves that none exists.
- It belongs to the **CDCL** family (conflict-driven clause learning) and is
  built on MiniSat.
- In our solver it only ever sees the **hard** clauses, plus at most one
  assumption per call. It never sees the soft clauses or their weights.

## 2. The main loop

1. **Decide.** Pick an unassigned variable and give it a value (§3).
2. **Propagate.** After every decision, any clause with only one literal left
   unassigned forces that literal: unit propagation. Two "watched literals"
   per clause make this fast.
3. **On a conflict, learn.** If propagation makes some clause false, the
   solver:
   - traces back which decisions caused it;
   - learns a new clause that rules this combination out, so the mistake is
     never repeated;
   - backjumps to an earlier decision level (§4).
4. **Repeat** until either:
   - every variable has a value: that is a model (a satisfying assignment);
   - or it derives the empty clause: that proves "unsatisfiable".
5. **Glucose's own contribution: which learned clauses to keep.**
   - Each learned clause is rated by its **LBD** (literal block distance):
     the number of distinct decision levels among its literals. Low LBD
     means short-range and useful.
   - Glucose keeps these "glue clauses" and regularly deletes the rest, so
     memory does not explode.
   - It restarts often, guided by the LBD of recent conflicts, and keeps
     everything it has learned across restarts.

## 3. Decisions, decision levels and the trail

A **decision** is a guess: when nothing is forced, the solver picks an
unassigned variable and assigns it a value. Everything else follows from
decisions plus propagation.

Glucose keeps a **trail**: the ordered list of the assignments made so far.
Each entry is one of two kinds:
- **decision:** chosen freely;
- **implied:** forced by a clause through unit propagation.

Each decision opens a new **decision level**. Level 0 holds what the clauses
force with no guess at all. Every implied literal belongs to the level of the
decision that caused it.

**Example.** Hard clauses (¬a ∨ b), (¬b ∨ c), (¬a ∨ ¬c):

| step | action | trail | level |
|---:|---|---|---:|
| 1 | decide **a = true** | a | 1 |
| 2 | (¬a ∨ b) forces b | a, b | 1 |
| 3 | (¬b ∨ c) forces c | a, b, c | 1 |
| 4 | (¬a ∨ ¬c) is now false: **conflict** | | |

## 4. What happens at a conflict

1. **Analyse.** Walk back through the trail to the clauses that forced each
   literal. Stop at a cut where only one literal belongs to the current
   level: the *first unique implication point* (1-UIP). In the example the
   cause is just a, so the solver learns the clause **(¬a)**.
2. **Backjump.** Jump back to the highest level that the learned clause still
   depends on, not simply one level up. In the example that is level 0.
3. **Propagate the learned clause.** At level 0, (¬a) forces a = false, so the
   bad guess can never be made again.

This **non-chronological backjumping** is the reason CDCL scales: one learned
clause can rule out a whole region of the search space.

## 5. How a decision is chosen

**The variable: activity (VSIDS).**
- Every variable has an activity score.
- Every variable involved in a conflict gets its score bumped, and all
  scores decay over time. Glucose starts with fast decay and slows to a
  factor of about 0.95.
- Variables from recent conflicts rise to the top of a priority heap. The
  next decision takes the most active unassigned variable.
- The effect: the solver concentrates on the "hot" part of the problem.

**The value: phase.**
- **Phase saving.** When backjumping undoes an assignment, the solver
  remembers the variable's last value and reuses it at the next decision on
  that variable. Restarts keep both the saved phases and the learned clauses,
  so progress is not lost.
- **User phase.** PySAT's `set_phases` is our way in: it sets a preferred
  value per variable. [inference] As far as we know, in MiniSat-derived
  solvers this preference takes priority at decision time.
  - [verified] Our own test agrees: repairing an already-feasible assignment
    returns it unchanged (`tests/test_hard_h3.py::
    test_repair_returns_a_feasible_assignment_near_the_input`).

**Consequence for our solver.**
- When we pass the current assignment x as phases, every decision agrees
  with x unless a conflict forces otherwise.
- So the model Glucose returns differs from x only where the hard clauses
  force a change. That is why repair `R` and moves `M` stay *near* x.
- [verified] On ja-maxham-00000385 a repair still changed about 940
  variables on average (the H3 smoke). On that instance the hard clauses
  force a lot.

## 6. Assumptions: decisions that cannot be undone

A call `solve(assumptions=[l])` works like this:
- Glucose places l as the **first decision** (level 1), before any free
  decision.
- If a conflict ever requires undoing l itself, the answer is
  **"unsatisfiable under the assumptions"**, not "unsatisfiable" overall.
  The clauses alone may still be satisfiable.
- Its final conflict analysis reports **which assumptions** caused the
  failure. That subset is the **core**.

**Two uses of the same mechanism:**

| | what is assumed | what an UNSAT answer gives |
|---|---|---|
| our moves `M` (H3) | **one** literal of one soft clause | if every literal of the clause fails: that soft clause is a **singleton core**, false in every feasible assignment (N-2026-10-11-m) |
| RC2 | **all** remaining soft clauses at once | a core: a subset of soft clauses that cannot all hold together, of any size. Its bound rises to the optimum |

That is why our singleton-core bound is weak. On ja-maxham-00000385 it
reached 31–33 against the optimum 37; the missing units come from cores of
two or more soft clauses, which single-literal assumptions never detect.

## 7. Why one call can take 30 s

- From a given assignment x, decisions follow x. If the assumption l is
  incompatible with x in a far-reaching way, Glucose may need many conflicts
  and backjumps before it either finds a nearby model or proves none exists.
- [verified] On ja-maxham-00000385 the median move call took 7 ms (refuted)
  to 63 ms (satisfiable), but single calls took 4.9 s and 30 s (the H3
  timing probe).
- The real cost is the number of conflicts. So each move call is capped at
  **5,000 conflicts** (`hard.moves.conf_budget`).
  - A call that hits the cap proves nothing: it is a "budget miss", not a
    core.
  - After 3 misses the clause is set aside for the run.

## 8. How our solver uses Glucose, in one place

| use | call | limits |
|---|---|---|
| initialisation | `solve()` per member, phases drawn from the JW prior or coins | interrupted at the run deadline |
| repair `R` | `solve()` with the child as phases | interrupted at the run deadline; no conflict cap |
| move `M` | `solve(assumptions=[l])` with the current assignment as phases | run deadline **and** 5,000 conflicts |

- **One solver per run** (`HardSAT`): learned clauses persist, so later
  calls benefit from earlier ones.
- **All Glucose time is charged to the run clock.**
- **The roles rule** (`CORPUS_FREEZE_PREP.md` §8.4): Glucose sees only the
  hard clauses and assumptions, never the objective. RC2 never seeds the
  solver.
