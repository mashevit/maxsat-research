# Parked for the end of the project: explanations the user asked to keep, not to hear now

**Created:** 2026-10-28.

> "I dont want monkey patch explanation, undo it from reminders, put it in
> some note that you will remember it when I finish project, when I ask
> about details I forgot" (user, 2026-10-28)

**Rule:** nothing here is a reminder or a next step. Raise an item only
when the project is being finished (write-up, code hand-off) or when the
user asks about a detail it covers.

| item | parked | where the explanation is |
|---|---|---|
| The "monkey patch" engineering decision in the strong tree: attribute caches attached to the WCNF object, and pytest `monkeypatch` of `ls_v3.NBRS_MAX` to force lean tables in tests | 2026-10-25 (postponed), 2026-10-28 (parked) | [`NOTES_2026-10-21_AGENDA_AND_STATS.md`](NOTES_2026-10-21_AGENDA_AND_STATS.md) §4 |
| What the "lean tables" are: the neighbour-table mode for very long clauses (no `nbrs` lists; CC and PX walk the clauses instead, walk mutation samples a neighbour by rejection), when it switches on (Σk(k−1) > 50M, only the setcover rail instances so far), and why it gives the same results | 2026-10-28 (user: "remind me as with the monkey patch to get explanation what are lean tables, in end of project when i ask what i forgot") | [`LONG_CLAUSE_RULE_DESIGN.md`](LONG_CLAUSE_RULE_DESIGN.md); built in C since C1 (`COMPILED_MEMETIC_PLAN.md`) |
