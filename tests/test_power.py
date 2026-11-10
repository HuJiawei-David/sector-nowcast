from nowcast.power import build_rows, drop_major_breaks, family_summary, min_hits
from nowcast.quarters import Quarter, qrange


def test_min_hits_examples():
    assert min_hits(14) == 11  # CLAUDE.md example
    assert min_hits(9) == 8
    assert min_hits(11) == 9


def test_family_size_and_N():
    rows = build_rows()
    assert family_summary(rows)["direction_cells"] == 39
    by = {(r["name"], r["source"], r["target"]): r for r in rows}
    assert by[("EXPE", "tsa", "y")]["N"] == 14
    assert by[("EXPE", "combined", "k")]["first_q"] == "2024Q1"
    assert by[("TCOM", "caac", "y")]["N"] == 9
    assert by[("TCOM", "caac", "y")]["last_q"] == "2026Q2"  # fixed at prereg
    assert by[("EXPE", "tsa", "y")]["N_excl_major_breaks"] == 14  # EXPE has no MAJOR break in window


def test_drop_major_breaks_uses_q_and_q_minus_1():
    qs = qrange(Quarter(2025, 1), Quarter(2025, 4))
    assert drop_major_breaks(qs, {Quarter(2025, 2)}) == [Quarter(2025, 1), Quarter(2025, 4)]
