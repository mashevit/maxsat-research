"""`generator: ksat_distinct` grids, and the calib_2sat_sc batch as data.

Plan: docs/current/CALIB_2SAT_SC.md. The batch file is checked here against
what the plan states (cells, m, seeds, separation from earlier batches); the
end-to-end tests run a small distinct grid through generate-grid and --check.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from instancegen import DISTINCT_GENERATOR_NAME, GENERATOR_NAME
from instancegen.cli import load_grid, main, render
from instancegen.generate import DistinctParams
from instancegen.validate import check_distinct_wcnf

REPO = Path(__file__).resolve().parents[2]
GRIDS = REPO / "instancegen" / "grids"
SC = GRIDS / "calib_2sat_sc.yaml"

SMALL_DISTINCT = """\
batch: t_distinct
generator: ksat_distinct
dialect: old
seeds: [201, 202]
families:
  - {family: max2sat_distinct, k: 2, n: [60, 90], alpha: [1.1, 1.2]}
"""


# --- calib_2sat_sc as data ----------------------------------------------------

def test_sc_grid_cells_and_m() -> None:
    g = load_grid(str(SC))
    assert g.batch == "calib_2sat_sc"
    assert g.generator == DISTINCT_GENERATOR_NAME
    assert g.dialect == "old"
    assert g.seeds == []  # every cell carries its own seed block
    got = {(c.k, c.n, c.alpha): g.gen_params(c, 201).m for c in g.cells}
    assert got == {
        (2, 2000, 1.10): 2200, (2, 2000, 1.15): 2300, (2, 2000, 1.20): 2400,
        (2, 8000, 1.10): 8800, (2, 8000, 1.15): 9200, (2, 8000, 1.20): 9600,
        (2, 32000, 1.10): 35200, (2, 32000, 1.15): 36800, (2, 32000, 1.20): 38400,
    }
    items = list(g.items())
    assert len(items) == 45
    assert all(isinstance(g.gen_params(c, s), DistinctParams) for c, s in items)


def test_sc_every_instance_has_its_own_seed() -> None:
    """No two cells share a seed, so no instance is a prefix of another
    (generate_distinct's prefix property, CALIB_2SAT_SC.md §3)."""
    g = load_grid(str(SC))
    seeds = [s for _, s in g.items()]
    assert sorted(seeds) == list(range(201, 246))
    assert all(len(g.cell_seeds(c)) == 5 for c in g.cells)


def test_sc_no_instance_is_a_prefix_of_another() -> None:
    g = load_grid(str(SC))
    by_n = {}
    for c, s in g.items():
        if c.n == 2000:
            by_n.setdefault(c.alpha, []).append(render(g, c, s)[1].clauses)
    for small in by_n[1.10]:
        for large in by_n[1.20]:
            assert large[:len(small)] != small


def test_sc_seeds_disjoint_from_every_earlier_batch() -> None:
    sc = {s for _, s in load_grid(str(SC)).items()}
    for name in ("calib_a", "calib_b", "calib_c"):
        g = load_grid(str(GRIDS / f"{name}.yaml"))
        used = {s for c in g.cells for s in g.cell_seeds(c)}
        assert sc & used == set(), name
    assert max(sc) < 1001  # the final-corpus range starts at 1001


def test_sc_filenames_and_cell_ids_do_not_collide_with_earlier_batches() -> None:
    sc = load_grid(str(SC))
    names = {render(sc, c, s)[2] for c, s in sc.items()}
    ids = {c.cell_id for c in sc.cells}
    assert len(names) == 45
    assert all(n.startswith("ksat_distinct_") for n in names)
    for name in ("calib_a", "calib_b", "calib_c"):
        g = load_grid(str(GRIDS / f"{name}.yaml"))
        assert ids & {c.cell_id for c in g.cells} == set()


def test_earlier_grids_still_weighted_ksat() -> None:
    for name in ("calib_a", "calib_b", "calib_c"):
        assert load_grid(str(GRIDS / f"{name}.yaml")).generator == GENERATOR_NAME


# --- end to end ---------------------------------------------------------------

def test_distinct_grid_end_to_end(tmp_path: Path) -> None:
    grid = tmp_path / "g.yaml"
    grid.write_text(SMALL_DISTINCT)
    root = tmp_path / "staging"
    assert main(["generate-grid", "--grid", str(grid), "--staging-root", str(root)]) == 0
    out = root / "data" / "generated" / "t_distinct"
    rows = [json.loads(l) for l in (out / "manifest.jsonl").read_text().splitlines()]
    assert len(rows) == 8
    for r in rows:
        assert r["generator"]["name"] == DISTINCT_GENERATOR_NAME
        assert r["generator"]["sampling"].startswith("uniform_clauses_without_replacement")
        assert r["m"] == round(r["alpha"] * r["n"])
        assert r["sizes"]["n_hard"] == 0 and r["sizes"]["total_soft_weight"] == r["m"]
        assert r["n_candidates_drawn"] == r["m"] + r["n_rejected_duplicates"]
        assert len(r["rejected_duplicates"]) == r["n_rejected_duplicates"]
        text = (root / r["instance"]).read_text()
        rep = check_distinct_wcnf(text, n=r["n"], k=r["k"], m=r["m"])
        assert rep["ok"], rep["problems"]
    slurm = (root / "scripts" / "manifest_t_distinct_rc2.txt").read_text().split()
    assert slurm == [r["instance"] for r in rows]
    assert main(["generate-grid", "--grid", str(grid), "--staging-root", str(root),
                 "--check"]) == 0
    # A second generation is byte-identical: files reported unchanged.
    first = {p.name: p.read_bytes() for p in out.glob("*.wcnf")}
    assert main(["generate-grid", "--grid", str(grid), "--staging-root", str(root)]) == 0
    assert {p.name: p.read_bytes() for p in out.glob("*.wcnf")} == first


def test_check_detects_tampering(tmp_path: Path) -> None:
    grid = tmp_path / "g.yaml"
    grid.write_text(SMALL_DISTINCT)
    root = tmp_path / "staging"
    main(["generate-grid", "--grid", str(grid), "--staging-root", str(root)])
    victim = next((root / "data" / "generated" / "t_distinct").glob("*.wcnf"))
    victim.write_text(victim.read_text().replace(" 0\n", " 0\n", 1) + "1 1 2 0\n")
    assert main(["generate-grid", "--grid", str(grid), "--staging-root", str(root),
                 "--check"]) == 1


@pytest.mark.parametrize("edit, match", [
    (("dialect: old", "dialect: new"), "dialect 'old' only"),
    (("dialect: old", "dialect: old\nparams: {w_max: 4}"), "takes no params"),
    (("generator: ksat_distinct", "generator: nope"), "unknown generator"),
])
def test_bad_distinct_grids_rejected(tmp_path: Path, edit, match: str) -> None:
    grid = tmp_path / "g.yaml"
    grid.write_text(SMALL_DISTINCT.replace(*edit))
    with pytest.raises(ValueError, match=match):
        load_grid(str(grid))


def test_missing_seeds_rejected(tmp_path: Path) -> None:
    grid = tmp_path / "g.yaml"
    grid.write_text(SMALL_DISTINCT.replace("seeds: [201, 202]\n", ""))
    with pytest.raises(ValueError, match="no top-level seeds"):
        load_grid(str(grid))


def test_impossible_distinct_cell_fails_loudly(tmp_path: Path) -> None:
    grid = tmp_path / "g.yaml"
    grid.write_text(SMALL_DISTINCT.replace("n: [60, 90], alpha: [1.1, 1.2]",
                                           "n: [3], alpha: [5]"))  # m=15 > 12
    with pytest.raises(ValueError, match="exceeds the 12 distinct clauses"):
        main(["generate-grid", "--grid", str(grid), "--staging-root", str(tmp_path / "s")])


def test_smoke_grid_is_outside_the_batch() -> None:
    """The preflight's smoke instances (CALIB_2SAT_SC.md §9a) never share a seed
    or a file with the batch."""
    smoke = load_grid(str(GRIDS / "calib_2sat_sc_smoke.yaml"))
    sc = load_grid(str(SC))
    assert {s for _, s in smoke.items()} == {9001, 9002}
    assert {s for _, s in smoke.items()} & {s for _, s in sc.items()} == set()
    assert ({render(smoke, c, s)[2] for c, s in smoke.items()}
            & {render(sc, c, s)[2] for c, s in sc.items()}) == set()
