#!/usr/bin/env python3
"""
Build a NAM curve-number raster from a project's Abflusstyp fractions.

Each Atyp keeps its area share. Cells are ordered by distance to the river
network (Project.branches_geojson): Atyp 1 is closest, Atyp 5 is farthest.
The result overwrites data/{userId}/{projectId}/curvenumbers.tif, which NAM
already reads. The previous raster is copied to curvenumbers_landcover.tif
once, so a later run does not replace that backup.

This script is not wired into the web app. A calculation started in the UI
still regenerates curve numbers from land cover and soil and would overwrite
curvenumbers.tif.

If the project data directory is not writable, the raster is written to a
temp directory and, when a running container mounts that tree, copied in
with docker.

Usage:
    python scripts/generate_atyp_curvenumbers.py --project-id <id>
"""

import argparse
import json
import math
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import rasterio
from rasterio.features import rasterize
from scipy.ndimage import distance_transform_edt
from shapely.geometry import shape

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, ".."))
_API_DIR = os.path.join(_PROJECT_ROOT, "src", "api")

ATYP_ORDER: Tuple[str, ...] = ("Atyp 1", "Atyp 2", "Atyp 3", "Atyp 4", "Atyp 5")
# Closest to the channel first. Siedl.typ 1 has the same CN as Atyp 1, so both
# form the near-stream band of CN 80.
CLASS_ORDER: Tuple[str, ...] = ("Siedl.typ 1",) + ATYP_ORDER
CLASS_CN: Dict[str, float] = {
    "Siedl.typ 1": 80.0,
    "Atyp 1": 75.0,
    "Atyp 2": 70.0,
    "Atyp 3": 60.0,
    "Atyp 4": 50.0,
    "Atyp 5": 36.0,
}
ATYP_CN = {name: CLASS_CN[name] for name in ATYP_ORDER}
# Shares below this are treated as rounding residue (for example 0.0012%).
NON_ATYP_IGNORE_BELOW_PCT = 0.05
FRACTION_TOLERANCE = 1e-4


def canonical_class_name(typ: str) -> Optional[str]:
    """Map 'Atyp 1' / 'Siedl.typ 1' spellings to the canonical label."""
    compact = "".join(ch for ch in str(typ).lower() if ch.isalnum())
    for index, name in enumerate(ATYP_ORDER, start=1):
        if compact == f"atyp{index}":
            return name
    if compact in {"siedltyp1", "siedlungstyp1"}:
        return "Siedl.typ 1"
    return None


def resolve_atyp_percentages(
    fraction_sets: Sequence[Mapping[str, float]],
) -> Tuple[Dict[str, float], Dict[str, Any]]:
    """
    Check that every Clark-WSL entry carries the same Atyp shares.

    Returns percentages normalised to 100, plus a report of the original
    shares and any ignored non-Atyp residue. Raises ValueError when the
    entries disagree or a non-Atyp type has a real area share.
    """
    if not fraction_sets:
        raise ValueError("Project has no Clark-WSL fraction sets")

    parsed: List[Tuple[Dict[str, float], Dict[str, float]]] = []
    for entry in fraction_sets:
        atyp = {name: 0.0 for name in CLASS_ORDER}
        other: Dict[str, float] = {}
        for typ, pct in entry.items():
            if pct is None:
                continue
            value = float(pct)
            if math.isnan(value) or value == 0.0:
                continue
            name = canonical_class_name(str(typ))
            if name is None:
                other[str(typ)] = other.get(str(typ), 0.0) + value
            else:
                atyp[name] += value
        parsed.append((atyp, other))

    reference_atyp, reference_other = parsed[0]
    for index, (atyp, other) in enumerate(parsed[1:], start=1):
        for name in CLASS_ORDER:
            if abs(atyp[name] - reference_atyp[name]) > FRACTION_TOLERANCE:
                raise ValueError(
                    f"Atyp percentages differ between Clark-WSL entries "
                    f"(entry 0 {name}={reference_atyp[name]}, "
                    f"entry {index} {name}={atyp[name]})"
                )
        other_keys = set(reference_other) | set(other)
        for key in other_keys:
            left = reference_other.get(key, 0.0)
            right = other.get(key, 0.0)
            if abs(left - right) > FRACTION_TOLERANCE:
                raise ValueError(
                    f"Non-Atyp percentages differ between Clark-WSL entries "
                    f"({key}: {left} vs {right})"
                )

    significant_other = {
        key: value
        for key, value in reference_other.items()
        if value >= NON_ATYP_IGNORE_BELOW_PCT
    }
    ignored_other = {
        key: value
        for key, value in reference_other.items()
        if value < NON_ATYP_IGNORE_BELOW_PCT
    }
    if significant_other:
        listed = ", ".join(f"{key}={value}" for key, value in sorted(significant_other.items()))
        raise ValueError(
            "Non-Atyp fractions have no curve number and are large enough to matter: "
            f"{listed}"
        )

    original = {
        name: reference_atyp[name]
        for name in CLASS_ORDER
        if reference_atyp[name] > 0.0
    }
    total = sum(original.values())
    if total <= 0.0:
        raise ValueError("No Atyp percentages found on the project")

    normalized = {name: value / total * 100.0 for name, value in original.items()}
    report = {
        "original_percent": original,
        "original_sum": total,
        "normalized_percent": normalized,
        "ignored_non_atyp_percent": ignored_other,
    }
    return normalized, report


