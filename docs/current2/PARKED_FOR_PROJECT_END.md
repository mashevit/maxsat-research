# Parked for the end of the project: explanations the user asked to keep, not to hear now

**Created:** 2026-10-28. **Updated:** 2026-11-01 (Aperture comparison added; monkey patch scoped to the code).

> "I dont want monkey patch explanation, undo it from reminders, put it in
> some note that you will remember it when I finish project, when I ask
> about details I forgot" (user, 2026-10-28)

> "remember to remind me also the aperture comparison, when i ask you if i
> forgot something, along with the monley patch in code not tests, and lea
> tables explantaion. write in some index doc, in memory only keep pointer to
> that index" (user, 2026-11-01)

**Rule:** nothing here is a reminder or a next step. Raise **all** the items
when the user asks whether they forgot something, or when the project is
being finished (write-up, code hand-off). Also raise an item when the user
asks about a detail it covers. This file is the index; the memory keeps only
a pointer to it.

| item | parked | where the explanation is |
|---|---|---|
| The "monkey patch" engineering decision in the strong tree. **The one to explain is the one in the solver code, not the tests** (user, 2026-11-01): attribute caches attached at run time to the WCNF object. (For reference only: pytest `monkeypatch` of `ls_v3.NBRS_MAX` forces lean tables in tests.) | 2026-10-25 (postponed), 2026-10-28 (parked), 2026-11-01 (scope: the code) | [`NOTES_2026-10-21_AGENDA_AND_STATS.md`](NOTES_2026-10-21_AGENDA_AND_STATS.md) §4 |
| What the "lean tables" are: the neighbour-table mode for very long clauses (no `nbrs` lists; CC and PX walk the clauses instead, walk mutation samples a neighbour by rejection), when it switches on (Σk(k−1) > 50M, only the setcover rail instances so far), and why it gives the same results | 2026-10-28 (user: "remind me as with the monkey patch to get explanation what are lean tables, in end of project when i ask what i forgot") | [`LONG_CLAUSE_RULE_DESIGN.md`](LONG_CLAUSE_RULE_DESIGN.md); built in C since C1 (`COMPILED_MEMETIC_PLAN.md`) |
| The memetic vs Aperture (Technion, Nadel / Slonimski / Strichman; MSE 2026 anytime winner, 4 of 6 tracks): on the 135 shared instances with a proven optimum, the memetic beats every Aperture variant on 7 at 1707 s (6 maximum-colorful-subtree) and Aperture-KBG on 19, but Aperture-KBG beats all 3 memetic seeds on 80 and the memetic is never better than the best verified anytime result | 2026-11-01 (user: "remind me also the aperture comparison, when i ask you if i forgot something") | [`MSE26_MEMETIC_VS_APERTURE.md`](MSE26_MEMETIC_VS_APERTURE.md); N-2026-11-01-i |
