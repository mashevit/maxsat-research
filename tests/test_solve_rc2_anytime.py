"""Tests for src.cli.solve_rc2_anytime."""
from __future__ import annotations

import os

from src.cli.solve_rc2_anytime import solve_rc2_with_timeout

MINI_WCNF = "data/toy/mini.wcnf"
MINI_WCNF_EXPECTED_COST = 3  # confirmed independently via PySAT RC2


def _synth_tiny_wcnf(tmp_path):
    """Fallback instance: 2-var WCNF with optimum cost 0 (all clauses sat)."""
    p = tmp_path / "tiny.wcnf"
    # top=10; soft clauses (1, x1 v -x2), (1, -x1 v x2) — both satisfiable.
    p.write_text("p wcnf 2 2 10\n1 1 -2 0\n1 -1 2 0\n")
    return str(p), 0


def _instance(tmp_path):
    if os.path.exists(MINI_WCNF):
        return MINI_WCNF, MINI_WCNF_EXPECTED_COST
    return _synth_tiny_wcnf(tmp_path)


def test_optimal_on_tiny_instance(tmp_path):
    path, expected_cost = _instance(tmp_path)
    res = solve_rc2_with_timeout(path, timeout_s=5.0, solver="g3")
    assert res.status == "optimal", f"expected optimal, got {res.status!r} (error={res.error!r})"
    assert res.cost == expected_cost
    assert res.cost_lower_bound == expected_cost
    assert res.model is not None
    assert res.n_vars > 0
    assert res.n_clauses == res.n_hard + res.n_soft
    assert res.error is None


def test_tight_timeout_yields_optimal_or_timeout(tmp_path):
    path, _ = _instance(tmp_path)
    res = solve_rc2_with_timeout(path, timeout_s=0.001, solver="g3")
    # A trivially small instance may finish before the alarm fires; accept either.
    assert res.status in ("optimal", "timeout"), (
        f"unexpected status {res.status!r} (error={res.error!r})"
    )
    assert res.elapsed_s < 1.0, f"elapsed_s={res.elapsed_s!r} too high"
    if res.status == "timeout":
        assert res.cost is None
        assert res.model is None
        # cost_lower_bound may be 0 or higher; just ensure non-negative if present.
        if res.cost_lower_bound is not None:
            assert res.cost_lower_bound >= 0


if __name__ == "__main__":  # allow running without pytest installed
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        import pathlib

        tp = pathlib.Path(td)
        test_optimal_on_tiny_instance(tp)
        test_tight_timeout_yields_optimal_or_timeout(tp)
    print("OK")
