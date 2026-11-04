"""Simplified distributed SCS-CN rainfall-runoff calculation.

NAM2 uses uniform rainfall, searches a travel-time-dependent range of event
durations, applies Ia = 0.1 S, and routes 10-minute runoff increments.
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
    build_duration_candidates,
    calculate_scs_runoff,
    find_critical_scs_event,
)

DT_MINUTES = 10


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
    """Run the fixed NAM2 setup while accepting the legacy NAM call signature."""

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

    valid_curve_numbers = adjusted_cn[valid_mask]
    valid_travel_times = time_values[valid_mask]
    duration_candidates, travel_time_p95, search_truncated = (
        build_duration_candidates(
            valid_travel_times,
            dt_minutes=DT_MINUTES,
        )
    )
    critical_event = find_critical_scs_event(
        intensity_fn=intensity_fn,
        rp_years=x,
        durations_minutes=duration_candidates,
        curve_numbers=valid_curve_numbers,
        pixel_area_m2=pixel_area_m2,
        travel_times=valid_travel_times,
        dt_minutes=DT_MINUTES,
    )

    critical_duration = float(critical_event["critical_duration_minutes"])
    precipitation_mm = float(critical_event["precipitation_mm"])
    peak_discharge = float(critical_event["peak_discharge_m3s"])
    peak_time = float(critical_event["peak_time_minutes"])
    routed_volumes = critical_event["routed_volumes_m3"]
    discharge = critical_event["discharge_m3s"]
    runoff_depth = critical_event["runoff_depth_mm"]
    total_runoff_volume = float(critical_event["total_runoff_volume_m3"])
    peak_timestep = int(np.argmax(discharge))

    retention_valid, abstraction_valid, _ = calculate_scs_runoff(
        precipitation_mm,
        valid_curve_numbers,
    )
    mean_retention = float(np.mean(retention_valid))
    mean_abstraction = float(np.mean(abstraction_valid))
    effective_curve_number = float(np.mean(valid_curve_numbers))
    catchment_raster_area_m2 = float(np.sum(valid_mask) * pixel_area_m2)

    total_precipitation_volume = precipitation_mm * catchment_raster_area_m2 / 1000.0
    total_infiltration_volume = total_precipitation_volume - total_runoff_volume
    runoff_percentage = (
        100.0 * total_runoff_volume / total_precipitation_volume
        if total_precipitation_volume > 0
        else 0.0
    )

    peak_interval_depth = (
        peak_discharge * DT_MINUTES * 60.0 / catchment_raster_area_m2 * 1000.0
    )
    discharge_list = [float(value) for value in discharge]
    result_data = {
        "HQ": peak_discharge,
        "Tc": critical_duration,
        "TB": critical_duration,
        "TFl": travel_time_p95,
        "i": float(critical_event["intensity_mm_per_hour"]),
        "S": mean_retention,
        "Ia": mean_abstraction,
        "Pe": float(peak_interval_depth),
        "HQ_time": json.dumps(discharge_list),
    }
    _store_result(nam_id, climate_scenario, result_data, nam_print)

    nam_print(
        "NAM2 completed:",
        f"Dcritical={critical_duration:.0f} min,",
        f"T95={travel_time_p95:.1f} min,",
        f"Dsearch={duration_candidates[0]}-{duration_candidates[-1]} min,"
        f"P={precipitation_mm:.2f} mm,",
        f"runoff={total_runoff_volume:.2f} m3,",
        f"HQ={peak_discharge:.3f} m3/s,",
        f"HQ60={critical_event['hq_60_m3s']:.3f} m3/s",
    )

    return {
        **result_data,
        "effective_curve_number": effective_curve_number,
        "runoff_timesteps": [float(value) for value in routed_volumes],
        "discharge_timesteps": discharge_list,
        "max_timestep": peak_timestep,
        "peak_time_minutes": peak_time,
        "critical_duration_minutes": critical_duration,
        "travel_time_p95_minutes": travel_time_p95,
        "duration_search_min_minutes": int(duration_candidates[0]),
        "duration_search_max_minutes": int(duration_candidates[-1]),
        "duration_search_truncated": bool(search_truncated),
        "duration_peaks_m3s": {
            int(duration): float(peak)
            for duration, peak in critical_event["peaks_by_duration_m3s"].items()
        },
        "hq_60_m3s": float(critical_event["hq_60_m3s"]),
        "total_cells": int(np.sum(valid_mask)),
        "pixel_area_m2": float(pixel_area_m2),
        "precipitation_mm": precipitation_mm,
        "precipitation_factor": 1.0,
        "rain_block_count": int(critical_duration // DT_MINUTES),
        "water_balance": {
            "approach": "uniform_critical_duration",
            "total_precipitation_volume_m3": float(total_precipitation_volume),
            "total_infiltration_volume_m3": float(total_infiltration_volume),
            "total_runoff_volume_m3": total_runoff_volume,
            "infiltration_percentage": float(100.0 - runoff_percentage),
            "runoff_percentage": float(runoff_percentage),
            "mean_runoff_depth_mm": float(np.mean(runoff_depth)),
        },
        "routing_method": "time_values",
        "time_values_info": {
            "used_time_values": True,
            "max_travel_time": float(np.max(valid_travel_times)),
            "mean_travel_time": float(np.mean(valid_travel_times)),
            "min_travel_time": float(np.min(valid_travel_times)),
            "p95_travel_time": travel_time_p95,
        },
    }
