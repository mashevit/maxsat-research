"""M1 tests for instancegen.cli (docs/CORPUS_CALIBRATION_GOALS.md §6 M1).

Run from the repo root: python -m pytest instancegen -q
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from instancegen.cli import Cell, load_grid, main, render

REPO = Path(__file__).resolve().parents[2]
CALIB_A = REPO / "instancegen" / "grids" / "calib_a.yaml"
CALIB_B = REPO / "instancegen" / "grids" / "calib_b.yaml"

SMALL_GRID = """\
batch: t_small
dialect: old
params: {hard_ratio: 0.0, w_max: 1, weight_dist: uniform}
seeds: [1, 2]
families:
  - {family: max3sat, k: 3, n: [20, 30], alpha: [4.26, 5]}
  - {family: max2sat, k: 2, n: [25], alpha: [2, 3]}
"""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --- calib_a grid as data ---------------------------------------------------

def test_calib_a_grid_shape() -> None:
    g = load_grid(str(CALIB_A))
    assert g.batch == "calib_a"
    assert g.dialect == "old"
    assert g.seeds == [1, 2, 3, 4, 5]
    assert len(g.cells) == 36
    assert sum(1 for c in g.cells if c.k == 3) == 20
    assert sum(1 for c in g.cells if c.k == 2) == 16
    items = list(g.items())
    assert len(items) == 180
    names = [render(g, c, s)[2] for c, s in items]
    assert len(set(names)) == 180


def test_calib_a_is_pure_soft_unit_weight_and_m_is_round_alpha_n() -> None:
    g = load_grid(str(CALIB_A))
    for cell in g.cells:
        p = g.gen_params(cell, 1)
        assert p.hard_ratio == 0.0 and p.w_max == 1 and p.weight_dist == "uniform"
        assert p.n_hard == 0
        assert p.n_soft == int(round(cell.alpha * cell.n))
        assert p.k == cell.k


def test_calib_a_reproduces_pilot_cells() -> None:
    """Two calib_a cells coincide with pilot files whose optima are on record
    (results/profile/gen_pilot_cap60.jsonl: c* = 6 and 25). The bytes must be
    the pilot's bytes, i.e. the same filename from the same GenParams."""
    g = load_grid(str(CALIB_A))
    by_id = {c.cell_id: c for c in g.cells}
    _, _, name3, _ = render(g, by_id["max3sat_n50_a6"], 1)
    _, _, name2, _ = render(g, by_id["max2sat_n100_a4"], 1)
    assert name3 == "wksat_v50_k3_sr6.00_hr0.00_w1_uniform_s1.wcnf"
    assert name2 == "wksat_v100_k2_sr4.00_hr0.00_w1_uniform_s1.wcnf"


def test_cell_id_format() -> None:
    assert Cell("max3sat", 3, 250, 4.26).cell_id == "max3sat_n250_a4.26"
    assert Cell("max2sat", 2, 100, 2.0).cell_id == "max2sat_n100_a2"


# --- calib_b: the alpha-refinement grid (docs/CALIB_B_PLAN.md) --------------

def test_calib_b_grid_shape() -> None:
    g = load_grid(str(CALIB_B))
    assert g.batch == "calib_b"
    assert g.dialect == "old"
    assert len(g.cells) == 22
    items = list(g.items())
    assert len(items) == 110
    names = [render(g, c, s)[2] for c, s in items]
    assert len(set(names)) == 110


def test_calib_b_cell_kinds_and_seed_ranges() -> None:
    """17 exploratory cells at seeds 1-5, 5 reinforcement cells at 6-10
    (plan §4a/§4b). The reinforcement seeds must be disjoint from calib_a's
    1-5 and from the final corpus's 1001-1020, or instances would be
    regenerated rather than added."""
    g = load_grid(str(CALIB_B))
    explore = [c for c in g.cells if g.cell_seeds(c) == [1, 2, 3, 4, 5]]
    reinforce = [c for c in g.cells if g.cell_seeds(c) == [6, 7, 8, 9, 10]]
    assert len(explore) == 17 and len(reinforce) == 5
    assert len(explore) + len(reinforce) == len(g.cells)
    assert {c.cell_id for c in reinforce} == {
        "max3sat_n50_a8", "max3sat_n70_a6", "max3sat_n250_a4.26",
        "max2sat_n150_a3", "max2sat_n400_a2",
    }


