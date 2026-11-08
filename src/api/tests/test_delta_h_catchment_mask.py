import numpy as np
import pytest

from calculations.discharge import _delta_h_from_dem_and_mask


def test_delta_h_masks_to_catchment_cells_only():
    dem = np.array(
        [
            [100.0, 110.0, 200.0],
            [120.0, 130.0, 210.0],
            [50.0, 140.0, 220.0],
        ]
    )
    catch = np.array(
        [
            [False, True, False],
            [True, True, False],
            [False, True, False],
        ]
    )
    # Inside catch: 110, 120, 130, 140 → range 30
    assert _delta_h_from_dem_and_mask(dem, catch) == pytest.approx(30.0)


def test_delta_h_rejects_shape_mismatch_like_clip_to_bug():
    dem = np.zeros((4324, 4000))
    catch = np.ones((4800, 4800), dtype=bool)
    with pytest.raises(ValueError, match="does not match DEM shape"):
        _delta_h_from_dem_and_mask(dem, catch)


def test_delta_h_ignores_negative_and_nan_outside_or_inside():
    dem = np.array([[np.nan, -1.0], [105.0, 115.0]], dtype=np.float64)
    catch = np.array([[True, True], [True, True]])
    assert _delta_h_from_dem_and_mask(dem, catch) == pytest.approx(10.0)
