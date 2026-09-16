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
