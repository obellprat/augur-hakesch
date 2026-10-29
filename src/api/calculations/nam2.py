"""Simplified distributed SCS-CN rainfall-runoff calculation.

NAM2 intentionally supports one fixed model setup: uniform 60-minute rainfall,
Ia = 0.1 S, six cumulative 10-minute SCS runoff increments, and time-values routing.
"""

import builtins
import json
import os
import traceback

import numpy as np
import rasterio
from rasterio.warp import Resampling, reproject

from calculations.calculations import app
from calculations.discharge import (
    _load_cc_factor_simple,
    connect_prisma_with_retry,
    construct_idf_curve,
)
from calculations.nam2_core import (
    calculate_and_route_scs_event,
    calculate_scs_runoff,
)

DT_MINUTES = 10
EVENT_DURATION_MINUTES = 60
RAIN_BLOCK_COUNT = EVENT_DURATION_MINUTES // DT_MINUTES


def _data_directories():
    directories = []
    if os.getenv("DATA_DIR"):
        directories.append(os.getenv("DATA_DIR"))
    directories.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data")))
    directories.append(os.path.join(os.getcwd(), "data"))
    return list(dict.fromkeys(directories))


def _resolve_raster_path(project_id, user_id, filename):
    candidates = [
        os.path.join(base, str(user_id), str(project_id), filename)
        for base in _data_directories()
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    raise FileNotFoundError(f"{filename} not found; tried: {', '.join(candidates)}")


def _read_float_raster(path):
    with rasterio.open(path) as source:
        data = source.read(1, masked=True).astype(np.float64).filled(np.nan)
        return data, source.transform, source.crs


def _load_model_rasters(project_id, user_id):
    cn_path = _resolve_raster_path(project_id, user_id, "curvenumbers.tif")
    time_path = _resolve_raster_path(project_id, user_id, "time_values.tif")

    cn_data, cn_transform, cn_crs = _read_float_raster(cn_path)
    time_data, time_transform, time_crs = _read_float_raster(time_path)

    grids_match = (
        time_data.shape == cn_data.shape
        and time_transform == cn_transform
        and time_crs == cn_crs
    )
    if not grids_match:
        aligned_time_data = np.full(cn_data.shape, np.nan, dtype=np.float64)
        reproject(
            source=time_data,
            destination=aligned_time_data,
            src_transform=time_transform,
            src_crs=time_crs,
            dst_transform=cn_transform,
            dst_crs=cn_crs,
            src_nodata=np.nan,
            dst_nodata=np.nan,
            resampling=Resampling.bilinear,
        )
        time_data = aligned_time_data

    pixel_area_m2 = abs(cn_transform.a * cn_transform.e)
    return cn_data, time_data, pixel_area_m2


def _result_relation(climate_scenario, result_data):
    relation_by_scenario = {
        "1_5_degree": "NAM_Result_1_5",
        "2_degree": "NAM_Result_2",
        "3_degree": "NAM_Result_3",
        "4_degree": "NAM_Result_4",
    }
    relation = relation_by_scenario.get(climate_scenario, "NAM_Result")
    return {
        relation: {
            "upsert": {
                "update": result_data,
                "create": result_data,
            }
        }
    }


def _store_result(nam_id, climate_scenario, result_data, print_fn):
    prisma = None
    try:
        prisma = connect_prisma_with_retry()
        prisma.nam.update(
            where={"id": nam_id},
            data=_result_relation(climate_scenario, result_data),
        )
    except Exception as exc:
        print_fn(f"Error updating NAM2 results: {exc}", warning=True)
        print_fn(traceback.format_exc(), warning=True)
    finally:
        if prisma is not None:
            try:
                prisma.disconnect(5)
            except Exception:
                pass


@app.task(name="nam2", bind=True)
def nam2(
    self,
    P_low_1h,
    P_high_1h,
    P_low_24h,
    P_high_24h,
    rp_low,
    rp_high,
    x,
    curve_number,
    catchment_area,
    channel_length,
    delta_h,
    nam_id,
    project_id=None,
    user_id=None,
    water_balance_mode=None,
    precipitation_factor=None,
    storm_center_mode=None,
    routing_method=None,
    readiness_to_drain=None,
    discharge_point=None,
    discharge_point_crs="EPSG:4326",
    project_easting=None,
    project_northing=None,
    cc_degree=0.0,
    climate_scenario="current",
    debug=True,
    persist=True,
):
    """Run the fixed NAM2 setup while accepting the legacy NAM call signature.

    Precipitation is never scaled. precipitation_factor is accepted for call
    compatibility and the rainfall stays at factor 1.
    persist=False returns the hydrograph values without writing NAM_Result.
    """

    def nam_print(*args, **kwargs):
        warning = kwargs.pop("warning", False)
        message = " ".join(str(arg) for arg in args)
        important = any(
            token in message.lower()
            for token in ("warning", "error", "failed", "not found")
        )
        if debug or warning or important:
            builtins.print(*args, **kwargs)

    # Accepted for call compatibility; NAM2 deliberately does not use these modes.
    _ = (
        curve_number,
        catchment_area,
        channel_length,
        delta_h,
        water_balance_mode,
        precipitation_factor,
        storm_center_mode,
        routing_method,
        discharge_point,
        discharge_point_crs,
        project_easting,
        project_northing,
    )

    if project_id is None or user_id is None:
        return {"error": "Project ID and User ID required for NAM2 calculation"}

    try:
        cn_data, time_values, pixel_area_m2 = _load_model_rasters(project_id, user_id)
    except Exception as exc:
        nam_print(f"Error loading NAM2 rasters: {exc}", warning=True)
        return {"error": f"Error loading NAM2 rasters: {exc}"}

    cn_mask = np.isfinite(cn_data) & (cn_data > 0)
    if not np.any(cn_mask):
        return {"error": "No valid curve numbers found in raster"}

    adjustment = float(readiness_to_drain or 0.0)
    adjusted_cn = np.array(cn_data, copy=True)
    adjusted_cn[cn_mask] = np.clip(adjusted_cn[cn_mask] + adjustment, 30.0, 100.0)

    time_mask = np.isfinite(time_values) & (time_values > 0)
    valid_mask = cn_mask & time_mask
    if not np.any(valid_mask):
        return {"error": "No cells have both a valid curve number and travel time"}

    scenario_degrees = {
        "current": 0.0,
        "1_5_degree": 1.5,
        "2_degree": 2.0,
        "3_degree": 3.0,
    }
    scenario_degree = scenario_degrees.get(climate_scenario, float(cc_degree))
    climate_factor = _load_cc_factor_simple(scenario_degree)
    intensity_fn = construct_idf_curve(
        P_low_1h,
        P_high_1h,
        P_low_24h,
        P_high_24h,
        rp_low,
        rp_high,
        climate_factor,
    )

    intensity_60 = float(
        intensity_fn(rp_years=x, duration_minutes=EVENT_DURATION_MINUTES)
    )
    precipitation_mm = intensity_60 * EVENT_DURATION_MINUTES / 60.0

    retention = np.full(cn_data.shape, np.nan, dtype=np.float64)
    initial_abstraction = np.full(cn_data.shape, np.nan, dtype=np.float64)
    retention_valid, abstraction_valid, _ = calculate_scs_runoff(
        precipitation_mm,
        adjusted_cn[valid_mask],
    )
    retention[valid_mask] = retention_valid
    initial_abstraction[valid_mask] = abstraction_valid

    runoff_depth, runoff_volume_blocks, routed_volumes, discharge = (
        calculate_and_route_scs_event(
            precipitation_mm,
            adjusted_cn,
            pixel_area_m2,
            time_values,
            valid_mask,
            dt_minutes=DT_MINUTES,
            block_count=RAIN_BLOCK_COUNT,
        )
    )
    runoff_volumes = np.sum(runoff_volume_blocks, axis=0)

    peak_discharge = float(np.max(discharge))
    peak_timestep = int(np.argmax(discharge))
    concentration_time = float((peak_timestep + 1) * DT_MINUTES)
    mean_retention = float(np.mean(retention[valid_mask]))
    mean_abstraction = float(np.mean(initial_abstraction[valid_mask]))
    effective_curve_number = float(np.mean(adjusted_cn[valid_mask]))
    catchment_raster_area_m2 = float(np.sum(valid_mask) * pixel_area_m2)

    total_precipitation_volume = precipitation_mm * catchment_raster_area_m2 / 1000.0
    total_runoff_volume = float(np.sum(runoff_volumes[valid_mask]))
    total_infiltration_volume = total_precipitation_volume - total_runoff_volume
    runoff_percentage = (
        100.0 * total_runoff_volume / total_precipitation_volume
        if total_precipitation_volume > 0
        else 0.0
    )

    final_intensity = float(
        intensity_fn(rp_years=x, duration_minutes=concentration_time)
    )
    peak_interval_depth = (
        peak_discharge * DT_MINUTES * 60.0 / catchment_raster_area_m2 * 1000.0
    )
    discharge_list = [float(value) for value in discharge]
    result_data = {
        "HQ": peak_discharge,
        "Tc": concentration_time,
        "TB": concentration_time,
        "TFl": 0.0,
        "i": final_intensity,
        "S": mean_retention,
        "Ia": mean_abstraction,
        "Pe": float(peak_interval_depth),
        "HQ_time": json.dumps(discharge_list),
    }
    if persist:
        _store_result(nam_id, climate_scenario, result_data, nam_print)

    nam_print(
        "NAM2 completed:",
        f"P60={precipitation_mm:.2f} mm,",
        f"runoff={total_runoff_volume:.2f} m3,",
        f"HQ={peak_discharge:.3f} m3/s",
    )

    return {
        **result_data,
        "effective_curve_number": effective_curve_number,
        "runoff_timesteps": [float(value) for value in routed_volumes],
        "discharge_timesteps": discharge_list,
        "max_timestep": peak_timestep,
        "total_cells": int(np.sum(valid_mask)),
        "pixel_area_m2": float(pixel_area_m2),
        "precipitation_mm": precipitation_mm,
        "precipitation_factor": 1.0,
        "rain_block_count": RAIN_BLOCK_COUNT,
        "water_balance": {
            "approach": "uniform",
            "total_precipitation_volume_m3": float(total_precipitation_volume),
            "total_infiltration_volume_m3": float(total_infiltration_volume),
            "total_runoff_volume_m3": total_runoff_volume,
            "infiltration_percentage": float(100.0 - runoff_percentage),
            "runoff_percentage": float(runoff_percentage),
        },
        "routing_method": "time_values",
        "time_values_info": {
            "used_time_values": True,
            "max_travel_time": float(np.max(time_values[valid_mask])),
            "mean_travel_time": float(np.mean(time_values[valid_mask])),
            "min_travel_time": float(np.min(time_values[valid_mask])),
        },
    }
