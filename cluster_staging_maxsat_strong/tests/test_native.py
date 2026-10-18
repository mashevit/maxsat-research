"""B5: the C polish core equals the Python twin (src/sat/ls_v3.py with PortableRng).

docs/current2/STRONGER_MEMETIC_DESIGN.md §7. The build goes through
scripts/build_native.sh into a temporary directory (MAXSAT_NATIVE_BUILD_DIR), so
the test never touches the tree's own build. Skipped when no C compiler exists.

- the RNG streams agree;
- walksat_v3 (tabu none / tenure / cc; soft-only, weighted, hard; noops on/off)
  and dls_v3 (cc off/on; call and run weights) make the same flips: equal
  final assignments, step and flip counts, best costs and counters;
- a stale build (source changed) and a missing build are refused, and the
  shard runner refuses `ls.native: true` without a valid build (exit 2).
"""
from __future__ import annotations

import json
import os
import random
import shutil
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
TREE = os.path.dirname(HERE)
SRC = os.path.join(TREE, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from sat.cnf import WCNF  # noqa: E402
from sat.ls_v3 import dls_v3, init_dynamic_weights, walksat_v3  # noqa: E402
from sat.rng import PortableRng  # noqa: E402

pytestmark = pytest.mark.skipif(shutil.which("cc") is None and shutil.which("gcc") is None,
                                reason="no C compiler")


@pytest.fixture(scope="module")
def native(tmp_path_factory):
    d = tmp_path_factory.mktemp("native_build")
    env = dict(os.environ, MAXSAT_NATIVE_BUILD_DIR=str(d))
    subprocess.run(["bash", os.path.join(TREE, "scripts", "build_native.sh")], check=True, env=env,
                   capture_output=True)
    old = os.environ.get("MAXSAT_NATIVE_BUILD_DIR")
    os.environ["MAXSAT_NATIVE_BUILD_DIR"] = str(d)
    import native.native as nat
    nat._LIB = None
    yield nat
    nat._LIB = None
    if old is None:
        os.environ.pop("MAXSAT_NATIVE_BUILD_DIR", None)
    else:
        os.environ["MAXSAT_NATIVE_BUILD_DIR"] = old


def make_wcnf(tmp_path, name, n, k, m_soft, m_hard=0, w_max=1, seed=0, mixed_k=False):
    rng = random.Random(seed)
    top = m_soft * w_max + 1
    lines = []
    for i in range(m_hard + m_soft):
        kk = rng.randint(1, k) if mixed_k else k
        vs = rng.sample(range(1, n + 1), kk)
        lits = [v if rng.random() < 0.5 else -v for v in vs]
        w = top if i < m_hard else rng.randint(1, w_max)
        lines.append(f"{w} " + " ".join(map(str, lits)) + " 0")
    path = tmp_path / f"{name}.wcnf"
    path.write_text(f"p wcnf {n} {len(lines)} {top}\n" + "\n".join(lines) + "\n")
    return WCNF.parse_dimacs(str(path))


def start(n, seed):
    r = random.Random(seed)
    return [r.random() < 0.5 for _ in range(n)]


CASES = [
    dict(n=60, k=2, m_soft=130),
    dict(n=50, k=3, m_soft=220, w_max=4),
    dict(n=40, k=3, m_soft=120, m_hard=30, w_max=3),
    dict(n=30, k=2, m_soft=70, m_hard=15),
    dict(n=30, k=4, m_soft=90, m_hard=10, w_max=5, mixed_k=True),
]
KEYS = ("flips", "total_flips", "best_soft_weight", "hard_violations", "final_assign", "noop_steps")


def test_rng_streams_agree(native):
    for seed in (0, 1, 12345, 2 ** 40 + 7):
        r = PortableRng(seed)
        assert native.rng_stream(seed, 50) == [r.next() for _ in range(50)]


@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("tabu,tenure,trand", [("none", 0, 0), ("tenure", 7, 0), ("tenure", 4, 3), ("cc", 0, 0)])
@pytest.mark.parametrize("noops", [False, True])
def test_walksat_c_equals_python_twin(native, tmp_path, case, tabu, tenure, trand, noops):
    if case.get("m_hard") and not noops:
        # v2's rule: with hard clauses only applied flips count, so a stuck call
        # runs to its time limit -- both twins would loop forever without one.
        pytest.skip("hard instance without no-op counting needs a time limit")
    w = make_wcnf(tmp_path, "c", seed=3, **case)
    core = native.NativeCore(w)
    for seed in range(3):
        s0 = start(case["n"], 50 + seed)
        sa, sb = {}, {}
        a = walksat_v3(w, s0, rng=PortableRng(seed), max_flips=700, time_limit_s=None, noise=0.15,
                       hard_safe=True, budget_counts_noops=noops, tabu=tabu, tenure=tenure,
                       tenure_rand=trand, stats=sa)
        b = core.walksat(s0, seed, 700, None, noise=0.15, hard_safe=True, budget_counts_noops=noops,
                         tabu=tabu, tenure=tenure, tenure_rand=trand, stats=sb)
        for k in KEYS:
            assert a[k] == b[k], (k, seed)
        assert sa == sb


@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("cc", [False, True])
@pytest.mark.parametrize("sp,zeta,h_inc,t", [(0.01, 50, 1, 15), (0.2, 4, 2, 5), (0.0, 1000, 3, 42)])
def test_dls_c_equals_python_twin(native, tmp_path, case, cc, sp, zeta, h_inc, t):
    w = make_wcnf(tmp_path, "c", seed=5, **case)
    core = native.NativeCore(w)
    for seed in range(3):
        s0 = start(case["n"], 70 + seed)
        sa, sb = {}, {}
        a = dls_v3(w, s0, rng=PortableRng(seed), max_flips=700, time_limit_s=None, t=t, sp=sp,
                   zeta=zeta, h_inc=h_inc, cc=cc, stats=sa)
        b = core.dls(s0, seed, 700, None, t=t, sp=sp, zeta=zeta, h_inc=h_inc, cc=cc, stats=sb)
        for k in KEYS:
            assert a[k] == b[k], (k, seed)
        assert sa == sb


def test_dls_run_weights_c_equals_python(native, tmp_path):
    w = make_wcnf(tmp_path, "c", n=50, k=2, m_soft=120, seed=9)
    core = native.NativeCore(w)
    dwa, dwb = init_dynamic_weights(w), init_dynamic_weights(w)
    for call in range(4):
        s0 = start(50, call)
        a = dls_v3(w, s0, rng=PortableRng(call), max_flips=300, time_limit_s=None, zeta=8, dw=dwa)
        b = core.dls(s0, call, 300, None, zeta=8, dw=dwb)
        assert a["final_assign"] == b["final_assign"]
        assert dwa == dwb


def test_c_core_is_faster(native, tmp_path):
    import time
    w = make_wcnf(tmp_path, "big", n=4000, k=2, m_soft=4800, seed=1)
    core = native.NativeCore(w)
    s0 = start(4000, 0)
    t0 = time.perf_counter()
    walksat_v3(w, s0, rng=PortableRng(1), max_flips=20000, time_limit_s=None)
    tp = time.perf_counter() - t0
    t0 = time.perf_counter()
    core.walksat(s0, 1, 20000, None)
    tc = time.perf_counter() - t0
    assert tc < tp  # recorded, not asserted beyond "faster": speed is measured on the cluster


def test_stale_and_missing_builds_are_refused(native, tmp_path, monkeypatch):
    d = tmp_path / "copy"
    shutil.copytree(native.build_dir(), d)
    monkeypatch.setenv("MAXSAT_NATIVE_BUILD_DIR", str(d))
    native.build_info()
    info = (d / "BUILD_INFO.txt").read_text().replace("source_sha256=", "source_sha256=0")
    (d / "BUILD_INFO.txt").write_text(info)
    with pytest.raises(native.NativeUnavailable):
        native.build_info()
    monkeypatch.setenv("MAXSAT_NATIVE_BUILD_DIR", str(tmp_path / "nothing"))
    with pytest.raises(native.NativeUnavailable):
        native.build_info()


def test_shard_refuses_native_without_build_and_runs_with_it(native, tmp_path, monkeypatch):
    import yaml
    from cli import run_memetic_shard as shard
    w_path = tmp_path / "s.wcnf"
    rng = random.Random(1)
    lines = []
    for _ in range(100):
        vs = rng.sample(range(1, 51), 2)
        lines.append("1 " + " ".join(str(v if rng.random() < 0.5 else -v) for v in vs) + " 0")
    w_path.write_text("p wcnf 50 100 101\n" + "\n".join(lines) + "\n")
    cfg = {"impl": "v3", "ea": {"pop_size": 6, "max_gens": 2, "deadline_mode": "clip", "crossover": "px",
                                "mutation": "walk", "mutation_k": 4},
           "ls": {"ls_polish_flips": 200, "flip_budget": 200, "time_limit_s": 1.0, "core": "dls",
                  "tabu": "cc", "native": True}}
    cp = tmp_path / "n.yaml"
    cp.write_text(yaml.safe_dump(cfg))
    out = tmp_path / "o.jsonl"
    args = ["--instance", str(w_path), "--config", str(cp), "--seed", "1", "--budget-s", "5", "--out", str(out)]
    assert shard.main(args) == 0
    r = json.loads(out.read_text().strip().splitlines()[-1])
    assert r["status"] == "ok" and r["v3"]["ls_native"] is True
    assert r["native_build"]["source_sha256"] and r["native_build"]["compiler"]
    monkeypatch.setenv("MAXSAT_NATIVE_BUILD_DIR", str(tmp_path / "nothing"))
    assert shard.main(args[:-1] + [str(tmp_path / "o2.jsonl")]) == 2
