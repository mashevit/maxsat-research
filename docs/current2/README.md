# docs/current2: new documents from 2026-10-14 on

**Created:** 2026-10-14 (user: "create new current docs folder in which you
will put new docs from now").

**Rule:**
- **Every new document** (plans, read-outs, research notes
  `RESEARCH_NOTES_<TOPIC>.md`, web-LLM prompts, handouts) is created here,
  not in `docs/current/`.
- **Existing documents in `docs/current/` stay where they are** and are
  still updated in place: their paths appear in code comments, configs and
  cluster upload lists.
- **The three hubs stay in `docs/current/` and remain the entry points:**
  - `docs/current/NEXT_SESSION_CONTEXT.md` (read first);
  - `docs/current/RESEARCH_NOTES.md`: the §1 index and the dated notes;
    every new document here is indexed there, with its `docs/current2/`
    path;
  - `docs/current/READING_LIST.md`.
- Superseded documents go to `docs/archive/<date>_superseded/` with a
  README (as in `docs/archive/2026-10-14_superseded/`).

## Documents

| document | created | what it is |
|---|---|---|
| [`STRONG_MEMETIC_S1_RUN.md`](STRONG_MEMETIC_S1_RUN.md) | 2026-10-18 | The stronger memetic built (`impl: v3`, B1–B5, tree `cluster_staging_maxsat_strong/`): deviations, tests, speed, smoke, batch S1 (324 tasks), upload and commands. N-2026-10-18-c. |
| [`STRONGER_MEMETIC_DESIGN.md`](STRONGER_MEMETIC_DESIGN.md) | 2026-10-18 | Stronger memetic B1–B5: motivation, how each works (sources checked), parameters, the interactions between them, and the build plan for the third tree `cluster_staging_maxsat_strong/` (S1–S7) plus a leave-one-out batch. N-2026-10-18-b. |
| [`KERNEL_MEMETIC_RUN.md`](KERNEL_MEMETIC_RUN.md) | 2026-10-18 | Milestone A: the kernel module, gate and shard fields; smoke; the 18-task calib_2sat_sc2 batch (upload list, commands); §5 the proposed stronger memetic (direction B). N-2026-10-18-a. |
