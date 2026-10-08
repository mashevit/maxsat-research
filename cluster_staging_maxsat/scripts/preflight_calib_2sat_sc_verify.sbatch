#!/bin/bash
#SBATCH --partition=main
#SBATCH --job-name=preflight-2sat-sc-verify
#SBATCH --time=00:05:00
#SBATCH --mem=1G
#SBATCH --cpus-per-task=1
#SBATCH --output=logs/preflight-2sat-sc-verify-%j.out
#SBATCH --error=logs/preflight-2sat-sc-verify-%j.err

# Compute-node half of the calib_2sat_sc preflight (docs/current/CALIB_2SAT_SC.md §9a).
# Submitted by preflight_calib_2sat_sc.sh with --dependency=afterany:<smoke array>;
# it never runs on the login node (the cluster terminates Python there).
#
# Checks, on a compute node, in the same env the RC2 tasks use:
#   - pysat.__version__ == EXPECT_PYSAT; RC2 and src.cli.* import from the root;
#   - smoke task 1 (n=2000): completed, final_cost == lower bound (a proven c*);
#   - smoke task 2 (n=32000, cap 60): censored with a recovered lower bound and
#     no reported cost;
#   - both env records carry EXPECT_PYSAT and a Slurm array job id.
# Writes ${NODE_OUT}/PREFLIGHT_REPORT.txt; its last line is "PREFLIGHT_NODE OK"
# or "PREFLIGHT_NODE FAILED". LOCAL_SMOKE=1 skips module load/conda (workstation
# test of this script only).

set -uo pipefail
if [[ "${LOCAL_SMOKE:-0}" != "1" ]]; then
    module load anaconda
    source activate maxsat
fi
cd ..

NODE_OUT="${NODE_OUT:-results/smoke_calib_2sat_sc_node}"
EXPECT_PYSAT="${EXPECT_PYSAT:-1.9.dev3}"
mkdir -p "$NODE_OUT"

python - "$NODE_OUT" "$EXPECT_PYSAT" "${LOCAL_SMOKE:-0}" <<'PYEOF' > "${NODE_OUT}/PREFLIGHT_REPORT.txt" 2>&1
import json, os, platform, sys
out, expect, local = sys.argv[1], sys.argv[2], sys.argv[3] == "1"
fails = []
def line(ok, msg):
    print(("ok    " if ok else "FAIL  ") + msg)
    if not ok:
        fails.append(msg)

print(f"host {platform.node()}  python {platform.python_version()}  "
      f"slurm_job {os.environ.get('SLURM_JOB_ID')}")
try:
    import pysat
    line(pysat.__version__ == expect, f"PySAT {pysat.__version__} (expected {expect})")
    from pysat.examples.rc2 import RC2  # noqa: F401
    import src.cli.profile_hardness, src.cli.solve_rc2_anytime, src.cli.run_opt_rc2  # noqa: F401,E401
    line(True, "RC2 and src.cli imports")
except Exception as e:  # noqa: BLE001
    line(False, f"import failed: {type(e).__name__}: {e}")

def last(path):
    try:
        rows = [json.loads(l) for l in open(path) if l.strip()]
        return rows[-1] if rows else None
    except (FileNotFoundError, json.JSONDecodeError):
        return None

for task, want in ((1, "completed"), (2, "censored")):
    r = last(os.path.join(out, f"task_{task}.jsonl"))
    if r is None:
        line(False, f"task {task}: no row (see scripts/logs/rc2-profile-*_{task}.out)")
        continue
    p = r["profile"]
    desc = (f"status={p['status']} solve_s={p['solve_s']} final_cost={p['final_cost']} "
            f"lower_bound={p['cost_lower_bound']}")
    if want == "completed":
        good = (p["completed"] is True and p["status"] == "optimal"
                and p["final_cost"] is not None and p["final_cost"] == p["cost_lower_bound"])
    else:
        good = (p["completed"] is False and p["status"] in ("timeout", "subprocess_killed")
                and p["cost_lower_bound"] is not None and p["final_cost"] is None)
    line(good, f"task {task} ({want} expected): {desc}")
    env = last(os.path.join(out, f"task_{task}.env.json"))
    if env is None:
        line(False, f"task {task}: no env record")
    else:
        line(env.get("pysat_version") == expect and (local or env.get("slurm_array_job_id")),
             f"task {task} env: pysat {env.get('pysat_version')} python {env.get('python')} "
             f"host {env.get('host')} array_job {env.get('slurm_array_job_id')}")

print("PREFLIGHT_NODE OK" if not fails else "PREFLIGHT_NODE FAILED")
PYEOF
cat "${NODE_OUT}/PREFLIGHT_REPORT.txt"
