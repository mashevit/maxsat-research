# Archive 2026-10-14: superseded documents

Moved here on 2026-10-14 (user: "create new archive folder in docs, and move
there not relevant files, even if there are in current doc folder").

**Rule used:** `docs/current/READING_LIST.md` says that every document it
does not list "is either superseded or already summarised". A document was
moved only if all three hold:
1. it is not on the reading list;
2. it is not indexed as research content in `docs/current/RESEARCH_NOTES.md` §1;
3. no code, config, script or test refers to it. So no code comment goes
   stale, and no file in a cluster upload hash list changes.

Every markdown link to these files was rewritten to the new path, and no
link is broken. Plain mentions by file name remain in a few places; the
files are here.

| document | why it is superseded |
|---|---|
| `CALIB_A_A1_READOUT.md` | calib_a RC2 read-out; its results are carried by `CALIB_B_B1_READOUT.md` (reading list #6) and `M2_FULL_POOL_READOUT_AND_STATE.md` (#5) |
| `CALIB_B_SUMMARY.md` | a one-page summary of calib_b; the full read-out `CALIB_B_B1_READOUT.md` is on the list |
| `CORPUS_GENERATOR_PILOT_NOTE.md` | a companion of the generator pilot; `CORPUS_GENERATOR_PLAN.md` (#7) is the reference |
| `M2_DEEPPOLISH_SUMMARY.md` | a one-page summary of `M2_DEEPPOLISH_HANDOUT.md`, which stays in `docs/` |
| `M2_PILOT_READOUT.md` | the M2 pilot, superseded by the full-pool read-out `M2_FULL_POOL_READOUT_AND_STATE.md` (#5) |

**Not moved, although not on the reading list:**
- Code refers to these: `CALIB_B_PLAN.md`, `M2_DEEPPOLISH_HANDOUT.md`,
  `M2_DEEPPOLISH_RUN_PREPARATION.md`, `M2_FULL_POOL_RUN.md`.
- These are indexed research content: `CORPUS_FAMILY_SCOPE_NOTE.md`,
  `UUF_THREE_ARM_ABLATION_READOUT.md`, `maxsat-benchmark-design-notes.md`.
- Everything in `docs/current/` is on the reading list or indexed in
  `RESEARCH_NOTES.md`, so nothing moved from there.

The older archive is the parent folder `docs/archive/`.