def test_calib_b_reinforcement_cells_exist_in_calib_a_and_explore_cells_do_not() -> None:
    """Reinforcement cells must be calib_a cells (same (k, n, alpha)) so the
    extra seeds enlarge an existing cell; exploratory cells must be new, or
    the round would re-measure what A1 already measured."""
    a = {(c.k, c.n, c.alpha) for c in load_grid(str(CALIB_A)).cells}
    g = load_grid(str(CALIB_B))
    for cell in g.cells:
        key = (cell.k, cell.n, cell.alpha)
        if g.cell_seeds(cell) == [6, 7, 8, 9, 10]:
            assert key in a, f"reinforcement cell {cell.cell_id} is not a calib_a cell"
        else:
            assert key not in a, f"exploratory cell {cell.cell_id} duplicates calib_a"


def test_calib_b_shares_calib_a_generator_conventions() -> None:
    a = load_grid(str(CALIB_A))
    g = load_grid(str(CALIB_B))
    assert g.params == a.params and g.dialect == a.dialect
    for cell in g.cells:
        p = g.gen_params(cell, 1)
        assert p.hard_ratio == 0.0 and p.w_max == 1 and p.weight_dist == "uniform"
        assert p.n_hard == 0
        assert p.n_soft == int(round(cell.alpha * cell.n))


def test_calib_b_filenames_are_disjoint_from_calib_a() -> None:
    """Different batches write to different directories, but a filename
    collision would still mean two identical instances counted twice in a
    pooled Tier-2 manifest."""
    a = load_grid(str(CALIB_A))
    g = load_grid(str(CALIB_B))
    names_a = {render(a, c, s)[2] for c, s in a.items()}
    names_b = {render(g, c, s)[2] for c, s in g.items()}
    assert names_a & names_b == set()


# --- per-family seed override ----------------------------------------------

def test_per_family_seeds_override_top_level(tmp_path: Path) -> None:
    grid = tmp_path / "g.yaml"
    grid.write_text(SMALL_GRID.replace(
        "  - {family: max2sat, k: 2, n: [25], alpha: [2, 3]}",
        "  - {family: max2sat, k: 2, n: [25], alpha: [2, 3], seeds: [7, 8, 9]}"))
    g = load_grid(str(grid))
    assert g.seeds == [1, 2]
    by_id = {c.cell_id: c for c in g.cells}
    assert g.cell_seeds(by_id["max3sat_n20_a4.26"]) == [1, 2]
    assert g.cell_seeds(by_id["max2sat_n25_a2"]) == [7, 8, 9]
    assert len(list(g.items())) == 4 * 2 + 2 * 3
    root = tmp_path / "staging"
    assert main(["generate-grid", "--grid", str(grid), "--staging-root", str(root)]) == 0
    rows = [json.loads(l) for l in
            (root / "data" / "generated" / "t_small" / "manifest.jsonl").read_text().splitlines()]
    assert len(rows) == 14
    assert sorted(r["seed"] for r in rows if r["k"] == 2) == [7, 7, 8, 8, 9, 9]
    assert sorted(set(r["seed"] for r in rows if r["k"] == 3)) == [1, 2]
    assert main(["generate-grid", "--grid", str(grid), "--staging-root", str(root),
                 "--check"]) == 0


@pytest.mark.parametrize("bad, match", [
    ("seeds: [7, 7]", "duplicate seeds"),
    ("seeds: []", "empty seeds"),
])
def test_bad_per_family_seeds_rejected(tmp_path: Path, bad: str, match: str) -> None:
    grid = tmp_path / "g.yaml"
    grid.write_text(SMALL_GRID.replace(
        "  - {family: max2sat, k: 2, n: [25], alpha: [2, 3]}",
        f"  - {{family: max2sat, k: 2, n: [25], alpha: [2, 3], {bad}}}"))
    with pytest.raises(ValueError, match=match):
        load_grid(str(grid))


