#!/bin/bash
#SBATCH --partition=main
#SBATCH --job-name=mse16-smoke
#SBATCH --array=1-5
#SBATCH --time=00:05:00
#SBATCH --mem=4G
#SBATCH --cpus-per-task=1
#SBATCH --output=logs/mse16-smoke-%A_%a.out
#SBATCH --error=logs/mse16-smoke-%A_%a.err

# Smoke test for the MSE-2016 corpus screen: same code path as
# screen_mse16_array.sbatch, 5 hand-picked instances, cap 20 s instead of 900 s.
# Run this once after every rsync of the staging tree -- it catches a missing
# conda package, an unstaged data/ tree and a broken import in about a minute,
# which is much cheaper than finding out on task 104.
#
#   sbatch scripts/smoke_mse16_array.sbatch
#
# The 5 are NOT the first 5 lines of the screen manifest. They are chosen to
# cover every clause shape in the corpus and BOTH branches profile_hardness can
# take, which the first 5 (all bipartite MaxCut, all timeouts) would not:
#
#   1 c-fat500-1.clq.cnf   binary, 48 clauses    -> optimal in ~0.002 s, c* = 2
#   2 t3pm3-5555.spn.cnf   units + binary, 162   -> optimal in ~0.01 s,  c* = 17
#   3 scpclr10_maxsat.cnf  clauses up to len 126 -> capped, lb 13 (widest parse)
#   4 HG-4SAT-V100-C900-14 quaternary, 900       -> capped
#   5 s3v70c700-1.cnf      ternary, 700          -> capped, lb 8
#
# EXPECTED RESULT: tasks 1-2 status=optimal with exactly the costs above;
# tasks 3-5 hit the cap (status=timeout or status=subprocess_killed).
# **Three non-completions is a PASS, not a failure.** At a 20 s cap only the two
# small crafted instances finish; measured on the workstation, tasks 3-5 need
# well over 30 s. Their value here is that they exercise the subprocess-kill
# path (where the watchdog bug lived, commit a25b853) and the long-clause parse,
# neither of which the two fast instances touch.
#
# Which capped status you get just says which watchdog layer fired: `timeout`
# is the graceful SIGALRM inside the child, `subprocess_killed` the outer
# SIGKILL at cap+grace. Both are normal. Measured here, all three came back
# `subprocess_killed`.
#
# Only tasks 1-2 are asserted on value, because only they are machine
# independent: 0.002 s and 0.013 s complete on any node and the optima are
# exact. The capped tasks' `cost_lower_bound` is NOT asserted -- how far RC2
# gets in 20 s depends on node speed. Measured here: task 3 lb=13, task 5 lb=8,
# task 4 lb=null (RC2 had not established a bound yet -- legitimate, and the
# reason this is logged rather than asserted).
#
# WHAT WOULD BE A REAL FAILURE:
#   - status=error (the profiler itself broke) or a missing/empty output file
#   - status=unsat -- unreachable on this corpus, every clause is soft, so it
#     means the file was parsed as hard CNF (the EvalMaxSAT trap, in PySAT)
#   - task 1 or 2 not optimal, or optimal at a cost other than 2 / 17
#   - task 1 or 2 hitting the cap (they take milliseconds; something is wrong)
#   - "no files matched" from the profiler (data/ not rsynced)
#   - lb=null on ALL THREE of tasks 3-5. Any one alone is normal; all three
#     together suggests the progress-file recovery path is broken. Compare the
#     `lb=` values across the five task logs.

set -euo pipefail

MANIFEST="${MANIFEST:-scripts/manifest_mse16_smoke.txt}"
OUTDIR="${OUTDIR:-results/profile_mse16_smoke}"
CAP="${CAP:-20}"

echo "task=${SLURM_ARRAY_TASK_ID} host=$(hostname) start=$(date -Iseconds)"

module load anaconda
source activate maxsat

cd ..

INSTANCE=$(sed -n "${SLURM_ARRAY_TASK_ID}p" "$MANIFEST")
if [[ -z "$INSTANCE" ]]; then
    echo "FATAL: manifest ${MANIFEST} has no line ${SLURM_ARRAY_TASK_ID}" >&2
    exit 2
fi
echo "instance=${INSTANCE}"

if [[ ! -f "$INSTANCE" ]]; then
    echo "FATAL: instance not staged: ${INSTANCE}" >&2
    echo "The data/ tree is gitignored and rsynced separately -- rsync it." >&2
    exit 2
fi

mkdir -p "$OUTDIR"
OUT="${OUTDIR}/mse16_smoke_task_${SLURM_ARRAY_TASK_ID}.jsonl"
rm -f "$OUT"          # so a stale record from a previous smoke cannot pass

# No --bestknown: MSE-2016 ships no reference optima in this tree, matching
# screen_mse16_array.sbatch. Cap is deliberately 20 s, not the screen's 900 s.
python -m src.cli.profile_hardness \
    --instances "$INSTANCE" \
    --cap "$CAP" \
    --grace 10 \
    --out "$OUT"

# Fail the task on anything the eye would miss in a log: no record written, a
# status that should be unreachable, or a lost lower bound. Hitting the cap is
# expected on tasks 3-5 and passes.
python - "$OUT" "${SLURM_ARRAY_TASK_ID}" <<'PY'
import json, sys

# Only the two instantaneous tasks carry a value assertion; see the header.
EXPECT_OPTIMAL_COST = {1: 2, 2: 17}
CAPPED = {"timeout", "subprocess_killed"}

path, task = sys.argv[1], int(sys.argv[2])
recs = [json.loads(l) for l in open(path) if l.strip()]
if len(recs) != 1:
    sys.exit(f"FAIL: expected 1 record in {path}, got {len(recs)}")
p = recs[0]["profile"]
status = p["status"]

if status not in CAPPED | {"optimal"}:
    sys.exit(f"FAIL: unexpected status={status} error={p['error']}")

want = EXPECT_OPTIMAL_COST.get(task)
if want is not None:
    if status != "optimal":
        sys.exit(f"FAIL: task {task} should finish in milliseconds, "
                 f"got status={status}")
    if p["final_cost"] != want:
        sys.exit(f"FAIL: task {task} optimum is {p['final_cost']}, expected {want}")
elif status == "optimal" and p["final_cost"] is None:
    sys.exit("FAIL: status=optimal but final_cost is null")

# lb is reported, not asserted: whether RC2 establishes a bound inside a 20 s
# cap is node-speed dependent. lb=null on all three capped tasks is the signal
# worth chasing, and that is a cross-task comparison, not a per-task one.
print(f"OK task={task} status={status} solve_s={p['solve_s']} "
      f"cost={p['final_cost']} lb={p['cost_lower_bound']} tier={recs[0]['tier']}")
PY

echo "end=$(date -Iseconds) exit=$?"