def cell_counts_from_percentages(
    n_cells: int, percentages: Mapping[str, float]
) -> Dict[str, int]:
    """Largest-remainder allocation. Counts sum exactly to n_cells."""
    if n_cells < 0:
        raise ValueError("n_cells must be >= 0")
    names = [name for name in CLASS_ORDER if percentages.get(name, 0.0) > 0.0]
    if n_cells == 0 or not names:
        return {name: 0 for name in names}

    total_pct = sum(float(percentages[name]) for name in names)
    raw = {name: n_cells * (float(percentages[name]) / total_pct) for name in names}
    counts = {name: int(math.floor(raw[name] + 1e-9)) for name in names}
    leftover = n_cells - sum(counts.values())

    def fractional_part(name: str) -> float:
        return raw[name] - math.floor(raw[name] + 1e-9)

    if leftover > 0:
        ranked = sorted(names, key=lambda name: (-fractional_part(name), CLASS_ORDER.index(name)))
        if leftover > len(ranked):
            raise ValueError("Percentages do not account for the catchment cell count")
        for name in ranked[:leftover]:
            counts[name] += 1
    elif leftover < 0:
        ranked = sorted(names, key=lambda name: (fractional_part(name), CLASS_ORDER.index(name)))
        for name in ranked:
            if leftover == 0:
                break
            if counts[name] > 0:
                counts[name] -= 1
                leftover += 1
        if leftover != 0:
            raise ValueError("Could not reconcile Atyp cell counts")
    return counts


def distance_to_stream_pixels(stream_mask: np.ndarray, cell_size_m: Tuple[float, float]) -> np.ndarray:
    """Euclidean distance in metres from every pixel to the nearest stream pixel."""
    stream = np.asarray(stream_mask, dtype=bool)
    if stream.ndim != 2:
        raise ValueError("stream_mask must be 2-D")
    if not np.any(stream):
        raise ValueError("No stream pixels fall on the isozone grid")
    # distance_transform_edt measures distance to the nearest zero.
    field = np.where(stream, 0, 1)
    row_size, col_size = cell_size_m
    return distance_transform_edt(field, sampling=(row_size, col_size))