def test_duplicate_cells_rejected(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(SMALL_GRID.replace("n: [20, 30]", "n: [20, 20]"))
    with pytest.raises(ValueError, match="duplicate cells"):
        load_grid(str(bad))


# --- generate-grid end to end ----------------------------------------------

@pytest.fixture()
def staged(tmp_path: Path):
    grid = tmp_path / "grid.yaml"
    grid.write_text(SMALL_GRID)
    root = tmp_path / "staging"
    rc = main(["generate-grid", "--grid", str(grid), "--staging-root", str(root)])
    assert rc == 0
    return grid, root


def test_generate_grid_writes_files_manifest_and_slurm_manifest(staged) -> None:
    grid, root = staged
    out = root / "data" / "generated" / "t_small"
    files = sorted(p for p in out.glob("*.wcnf"))
    assert len(files) == 12  # 6 cells x 2 seeds
    rows = [json.loads(l) for l in (out / "manifest.jsonl").read_text().splitlines()]
    assert len(rows) == 12
    slurm = (root / "scripts" / "manifest_t_small_rc2.txt").read_text().splitlines()
    assert len(slurm) == 12
    # line N == row N, root-relative, forward slashes
    for i, (line, row) in enumerate(zip(slurm, rows), start=1):
        assert line == row["instance"], i
        assert line.startswith("data/generated/t_small/")
        assert (root / line).is_file()
    # manifest sha == file sha == sha256 file
    sha_lines = (root / "scripts" / "manifest_t_small_rc2.sha256").read_text().splitlines()
    assert len(sha_lines) == 12
    for row, sha_line in zip(rows, sha_lines):
        assert row["instance_sha256"] == _sha(root / row["instance"])
        assert sha_line == f"{row['instance_sha256']}  {row['instance']}"


def test_manifest_row_contents(staged) -> None:
    grid, root = staged
    out = root / "data" / "generated" / "t_small"
    rows = [json.loads(l) for l in (out / "manifest.jsonl").read_text().splitlines()]
    r = rows[0]
    assert r["batch"] == "t_small" and r["cell_id"] == "max3sat_n20_a4.26"
    assert r["family"] == "max3sat" and r["k"] == 3 and r["n"] == 20
    assert r["alpha"] == 4.26 and r["seed"] == 1
    assert r["m"] == round(4.26 * 20) == r["sizes"]["n_soft"]
    assert r["sizes"]["n_hard"] == 0 and r["sizes"]["total_soft_weight"] == r["m"]
    assert r["generator"]["name"] == "weighted_ksat"
    assert r["generator"]["params"] == {
        "n_vars": 20, "k": 3, "soft_ratio": 4.26, "hard_ratio": 0.0,
        "w_max": 1, "seed": 1, "weight_dist": "uniform",
    }
    assert r["dialect"] == "old"
    assert "created_utc" in r and "git_sha" in r
    # the wcnf itself carries no timestamp: header + m clause lines only
    text = (root / r["instance"]).read_text()
    lines = text.splitlines()
    assert lines[0] == f"p wcnf 20 {r['m']} {r['m'] + 1}"
    assert len(lines) == 1 + r["m"]
    assert all(l.startswith("1 ") for l in lines[1:])


def test_regeneration_is_byte_identical_and_check_passes(staged) -> None:
    grid, root = staged
    out = root / "data" / "generated" / "t_small"
    before = {p.name: p.read_bytes() for p in out.glob("*.wcnf")}
    rc = main(["generate-grid", "--grid", str(grid), "--staging-root", str(root)])
    assert rc == 0
    after = {p.name: p.read_bytes() for p in out.glob("*.wcnf")}
    assert before == after
    assert main(["generate-grid", "--grid", str(grid), "--staging-root", str(root),
                 "--check"]) == 0


def test_check_fails_on_tampered_file_and_missing_file(staged, capsys) -> None:
    grid, root = staged
    out = root / "data" / "generated" / "t_small"
    target = sorted(out.glob("*.wcnf"))[0]
    original = target.read_bytes()
    target.write_bytes(original + b"1 -1 2 0\n")
    assert main(["generate-grid", "--grid", str(grid), "--staging-root", str(root),
                 "--check"]) == 1
    assert "bytes differ" in capsys.readouterr().out
    os.unlink(target)
    assert main(["generate-grid", "--grid", str(grid), "--staging-root", str(root),
                 "--check"]) == 1
    assert "missing file" in capsys.readouterr().out
