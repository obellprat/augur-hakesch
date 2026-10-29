"""Cell assignment for the Atyp curve-number CLI. No database."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "generate_atyp_curvenumbers.py"
_spec = importlib.util.spec_from_file_location("generate_atyp_curvenumbers", _SCRIPT)
atyp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(atyp)


def test_stream_column_gets_highest_cn_and_exact_shares():
    stream = np.zeros((5, 5), dtype=bool)
    stream[:, 2] = True
    distance = atyp.distance_to_stream_pixels(stream, (1.0, 1.0))
    percentages = {name: 20.0 for name in atyp.ATYP_ORDER}

    first, stats = atyp.assign_curve_numbers(distance, np.ones((5, 5), dtype=bool), percentages)
    second, _ = atyp.assign_curve_numbers(distance, np.ones((5, 5), dtype=bool), percentages)

    np.testing.assert_array_equal(first, second)
    assert np.all(first[:, 2] == 80)
    assert stats["n_cells"] == 25
    assert stats["counts"] == {name: 5 for name in atyp.ATYP_ORDER}
    # Same distance: lower row, then lower column, is filled first.
    assert first[0, 1] == 75
    assert first[2, 1] == 75
    assert first[2, 3] == 65
    assert first[4, 4] == 36
    assert stats["classes"]["Atyp 1"]["max_distance_m"] == 0
    assert stats["classes"]["Atyp 5"]["min_distance_m"] > stats["classes"]["Atyp 1"]["max_distance_m"]


def test_settlement_type_is_closest_to_the_stream():
    stream = np.zeros((5, 5), dtype=bool)
    stream[:, 2] = True
    distance = atyp.distance_to_stream_pixels(stream, (1.0, 1.0))
    curve_numbers, stats = atyp.assign_curve_numbers(
        distance,
        np.ones((5, 5), dtype=bool),
        {"Siedl.typ 1": 20.0, "Atyp 5": 80.0},
    )
    assert np.all(curve_numbers[:, 2] == 80)
    assert stats["classes"]["Siedl.typ 1"]["count"] == 5
    assert stats["classes"]["Atyp 5"]["cn"] == 36
    assert stats["classes"]["Atyp 5"]["min_distance_m"] > 0


def test_largest_remainder_prefers_earlier_atyp_on_ties():
    counts = atyp.cell_counts_from_percentages(3, {"Atyp 1": 50.0, "Atyp 2": 50.0})
    assert counts == {"Atyp 1": 2, "Atyp 2": 1}
    assert sum(counts.values()) == 3

    uneven = atyp.cell_counts_from_percentages(
        10, {"Atyp 1": 33.4, "Atyp 2": 33.3, "Atyp 3": 33.3}
    )
    assert uneven == {"Atyp 1": 4, "Atyp 2": 3, "Atyp 3": 3}


def test_fraction_sets_must_agree_and_settlement_gets_cn_80():
    sets = [
        {"Atyp 1": 1.8, "Atyp 2": 14.2, "Siedl.typ 1": 1.68},
        {"Atyp1": 1.8, "Atyp 2": 14.2, "Siedlungstyp 1": 1.68},
    ]
    normalized, report = atyp.resolve_atyp_percentages(sets)
    assert report["ignored_non_atyp_percent"] == {}
    assert normalized["Siedl.typ 1"] == pytest.approx(1.68 / 17.68 * 100.0)
    assert atyp.CLASS_CN["Siedl.typ 1"] == 80.0
    assert sum(normalized.values()) == pytest.approx(100.0)

    with pytest.raises(ValueError, match="differ"):
        atyp.resolve_atyp_percentages([
            {"Atyp 1": 10.0, "Atyp 2": 90.0},
            {"Atyp 1": 20.0, "Atyp 2": 80.0},
        ])

    with pytest.raises(ValueError, match="Non-Atyp"):
        atyp.resolve_atyp_percentages([{"Atyp 1": 90.0, "Siedl.typ 2": 10.0}])
