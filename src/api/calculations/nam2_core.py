"""Pure hydrological helpers for the simplified NAM2 calculation."""

import numpy as np


def calculate_scs_runoff(precipitation_mm, curve_numbers):
    """Return cell retention, initial abstraction, and runoff depths in mm."""
    curve_numbers = np.asarray(curve_numbers, dtype=np.float64)
    retention = (25400.0 / curve_numbers) - 254.0
    initial_abstraction = 0.1 * retention
    runoff = np.zeros_like(retention)

    runoff_mask = precipitation_mm > initial_abstraction
    precipitation_excess = precipitation_mm - initial_abstraction[runoff_mask]
    runoff[runoff_mask] = (
        precipitation_excess**2
        / (precipitation_excess + retention[runoff_mask])
    )
    return retention, initial_abstraction, runoff


def calculate_incremental_scs_runoff_blocks(
    total_precipitation_mm,
    curve_numbers,
    block_count=6,
):
    """Return incremental SCS runoff depths for equal rainfall intervals."""
    if block_count <= 0:
        raise ValueError("block_count must be positive")

    curve_numbers = np.asarray(curve_numbers, dtype=np.float64)
    runoff_blocks = np.zeros((block_count,) + curve_numbers.shape, dtype=np.float64)
    previous_runoff = np.zeros_like(curve_numbers)

    for block_index in range(block_count):
        cumulative_precipitation = (
            total_precipitation_mm * (block_index + 1) / block_count
        )
        _, _, cumulative_runoff = calculate_scs_runoff(
            cumulative_precipitation,
            curve_numbers,
        )
        runoff_blocks[block_index] = cumulative_runoff - previous_runoff
        previous_runoff = cumulative_runoff

    return runoff_blocks


def route_runoff_blocks(
    runoff_volume_blocks,
    travel_times,
    valid_mask,
    dt_minutes=10,
):
    """Route runoff blocks with linear interpolation between time intervals."""
    if dt_minutes <= 0:
        raise ValueError("dt_minutes must be positive")

    runoff_volume_blocks = np.asarray(runoff_volume_blocks, dtype=np.float64)
    travel_times = np.asarray(travel_times, dtype=np.float64)
    valid_mask = np.asarray(valid_mask, dtype=bool)
    if (
        runoff_volume_blocks.ndim < 1
        or runoff_volume_blocks.shape[1:] != travel_times.shape
    ):
        raise ValueError(
            "runoff block cells and travel times must have the same shape"
        )
    if travel_times.shape != valid_mask.shape:
        raise ValueError("travel times and valid mask must have the same shape")

    block_count = runoff_volume_blocks.shape[0]
    if block_count <= 0:
        raise ValueError("at least one runoff block is required")

    routing_mask = valid_mask & np.isfinite(travel_times) & (travel_times > 0)
    if not np.any(routing_mask):
        empty = np.zeros(block_count, dtype=np.float64)
        return empty, empty.copy()

    fractional_steps = travel_times[routing_mask] / dt_minutes
    lower_steps = np.floor(fractional_steps).astype(int)
    lower_steps = np.maximum(lower_steps, 0)
    upper_weights = np.clip(fractional_steps - lower_steps, 0.0, 1.0)
    has_upper_share = upper_weights > 1e-12
    max_arrival_step = np.max(lower_steps + has_upper_share)
    routed_volumes = np.zeros(
        int(max_arrival_step) + block_count,
        dtype=np.float64,
    )

    for block_index in range(block_count):
        block_volumes = runoff_volume_blocks[block_index][routing_mask]
        np.add.at(
            routed_volumes,
            lower_steps + block_index,
            block_volumes * (1.0 - upper_weights),
        )
        if np.any(has_upper_share):
            np.add.at(
                routed_volumes,
                lower_steps[has_upper_share] + block_index + 1,
                block_volumes[has_upper_share] * upper_weights[has_upper_share],
            )

    discharge = routed_volumes / (dt_minutes * 60.0)
    return routed_volumes, discharge


def calculate_and_route_scs_event(
    total_precipitation_mm,
    curve_numbers,
    pixel_area_m2,
    travel_times,
    valid_mask,
    dt_minutes=10,
    block_count=6,
):
    """Calculate cumulative SCS increments and route their cell volumes."""
    curve_numbers = np.asarray(curve_numbers, dtype=np.float64)
    valid_mask = np.asarray(valid_mask, dtype=bool)
    if curve_numbers.shape != valid_mask.shape:
        raise ValueError("curve numbers and valid mask must have the same shape")

    runoff_depth_blocks = np.zeros(
        (block_count,) + curve_numbers.shape,
        dtype=np.float64,
    )
    runoff_depth_blocks[:, valid_mask] = calculate_incremental_scs_runoff_blocks(
        total_precipitation_mm,
        curve_numbers[valid_mask],
        block_count=block_count,
    )
    runoff_depth = np.sum(runoff_depth_blocks, axis=0)
    runoff_volume_blocks = runoff_depth_blocks
    runoff_volume_blocks *= pixel_area_m2 / 1000.0
    routed_volumes, discharge = route_runoff_blocks(
        runoff_volume_blocks,
        travel_times,
        valid_mask,
        dt_minutes=dt_minutes,
    )
    return runoff_depth, runoff_volume_blocks, routed_volumes, discharge


def route_equal_runoff_blocks(
    runoff_volumes,
    travel_times,
    valid_mask,
    dt_minutes=10,
    block_count=6,
):
    """Route equal runoff blocks by cell travel time and return volume and flow series."""
    if dt_minutes <= 0:
        raise ValueError("dt_minutes must be positive")
    if block_count <= 0:
        raise ValueError("block_count must be positive")

    runoff_volumes = np.asarray(runoff_volumes, dtype=np.float64)
    travel_times = np.asarray(travel_times, dtype=np.float64)
    valid_mask = np.asarray(valid_mask, dtype=bool)
    if (
        runoff_volumes.shape != travel_times.shape
        or runoff_volumes.shape != valid_mask.shape
    ):
        raise ValueError(
            "runoff volumes, travel times, and valid mask must have the same shape"
        )

    routing_mask = valid_mask & np.isfinite(travel_times) & (travel_times > 0)
    if not np.any(routing_mask):
        empty = np.zeros(block_count, dtype=np.float64)
        return empty, empty.copy()

    arrival_steps = np.rint(travel_times[routing_mask] / dt_minutes).astype(int)
    arrival_steps = np.maximum(arrival_steps, 0)
    interval_volumes = runoff_volumes[routing_mask] / block_count
    routed_volumes = np.zeros(
        int(np.max(arrival_steps)) + block_count,
        dtype=np.float64,
    )

    for block_index in range(block_count):
        np.add.at(routed_volumes, arrival_steps + block_index, interval_volumes)

    discharge = routed_volumes / (dt_minutes * 60.0)
    return routed_volumes, discharge
