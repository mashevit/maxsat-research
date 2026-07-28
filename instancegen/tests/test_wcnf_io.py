"""Step 2 tests: docs/INSTANCEGEN_PLAN.md §12 tests 1 (files), 2, 3, 4, 5.

Fails before instancegen/wcnf_io.py exists; passes after.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from instancegen.generate import GenParams, generate
from instancegen.wcnf_io import emit_order, format_wcnf, write_wcnf
from maxsat_new.cnf import WCNF

BASE = GenParams(
    n_vars=30,
    k=3,
    soft_ratio=4.0,
    hard_ratio=0.5,
    w_max=16,
    seed=11,
)


# --- §12 test 1 (file half): byte-identity ----------------------------------

@pytest.mark.parametrize("dialect", ["old", "new"])
def test_determinism_bytes(tmp_path, dialect: str) -> None:
    inst_a = generate(BASE)
    inst_b = generate(BASE)
    a = tmp_path / f"a_{dialect}.wcnf"
    b = tmp_path / f"b_{dialect}.wcnf"
    write_wcnf(inst_a, str(a), dialect=dialect)
    write_wcnf(inst_b, str(b), dialect=dialect)
    # Raw bytes, not parsed content.
    assert a.read_bytes() == b.read_bytes()
    assert a.read_bytes() != b""


@pytest.mark.parametrize("dialect", ["old", "new"])
def test_different_seeds_give_different_bytes(tmp_path, dialect: str) -> None:
    """Guards a degenerate writer that ignores its input (§12 test 1)."""
    a = tmp_path / f"s1_{dialect}.wcnf"
    b = tmp_path / f"s2_{dialect}.wcnf"
    write_wcnf(generate(BASE), str(a), dialect=dialect)
    write_wcnf(generate(replace(BASE, seed=BASE.seed + 1)), str(b), dialect=dialect)
    assert a.read_bytes() != b.read_bytes()


def test_matches_pysat_to_fp() -> None:
    """§9 claims both dialects are diff-comparable against pysat's writer."""
    import io

    from pysat.formula import WCNF as PysatWCNF

    inst = generate(BASE)
    pw = PysatWCNF()
    for cl in inst.hard_clauses:
        pw.append(list(cl.lits))
    for cl in inst.soft_clauses:
        pw.append(list(cl.lits), weight=cl.weight)

    for dialect, pysat_format in (("old", "legacy"), ("new", "mse22")):
        buf = io.StringIO()
        pw.to_fp(buf, format=pysat_format)
        assert format_wcnf(inst, dialect=dialect) == buf.getvalue(), dialect


def test_no_volatile_content_in_file(tmp_path) -> None:
    """created_utc / git_sha belong in the manifest only (§10.3)."""
    path = tmp_path / "x.wcnf"
    write_wcnf(generate(BASE), str(path), dialect="old")
    text = path.read_text(encoding="utf-8")
    assert "\r" not in text
    assert not any(line.startswith("c ") for line in text.splitlines())


# --- §12 test 2: round-trip through this repo's own parser -------------------

def test_roundtrip_old(tmp_path) -> None:
    inst = generate(BASE)
    path = tmp_path / "rt.wcnf"
    write_wcnf(inst, str(path), dialect="old")

    parsed = WCNF.parse_dimacs(str(path))

    assert parsed.n_vars == inst.n_vars
    assert len(parsed.clauses) == len(inst.clauses)
    assert parsed.hard_weight == inst.top

    expected = emit_order(inst)      # softs first, then hards (§9)
    assert len(expected) == len(parsed.clauses)
    for mine, theirs in zip(expected, parsed.clauses):
        assert theirs.weight == mine.weight
        assert tuple(theirs.lits) == mine.lits   # order preserved
        assert theirs.is_hard == mine.is_hard

    n_hard = sum(1 for c in parsed.clauses if c.is_hard)
    assert n_hard == BASE.n_hard
    assert len(parsed.clauses) - n_hard == BASE.n_soft


def test_roundtrip_old_pure_soft(tmp_path) -> None:
    """hard_ratio=0 must still round-trip (no hard clauses, top = 1+sum)."""
    inst = generate(replace(BASE, hard_ratio=0.0))
    path = tmp_path / "soft.wcnf"
    write_wcnf(inst, str(path), dialect="old")
    parsed = WCNF.parse_dimacs(str(path))
    assert not any(c.is_hard for c in parsed.clauses)
    assert len(parsed.clauses) == BASE.n_soft


# --- §12 test 3: the new dialect is NOT readable here (§9.1) -----------------

def test_new_dialect_not_parseable(tmp_path) -> None:
    """Pins the §9.1 mismatch. Fails loudly if parse_dimacs is ever extended."""
    inst = generate(BASE)
    path = tmp_path / "new.wcnf"
    write_wcnf(inst, str(path), dialect="new")
    with pytest.raises(ValueError):
        WCNF.parse_dimacs(str(path))


def test_new_dialect_shape(tmp_path) -> None:
    inst = generate(BASE)
    path = tmp_path / "new2.wcnf"
    write_wcnf(inst, str(path), dialect="new")
    lines = path.read_text(encoding="utf-8").splitlines()
    assert not any(line.startswith("p ") for line in lines)
    assert sum(1 for line in lines if line.startswith("h ")) == BASE.n_hard
    assert len(lines) == BASE.n_hard + BASE.n_soft
    # Softs first, then hards -- same order as "old" (§9).
    assert not lines[0].startswith("h ")
    assert lines[-1].startswith("h ")


# --- §12 test 4: no line the parser would silently drop (§9.5) --------------

@pytest.mark.parametrize("dialect", ["old", "new"])
@pytest.mark.parametrize("weight_dist", ["uniform", "few_classes:3", "powerlaw:2.0"])
def test_no_dropped_clause_lines(tmp_path, dialect: str, weight_dist: str) -> None:
    inst = generate(replace(BASE, weight_dist=weight_dist, w_max=32))
    path = tmp_path / "drop.wcnf"
    write_wcnf(inst, str(path), dialect=dialect)
    for line in path.read_text(encoding="utf-8").splitlines():
        assert line, "no blank lines"
        assert not line.startswith("0"), f"line would be dropped by cnf.py:57: {line}"
        assert not line.startswith("%"), f"line would be dropped by cnf.py:57: {line}"
    assert all(c.weight >= 1 for c in inst.soft_clauses)


# --- §12 test 5: dialect is required ----------------------------------------

def test_dialect_required(tmp_path) -> None:
    inst = generate(BASE)
    path = str(tmp_path / "d.wcnf")
    with pytest.raises(TypeError):
        write_wcnf(inst, path)          # type: ignore[call-arg]
    with pytest.raises(ValueError):
        write_wcnf(inst, path, dialect="mse22")
    with pytest.raises(ValueError):
        format_wcnf(inst, dialect="OLD")   # case-sensitive, no silent coercion


def test_dialect_positional_is_rejected(tmp_path) -> None:
    """Keyword-only: a positional third argument must not sneak in."""
    inst = generate(BASE)
    with pytest.raises(TypeError):
        write_wcnf(inst, str(tmp_path / "p.wcnf"), "old")  # type: ignore[misc]
