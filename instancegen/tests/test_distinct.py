"""Distinct-clause mode: generate.generate_distinct, validate.py, the CLI.

Contract: docs/current/RESEARCH_NOTES_DISTINCT_CLAUSE_GENERATOR.md. The last
section pins the original generate() output, so adding this mode is shown not
to have changed calib_a/b/c's generator.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter

import pytest

from instancegen import DISTINCT_GENERATOR_NAME, GENERATOR_NAME
from instancegen.cli import main
from instancegen.generate import (
    DistinctParams,
    GenParams,
    canonical,
    distinct_filename,
    generate,
    generate_distinct,
    n_possible_clauses,
)
from instancegen.validate import check_distinct_wcnf
from instancegen.wcnf_io import format_wcnf

BASE = DistinctParams(n_vars=50, k=2, m=300, seed=7)


def _text(p: DistinctParams) -> str:
    return format_wcnf(generate_distinct(p).instance, dialect="old")


# --- per-clause contract -----------------------------------------------------

@pytest.mark.parametrize("p", [
    BASE,
    DistinctParams(n_vars=30, k=3, m=500, seed=1),
    DistinctParams(n_vars=8, k=2, m=100, seed=3),   # 89% of the 112-clause space
    DistinctParams(n_vars=6, k=1, m=12, seed=4),    # the whole k=1 space
])
def test_clause_contract(p: DistinctParams) -> None:
    inst = generate_distinct(p).instance
    assert inst.n_vars == p.n_vars
    assert len(inst.clauses) == p.m
    keys = set()
    for cl in inst.clauses:
        assert len(cl.lits) == p.k
        assert all(1 <= abs(l) <= p.n_vars for l in cl.lits)
        assert len({abs(l) for l in cl.lits}) == p.k          # distinct vars
        assert not any(-l in cl.lits for l in cl.lits)        # no tautology
        assert cl.lits == canonical(cl.lits)                  # sorted by |var|
        assert cl.weight == 1 and not cl.is_hard
        keys.add(frozenset(cl.lits))                          # order-insensitive
    assert len(keys) == p.m
    assert inst.top == p.m + 1
    report = check_distinct_wcnf(format_wcnf(inst, dialect="old"),
                                 n=p.n_vars, k=p.k, m=p.m)
    assert report["ok"], report["problems"]


def test_polarity_and_variables_roughly_uniform() -> None:
    """Loose sanity bounds, not a test of the RNG: about half the literals
    positive and every variable used."""
    p = DistinctParams(n_vars=200, k=3, m=4000, seed=11)
    lits = [l for cl in generate_distinct(p).instance.clauses for l in cl.lits]
    frac_pos = sum(l > 0 for l in lits) / len(lits)
    assert 0.48 < frac_pos < 0.52
    counts = Counter(abs(l) for l in lits)
    assert len(counts) == p.n_vars
    # Chi-square against uniform: df = n - 1 = 199, sd = sqrt(2 df) ~ 20; a
    # 5-sd ceiling only catches a grossly non-uniform variable draw.
    mean = len(lits) / p.n_vars
    chi2 = sum((c - mean) ** 2 / mean for c in counts.values())
    df = p.n_vars - 1
    assert chi2 < df + 5 * (2 * df) ** 0.5


# --- reproducibility ---------------------------------------------------------

def test_same_seed_same_bytes() -> None:
    assert _text(BASE) == _text(BASE)
    a, b = generate_distinct(BASE), generate_distinct(BASE)
    assert a.rejected == b.rejected


def test_different_seed_differs() -> None:
    assert _text(BASE) != _text(DistinctParams(BASE.n_vars, BASE.k, BASE.m, BASE.seed + 1))


def test_prefix_property() -> None:
    """Acceptance order is the output order: a smaller m with the same seed is
    a prefix of a larger one."""
    small = generate_distinct(DistinctParams(50, 2, 100, 7)).instance.clauses
    large = generate_distinct(BASE).instance.clauses
    assert large[:100] == small


def test_filename_distinct_from_old_mode() -> None:
    assert distinct_filename(BASE) == "ksat_distinct_v50_k2_m300_s7.wcnf"
    assert not distinct_filename(BASE).startswith("wksat_")


# --- rejected candidates -----------------------------------------------------

def test_rejections_recorded_when_dense() -> None:
    p = DistinctParams(n_vars=4, k=2, m=24, seed=5)         # the full space
    assert n_possible_clauses(4, 2) == 24
    res = generate_distinct(p)
    accepted = set(c.lits for c in res.instance.clauses)
    assert len(accepted) == 24
    assert len(res.rejected) > 0
    assert all(r in accepted for r in res.rejected)
    assert all(r == canonical(r) for r in res.rejected)


def test_sparse_request_rarely_rejects() -> None:
    res = generate_distinct(DistinctParams(n_vars=10_000, k=2, m=2000, seed=1))
    assert len(res.rejected) <= 2   # expected m^2 / (2N) ~ 0.005


# --- boundaries --------------------------------------------------------------

def test_m_zero() -> None:
    res = generate_distinct(DistinctParams(n_vars=5, k=2, m=0, seed=1))
    assert res.instance.clauses == () and res.rejected == ()
    text = format_wcnf(res.instance, dialect="old")
    assert text == "p wcnf 5 0 1\n"
    assert check_distinct_wcnf(text, n=5, k=2, m=0)["ok"]


def test_k_equals_n_full_space() -> None:
    p = DistinctParams(n_vars=3, k=3, m=8, seed=2)
    inst = generate_distinct(p).instance
    assert sorted(c.lits for c in inst.clauses) == sorted(
        canonical((a * 1, b * 2, c * 3)) for a in (1, -1) for b in (1, -1) for c in (1, -1))


@pytest.mark.parametrize("n,k,m,msg", [
    (5, 0, 1, "k must be >= 1"),
    (3, 4, 1, "exceeds n_vars"),
    (5, 2, -1, "m must be >= 0"),
    (4, 2, 25, "exceeds the 24 distinct clauses"),
    (3, 3, 9, "exceeds the 8 distinct clauses"),
    (1, 1, 3, "exceeds the 2 distinct clauses"),
])
def test_impossible_requests_rejected(n: int, k: int, m: int, msg: str) -> None:
    with pytest.raises(ValueError, match=msg):
        generate_distinct(DistinctParams(n_vars=n, k=k, m=m, seed=1))


# --- the validator catches each violation ------------------------------------

@pytest.mark.parametrize("body,field", [
    ("1 1 2 0\n1 2 1 0\n", "duplicates"),          # same clause, literal order swapped
    ("1 1 -1 0\n1 2 3 0\n", "tautologies"),
    ("1 1 1 0\n1 2 3 0\n", "repeated_variable"),
    ("1 1 2 3 0\n1 2 3 0\n", "wrong_length"),
    ("1 1 9 0\n1 2 3 0\n", "out_of_range"),
    ("2 1 2 0\n1 2 3 0\n", "non_unit_weight"),
])
def test_validator_flags(body: str, field: str) -> None:
    report = check_distinct_wcnf("p wcnf 5 2 3\n" + body, n=5, k=2, m=2)
    assert not report["ok"]
    assert report[field] == 1


def test_validator_flags_count_and_top() -> None:
    assert not check_distinct_wcnf("p wcnf 5 1 2\n1 1 2 0\n", n=5, k=2, m=2)["ok"]
    assert not check_distinct_wcnf("p wcnf 5 1 99\n1 1 2 0\n", n=5, k=2, m=1)["ok"]


# --- CLI ---------------------------------------------------------------------

def test_cli_writes_instance_and_metadata(tmp_path) -> None:
    rc = main(["generate-distinct", "--n", "40", "--k", "2", "--m", "120",
               "--seed", "3", "--out-dir", str(tmp_path)])
    assert rc == 0
    wcnf = tmp_path / "ksat_distinct_v40_k2_m120_s3.wcnf"
    meta = json.loads(wcnf.with_suffix(".json").read_text())
    assert meta["generator"]["name"] == DISTINCT_GENERATOR_NAME != GENERATOR_NAME
    assert meta["generator"]["params"] == {"n_vars": 40, "k": 2, "m": 120, "seed": 3}
    assert meta["instance_sha256"] == hashlib.sha256(wcnf.read_bytes()).hexdigest()
    assert meta["n_candidates_drawn"] == 120 + meta["n_rejected_duplicates"]
    assert meta["validation"]["ok"] is True
    assert wcnf.read_text() == _text(DistinctParams(40, 2, 120, 3))


def test_cli_impossible_request(tmp_path) -> None:
    with pytest.raises(SystemExit, match="exceeds"):
        main(["generate-distinct", "--n", "4", "--k", "2", "--m", "25",
              "--seed", "1", "--out-dir", str(tmp_path)])


# --- the original generator is unchanged -------------------------------------

@pytest.mark.parametrize("p,sha", [
    # == sha256 of cluster_staging_maxsat/data/generated/calib_a/
    #    wksat_v100_k2_sr6.00_hr0.00_w1_uniform_s1.wcnf
    (GenParams(n_vars=100, k=2, soft_ratio=6.0, hard_ratio=0.0, w_max=1, seed=1),
     "0a3b3189ef31359aa5511242ce45b618affcd83ae9a830936abff29afd6f2da3"),
    (GenParams(n_vars=40, k=3, soft_ratio=4.0, hard_ratio=0.5, w_max=16, seed=7),
     "ce5f485a1ca9e76b37d35aed6e1028bdcfa14d1c92a01ea1e584650402f97e8a"),
])
def test_original_generator_bytes_pinned(p: GenParams, sha: str) -> None:
    text = format_wcnf(generate(p), dialect="old")
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == sha