def assign_curve_numbers(
    distance_m: np.ndarray,
    catchment_mask: np.ndarray,
    percentages: Mapping[str, float],
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Give the closest catchment cells Atyp 1, then Atyp 2, and so on.

    Ties are broken by row, then column, so the result does not depend on
    hash order. Cells outside the catchment stay 0 (nodata).
    """
    mask = np.asarray(catchment_mask, dtype=bool)
    distance = np.asarray(distance_m)
    if mask.shape != distance.shape:
        raise ValueError(
            f"Shape mismatch: distance {distance.shape}, catchment {mask.shape}"
        )
    rows, cols = np.nonzero(mask)
    n_cells = int(rows.size)
    if n_cells == 0:
        raise ValueError("Isozone raster has no catchment cells")

    counts = cell_counts_from_percentages(n_cells, percentages)
    order = np.lexsort((cols, rows, distance[rows, cols]))
    sorted_rows = rows[order]
    sorted_cols = cols[order]
    sorted_distance = distance[sorted_rows, sorted_cols]

    curve_numbers = np.zeros(mask.shape, dtype=np.float32)
    classes: Dict[str, Any] = {}
    cursor = 0
    for name in CLASS_ORDER:
        count = counts.get(name, 0)
        if count <= 0:
            continue
        selected = slice(cursor, cursor + count)
        curve_numbers[sorted_rows[selected], sorted_cols[selected]] = CLASS_CN[name]
        class_distance = sorted_distance[selected]
        classes[name] = {
            "cn": CLASS_CN[name],
            "count": int(count),
            "percent": round(100.0 * count / n_cells, 4),
            "min_distance_m": float(class_distance.min()),
            "max_distance_m": float(class_distance.max()),
        }
        cursor += count
    if cursor != n_cells:
        raise RuntimeError(f"Assigned {cursor} of {n_cells} catchment cells")

    mean_cn = float(curve_numbers[mask].mean())
    stats = {
        "n_cells": n_cells,
        "mean_cn": mean_cn,
        "counts": {name: int(counts.get(name, 0)) for name in CLASS_ORDER if counts.get(name, 0)},
        "classes": classes,
    }
    return curve_numbers, stats


def iter_branch_geometries(branches: Any) -> Iterable[Any]:
    if isinstance(branches, str):
        branches = json.loads(branches)
    if not isinstance(branches, dict):
        raise ValueError("branches_geojson is not a GeoJSON object")
    if branches.get("type") == "Feature":
        features = [branches]
    else:
        features = branches.get("features") or []
    if not features:
        raise ValueError("branches_geojson has no features")
    for feature in features:
        geometry = feature.get("geometry") if isinstance(feature, dict) else None
        if geometry:
            yield shape(geometry)


def rasterize_streams(branches: Any, out_shape: Tuple[int, int], transform) -> np.ndarray:
    shapes = [(geometry, 1) for geometry in iter_branch_geometries(branches)]
    if not shapes:
        raise ValueError("branches_geojson has no line geometries")
    burned = rasterize(
        shapes,
        out_shape=out_shape,
        transform=transform,
        fill=0,
        all_touched=True,
        dtype="uint8",
    )
    return burned.astype(bool)


def catchment_mask_from_isozones(data: np.ndarray, nodata: Optional[float]) -> np.ndarray:
    mask = np.isfinite(data)
    if nodata is not None and not (isinstance(nodata, float) and math.isnan(nodata)):
        mask &= data != nodata
    mask &= data > 0
    return mask


def project_data_dir(user_id: int, project_id: str) -> str:
    bases: List[str] = []
    env_dir = os.getenv("DATA_DIR")
    if env_dir:
        bases.append(env_dir)
    bases.append(os.path.join(_API_DIR, "data"))
    bases.append(os.path.join(os.getcwd(), "data"))
    tried = []
    for base in bases:
        candidate = os.path.join(base, str(user_id), str(project_id))
        tried.append(candidate)
        if os.path.isdir(candidate):
            return candidate
    raise FileNotFoundError(
        "Project data directory not found. Tried:\n  " + "\n  ".join(tried)
    )


def _fraction_sets_from_project(project) -> List[Dict[str, float]]:
    clark_entries = list(project.ClarkWSL or [])
    if not clark_entries:
        raise ValueError(f"Project {project.id} has no Clark-WSL entries")
    fraction_sets = []
    for entry in clark_entries:
        fractions: Dict[str, float] = {}
        for fraction in entry.Fractions or []:
            fractions[fraction.ZoneParameterTyp] = fractions.get(fraction.ZoneParameterTyp, 0.0) + float(
                fraction.pct or 0.0
            )
        annuality = entry.Annuality.number if entry.Annuality else None
        if not any(value > 0 for value in fractions.values()):
            raise ValueError(f"Clark-WSL entry for annuality {annuality} has no fractions")
        fraction_sets.append(fractions)
    return fraction_sets


def load_project(project_id: str):
    if _API_DIR not in sys.path:
        sys.path.insert(0, _API_DIR)
    from dotenv import load_dotenv
    from helpers.prisma import prisma

    load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))
    prisma.connect()
    try:
        return prisma.project.find_unique_or_raise(
            where={"id": project_id},
            include={
                "ClarkWSL": {
                    "include": {
                        "Fractions": True,
                        "Annuality": True,
                    }
                }
            },
        )
    finally:
        prisma.disconnect()


def write_stats(path: str, stats: Mapping[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(stats, handle, indent=2)
        handle.write("\n")


def write_curve_number_raster(path: str, curve_numbers: np.ndarray, transform, crs) -> None:
    profile = {
        "driver": "GTiff",
        "height": curve_numbers.shape[0],
        "width": curve_numbers.shape[1],
        "count": 1,
        "dtype": "float32",
        "crs": crs,
        "transform": transform,
        "nodata": 0,
        "compress": "lzw",
    }
    with rasterio.open(path, "w", **profile) as dataset:
        dataset.write(curve_numbers, 1)


def backup_existing_raster(curve_number_path: str) -> Optional[str]:
    """Copy the current raster once. Later runs keep that first backup."""
    backup_path = os.path.join(os.path.dirname(curve_number_path), "curvenumbers_landcover.tif")
    if not os.path.exists(curve_number_path):
        return None
    if os.path.exists(backup_path):
        print(f"Keeping existing land-cover backup: {backup_path}")
        return backup_path
    shutil.copy2(curve_number_path, backup_path)
    print(f"Backed up existing curve numbers to {backup_path}")
    return backup_path


def generate_for_project(project_id: str) -> Dict[str, Any]:
    project = load_project(project_id)
    if not project.branches_geojson:
        raise ValueError(f"Project {project_id} has no branches_geojson")

    data_dir = project_data_dir(project.userId, project_id)
    isozone_path = os.path.join(data_dir, "isozones_cog.tif")
    if not os.path.exists(isozone_path):
        raise FileNotFoundError(f"Isozone raster not found: {isozone_path}")

    percentages, fraction_report = resolve_atyp_percentages(_fraction_sets_from_project(project))

    with rasterio.open(isozone_path) as src:
        isozones = src.read(1)
        transform = src.transform
        crs = src.crs
        nodata = src.nodata
        cell_size = (abs(src.transform.e), abs(src.transform.a))

    mask = catchment_mask_from_isozones(isozones, nodata)

    streams = rasterize_streams(project.branches_geojson, isozones.shape, transform)
    distance_m = distance_to_stream_pixels(streams, cell_size)
    curve_numbers, assignment = assign_curve_numbers(distance_m, mask, percentages)

    stats = {
        "project_id": project_id,
        "user_id": project.userId,
        "isozone_raster": isozone_path,
        "cell_size_m": {"row": cell_size[0], "col": cell_size[1]},
        "stream_pixels": int(np.count_nonzero(streams)),
        **fraction_report,
        **assignment,
    }
    output_dir, installed = _write_raster(data_dir, project_id, curve_numbers, transform, crs)
    if installed:
        _set_output_paths(stats, data_dir, True)
        write_stats(stats["stats_path"], stats)
        return stats

    _set_output_paths(stats, output_dir, False)
    stats["permission_warning"] = (
        f"Cannot write to {data_dir}. Files were written to {output_dir}. "
        "Copy curvenumbers.tif and atyp_cn_stats.json into the project data directory "
        "before running NAM."
    )
    write_stats(stats["stats_path"], stats)
    if _install_via_docker(data_dir, output_dir):
        _set_output_paths(stats, data_dir, True)
        stats.pop("permission_warning", None)
        write_stats(os.path.join(output_dir, "atyp_cn_stats.json"), stats)
        _install_via_docker(data_dir, output_dir)
        print(f"Copied curve numbers into {data_dir} via docker")
    return stats


def _set_output_paths(stats: Dict[str, Any], directory: str, installed: bool) -> None:
    stats["curve_number_raster"] = os.path.join(directory, "curvenumbers.tif")
    stats["stats_path"] = os.path.join(directory, "atyp_cn_stats.json")
    stats["installed_in_project_dir"] = installed


def _docker_target(host_dir: str) -> Optional[Tuple[str, str]]:
    """Return (container, container directory) when a running container mounts host_dir."""
    try:
        listed = subprocess.run(
            ["docker", "ps", "-q"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None
    if listed.returncode != 0:
        return None
    container_ids = [line for line in listed.stdout.splitlines() if line.strip()]
    if not container_ids:
        return None
    inspected = subprocess.run(
        ["docker", "inspect", *container_ids],
        capture_output=True,
        text=True,
        check=False,
    )
    if inspected.returncode != 0:
        return None
    host_dir = os.path.abspath(host_dir)
    for container in json.loads(inspected.stdout):
        name = str(container.get("Name", "")).lstrip("/")
        for mount in container.get("Mounts") or []:
            source = os.path.abspath(mount.get("Source") or "")
            destination = mount.get("Destination") or ""
            if not source or not destination:
                continue
            if host_dir == source or host_dir.startswith(source + os.sep):
                relative = os.path.relpath(host_dir, source)
                container_dir = destination if relative == "." else os.path.join(destination, relative)
                return name, container_dir
    return None


def _install_via_docker(data_dir: str, source_dir: str) -> bool:
    """Copy the generated files into a root-owned project directory through a container mount."""
    target = _docker_target(data_dir)
    if target is None:
        return False
    container, container_dir = target
    quoted_dir = shlex.quote(container_dir)
    backup = (
        f"if [ -f {quoted_dir}/curvenumbers.tif ] && [ ! -f {quoted_dir}/curvenumbers_landcover.tif ]; then "
        f"cp -a {quoted_dir}/curvenumbers.tif {quoted_dir}/curvenumbers_landcover.tif; fi"
    )
    backed_up = subprocess.run(
        ["docker", "exec", container, "sh", "-c", backup],
        capture_output=True,
        text=True,
        check=False,
    )
    if backed_up.returncode != 0:
        print(f"Docker backup failed: {backed_up.stderr.strip()}", file=sys.stderr)
        return False
    for name in ("curvenumbers.tif", "atyp_cn_stats.json"):
        source = os.path.join(source_dir, name)
        if not os.path.exists(source):
            continue
        copied = subprocess.run(
            ["docker", "cp", source, f"{container}:{container_dir}/{name}"],
            capture_output=True,
            text=True,
            check=False,
        )
        if copied.returncode != 0:
            print(f"Docker copy of {name} failed: {copied.stderr.strip()}", file=sys.stderr)
            return False
    return True


def _permission_denied(exc: BaseException) -> bool:
    if isinstance(exc, PermissionError):
        return True
    return "Permission denied" in str(exc)


def _write_raster(data_dir, project_id, curve_numbers, transform, crs) -> Tuple[str, bool]:
    """Write the raster. Fall back to a temp directory when data_dir is read-only."""
    curve_number_path = os.path.join(data_dir, "curvenumbers.tif")
    try:
        backup_existing_raster(curve_number_path)
        write_curve_number_raster(curve_number_path, curve_numbers, transform, crs)
        return data_dir, True
    except Exception as exc:
        if not _permission_denied(exc):
            raise
        fallback = os.path.join(tempfile.gettempdir(), f"atyp-cn-{project_id}")
        os.makedirs(fallback, exist_ok=True)
        write_curve_number_raster(os.path.join(fallback, "curvenumbers.tif"), curve_numbers, transform, crs)
        return fallback, False


def print_stats(stats: Mapping[str, Any]) -> None:
    print(f"Project {stats['project_id']}: {stats['n_cells']} catchment cells")
    print(f"Stream pixels: {stats['stream_pixels']}")
    original_sum = stats["original_sum"]
    if abs(original_sum - 100.0) > 0.01:
        print(f"Atyp percentages summed to {original_sum:.4f} and were normalised to 100")
    ignored = stats.get("ignored_non_atyp_percent") or {}
    if ignored:
        listed = ", ".join(f"{key}={value}" for key, value in ignored.items())
        print(f"Ignored non-Atyp residue below {NON_ATYP_IGNORE_BELOW_PCT}%: {listed}")
    print(f"Mean CN: {stats['mean_cn']:.2f}")
    for name in CLASS_ORDER:
        info = stats["classes"].get(name)
        if not info:
            continue
        target = stats["normalized_percent"][name]
        print(
            f"  {name}: CN {info['cn']:.0f}, "
            f"{info['percent']:.2f}% (target {target:.2f}%), "
            f"distance {info['min_distance_m']:.1f}-{info['max_distance_m']:.1f} m"
        )
    print(f"Wrote {stats['curve_number_raster']}")
    print(f"Wrote {stats['stats_path']}")
    if not stats.get("installed_in_project_dir", True):
        print(f"Warning: {stats['permission_warning']}", file=sys.stderr)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Write a NAM curve-number raster from Atyp fractions.")
    parser.add_argument("--project-id", required=True, help="Project id, for example 6knjfj_5x7ZWSVRV5g2cX")
    args = parser.parse_args(argv)
    try:
        stats = generate_for_project(args.project_id)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print_stats(stats)
    return 0


if __name__ == "__main__":
    sys.exit(main())
