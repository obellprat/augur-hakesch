#!/usr/bin/env python3
"""
Compare NAM peak discharge for every project of one user.

For return period 100 and the current climate, each project is run twice:

- land-use curve numbers
- Atyp curve numbers

NAM2 always uses precipitation factor 1. The stored project factor is written
to the CSV and does not change the rainfall.

Results are appended to a CSV. NAM_Result rows in the database are not updated.
The land-use raster is kept as curvenumbers_landcover.tif. curvenumbers.tif is
left as the Atyp raster.

Usage:
    python scripts/export_nam_hq_comparison.py --user-id 2
"""

import argparse
import csv
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import traceback
from typing import Any, Dict, List, Optional

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, ".."))
_API_DIR = os.path.join(_PROJECT_ROOT, "src", "api")
sys.path.insert(0, _SCRIPT_DIR)
sys.path.insert(0, _API_DIR)

import generate_atyp_curvenumbers as atyp_cn
# import calculations.nam as nam_module
from calculations.nam2 import nam2 as nam_module

FIELDNAMES = [
    "Projekt_ID",
    "Projekttitel",
    "Beschreibung",
    "Einzugsgebietsgroesse_km2",
    "Max_Fliesslaenge_m",
    "Kumulative_Fliesslaenge_m",
    "Hoehendifferenz_m",
    "Ost",
    "Nord",
    "Niederschlagsfaktor",
    "Abflussbereitschaft",
    "Wasserbilanzmodus",
    "Sturmzentrummodus",
    "Routing_Methode",
    "Eigene_Bodendaten",
    "P_low_1h",
    "P_high_1h",
    "P_low_24h",
    "P_high_24h",
    "rp_low",
    "rp_high",
    "Atyp_1_pct",
    "Atyp_2_pct",
    "Atyp_3_pct",
    "Atyp_4_pct",
    "Atyp_5_pct",
    "Siedl_typ_1_pct",
    "Weitere_Abflusstypen",
    "Mod_Fliesszeit_Vo20",
    "Mod_Fliesszeit_psi",
    "Koella_Vo20",
    "Koella_Gletscherflaeche",
    "HQ_100_current_Mod_Fliesszeit",
    "HQ_100_current_Koella",
    "HQ_100_current_Clark_WSL",
    "HQ_100_current_Landuse_CN",
    "HQ_100_current_Atyp_CN",
    "Fehler",
]

ATYP_COLUMNS = {
    "Atyp 1": "Atyp_1_pct",
    "Atyp 2": "Atyp_2_pct",
    "Atyp 3": "Atyp_3_pct",
    "Atyp 4": "Atyp_4_pct",
    "Atyp 5": "Atyp_5_pct",
    "Siedl.typ 1": "Siedl_typ_1_pct",
}


def load_projects(user_id: int) -> List[Dict[str, Any]]:
    """Load scalar project fields only. Full Prisma records include catchment geometry and time out."""
    import psycopg2
    from dotenv import load_dotenv

    load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))
    database_url = os.environ["DATABASE_URL"].split("?", 1)[0]
    connection = psycopg2.connect(database_url)
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT p.id, p.title, p.description, p."userId",
                   p.catchment_area, p.channel_length, p.cummulative_channel_length, p.delta_h,
                   pt.easting, pt.northing,
                   n.id, n.precipitation_factor, n.water_balance_mode,
                   n.storm_center_mode, n.routing_method, n.readiness_to_drain,
                   n.use_own_soil_data,
                   i."P_low_1h", i."P_high_1h", i."P_low_24h", i."P_high_24h",
                   i.rp_low, i.rp_high,
                   mf."HQ", mf."Vo20", mf.psi,
                   ko."HQ", ko."Vo20", ko.glacier_area,
                   cw."Q",
                   fr.fractions
            FROM "Project" p
            LEFT JOIN "Point" pt ON pt.id = p."pointId"
            LEFT JOIN "IDF_Parameters" i ON i.id = p."idfParameterId"
            LEFT JOIN LATERAL (
                SELECT n.id, n.precipitation_factor, n.water_balance_mode,
                       n.storm_center_mode, n.routing_method, n.readiness_to_drain,
                       n.use_own_soil_data
                FROM "NAM" n
                JOIN "Annualities" a ON a.id = n.x
                WHERE n.project_id = p.id AND a.number = 100
                LIMIT 1
            ) n ON true
            LEFT JOIN LATERAL (
                SELECT r."HQ", m."Vo20", m.psi
                FROM "Mod_Fliesszeit" m
                JOIN "Annualities" a ON a.id = m.x
                LEFT JOIN "Mod_Fliesszeit_Result" r ON r.id = m.mod_fliesszeit_result_id
                WHERE m.project_id = p.id AND a.number = 100
                LIMIT 1
            ) mf ON true
            LEFT JOIN LATERAL (
                SELECT r."HQ", k."Vo20", k.glacier_area
                FROM "Koella" k
                JOIN "Annualities" a ON a.id = k.x
                LEFT JOIN "Koella_Result" r ON r.id = k.koella_result_id
                WHERE k.project_id = p.id AND a.number = 100
                LIMIT 1
            ) ko ON true
            LEFT JOIN LATERAL (
                SELECT r."Q"
                FROM "ClarkWSL" c
                JOIN "Annualities" a ON a.id = c.x
                LEFT JOIN "ClarkWSL_Result" r ON r.id = c.clarkwsl_result_id
                WHERE c.project_id = p.id AND a.number = 100
                LIMIT 1
            ) cw ON true
            LEFT JOIN LATERAL (
                SELECT json_object_agg(summed.typ, summed.pct) AS fractions
                FROM (
                    SELECT f."ZoneParameterTyp" AS typ, SUM(f.pct) AS pct
                    FROM "ClarkWSL" c
                    JOIN "Fractions" f ON f.clarkwsl_id = c.id
                    WHERE c.project_id = p.id
                      AND c.id = (
                          SELECT c2.id
                          FROM "ClarkWSL" c2
                          JOIN "Annualities" a2 ON a2.id = c2.x
                          WHERE c2.project_id = p.id
                          ORDER BY (a2.number = 100) DESC, a2.number
                          LIMIT 1
                      )
                    GROUP BY f."ZoneParameterTyp"
                ) summed
            ) fr ON true
            WHERE p."userId" = %s
            ORDER BY p.title, p.id
            """,
            (user_id,),
        )
        fetched = cursor.fetchall()
    finally:
        connection.close()

    rows = []
    for record in fetched:
        (
            project_id, title, description, owner_id,
            catchment_area, channel_length, cumulative_channel_length, delta_h,
            easting, northing,
            nam_id, precipitation_factor, water_balance_mode,
            storm_center_mode, routing_method, readiness_to_drain,
            use_own_soil_data,
            p_low_1h, p_high_1h, p_low_24h, p_high_24h,
            rp_low, rp_high,
            hq_mod_fliesszeit, mod_fliesszeit_vo20, mod_fliesszeit_psi,
            hq_koella, koella_vo20, koella_glacier_area,
            hq_clark_wsl,
            fractions,
        ) = record
        idf = None
        if p_low_1h is not None:
            idf = {
                "P_low_1h": p_low_1h,
                "P_high_1h": p_high_1h,
                "P_low_24h": p_low_24h,
                "P_high_24h": p_high_24h,
                "rp_low": rp_low,
                "rp_high": rp_high,
            }
        rows.append(
            {
                "project_id": project_id,
                "title": title or "",
                "description": description or "",
                "user_id": owner_id,
                "nam_id": nam_id,
                "precipitation_factor": None if precipitation_factor is None else float(precipitation_factor),
                "water_balance_mode": water_balance_mode,
                "storm_center_mode": storm_center_mode,
                "routing_method": routing_method,
                "readiness_to_drain": readiness_to_drain,
                "use_own_soil_data": use_own_soil_data,
                "catchment_area": catchment_area,
                "channel_length": channel_length,
                "cumulative_channel_length": cumulative_channel_length,
                "delta_h": delta_h,
                "easting": easting,
                "northing": northing,
                "idf": idf,
                "fractions": fractions,
                "hq_mod_fliesszeit": hq_mod_fliesszeit,
                "mod_fliesszeit_vo20": mod_fliesszeit_vo20,
                "mod_fliesszeit_psi": mod_fliesszeit_psi,
                "hq_koella": hq_koella,
                "koella_vo20": koella_vo20,
                "koella_glacier_area": koella_glacier_area,
                "hq_clark_wsl": hq_clark_wsl,
            }
        )
    return rows


def preserve_landcover(data_dir: str) -> str:
    """Keep the current curve-number raster as the land-use backup, once."""
    current = os.path.join(data_dir, "curvenumbers.tif")
    landcover = os.path.join(data_dir, "curvenumbers_landcover.tif")
    if os.path.exists(landcover):
        return landcover
    if not os.path.exists(current):
        raise FileNotFoundError(f"Curve number raster not found: {current}")

    target = atyp_cn._docker_target(data_dir)
    if target is not None:
        container, container_dir = target
        quoted = shlex.quote(container_dir)
        copied = subprocess.run(
            [
                "docker",
                "exec",
                container,
                "sh",
                "-c",
                f"cp -a {quoted}/curvenumbers.tif {quoted}/curvenumbers_landcover.tif",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if copied.returncode != 0 or not os.path.exists(landcover):
            raise RuntimeError(copied.stderr.strip() or "Could not back up the land-use curve numbers")
        return landcover

    shutil.copy2(current, landcover)
    return landcover


def install_curve_numbers(data_dir: str, source_tif: str) -> None:
    """Make NAM read source_tif by placing it at curvenumbers.tif."""
    staging = tempfile.mkdtemp(prefix="cn-swap-")
    try:
        shutil.copy2(source_tif, os.path.join(staging, "curvenumbers.tif"))
        if atyp_cn._install_via_docker(data_dir, staging):
            return
        shutil.copy2(source_tif, os.path.join(data_dir, "curvenumbers.tif"))
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def run_nam(project: Dict[str, Any]) -> float:
    if project["nam_id"] is None:
        raise ValueError("No NAM entry for return period 100")
    if project["idf"] is None:
        raise ValueError("Project has no IDF parameters")
    discharge_point = None
    if project["easting"] is not None and project["northing"] is not None:
        discharge_point = (project["easting"], project["northing"])
    idf = project["idf"]
    result = nam_module.__wrapped__(
        P_low_1h=float(idf["P_low_1h"]),
        P_high_1h=float(idf["P_high_1h"]),
        P_low_24h=float(idf["P_low_24h"]),
        P_high_24h=float(idf["P_high_24h"]),
        rp_low=float(idf["rp_low"]),
        rp_high=float(idf["rp_high"]),
        x=100,
        curve_number=70.0,
        catchment_area=float(project["catchment_area"]),
        channel_length=float(project["channel_length"]),
        delta_h=float(project["delta_h"]),
        nam_id=project["nam_id"],
        project_id=project["project_id"],
        user_id=project["user_id"],
        water_balance_mode=project["water_balance_mode"],
        precipitation_factor=1.0,
        storm_center_mode=project["storm_center_mode"],
        routing_method=project["routing_method"],
        readiness_to_drain=project["readiness_to_drain"],
        discharge_point=discharge_point,
        discharge_point_crs="EPSG:2056",
        climate_scenario="current",
        debug=False,
        persist=False,
    )
    if not isinstance(result, dict) or "error" in result or "HQ" not in result:
        message = result.get("error") if isinstance(result, dict) else "NAM returned no HQ"
        raise RuntimeError(message)
    return float(result["HQ"])


def _hq(value: Any) -> Any:
    if value is None:
        return ""
    return float(value)


def _text(value: Any) -> Any:
    if value is None:
        return ""
    return value


def _bool_cell(value: Any) -> Any:
    if value is None:
        return ""
    return bool(value)


def _fraction_columns(raw: Any) -> Dict[str, Any]:
    """Map stored Clark-WSL shares onto the fixed Atyp columns."""
    columns: Dict[str, Any] = {name: "" for name in ATYP_COLUMNS.values()}
    extras: List[str] = []
    if isinstance(raw, str):
        raw = json.loads(raw)
    if not raw:
        columns["Weitere_Abflusstypen"] = ""
        return columns

    merged: Dict[str, float] = {}
    for typ, pct in raw.items():
        if pct is None:
            continue
        name = atyp_cn.canonical_class_name(str(typ)) or str(typ)
        merged[name] = merged.get(name, 0.0) + float(pct)

    for name, pct in sorted(merged.items()):
        column = ATYP_COLUMNS.get(name)
        if column:
            columns[column] = pct
        elif pct:
            extras.append(f"{name}={pct:g}")
    columns["Weitere_Abflusstypen"] = "; ".join(extras)
    return columns


def _result_row(project: Dict[str, Any], fehler: str = "") -> Dict[str, Any]:
    idf = project.get("idf") or {}
    row = {
        "Projekt_ID": project["project_id"],
        "Projekttitel": project["title"],
        "Beschreibung": project["description"],
        "Einzugsgebietsgroesse_km2": _hq(project.get("catchment_area")),
        "Max_Fliesslaenge_m": _hq(project.get("channel_length")),
        "Kumulative_Fliesslaenge_m": _hq(project.get("cumulative_channel_length")),
        "Hoehendifferenz_m": _hq(project.get("delta_h")),
        "Ost": _hq(project.get("easting")),
        "Nord": _hq(project.get("northing")),
        "Niederschlagsfaktor": _hq(project.get("precipitation_factor")),
        "Abflussbereitschaft": _hq(project.get("readiness_to_drain")),
        "Wasserbilanzmodus": _text(project.get("water_balance_mode")),
        "Sturmzentrummodus": _text(project.get("storm_center_mode")),
        "Routing_Methode": _text(project.get("routing_method")),
        "Eigene_Bodendaten": _bool_cell(project.get("use_own_soil_data")),
        "P_low_1h": _hq(idf.get("P_low_1h")),
        "P_high_1h": _hq(idf.get("P_high_1h")),
        "P_low_24h": _hq(idf.get("P_low_24h")),
        "P_high_24h": _hq(idf.get("P_high_24h")),
        "rp_low": _hq(idf.get("rp_low")),
        "rp_high": _hq(idf.get("rp_high")),
        "Mod_Fliesszeit_Vo20": _hq(project.get("mod_fliesszeit_vo20")),
        "Mod_Fliesszeit_psi": _hq(project.get("mod_fliesszeit_psi")),
        "Koella_Vo20": _hq(project.get("koella_vo20")),
        "Koella_Gletscherflaeche": _hq(project.get("koella_glacier_area")),
        "HQ_100_current_Mod_Fliesszeit": _hq(project.get("hq_mod_fliesszeit")),
        "HQ_100_current_Koella": _hq(project.get("hq_koella")),
        "HQ_100_current_Clark_WSL": _hq(project.get("hq_clark_wsl")),
        "HQ_100_current_Landuse_CN": "",
        "HQ_100_current_Atyp_CN": "",
        "Fehler": fehler,
    }
    row.update(_fraction_columns(project.get("fractions")))
    return row


def compare_project(project: Dict[str, Any]) -> Dict[str, Any]:
    row = _result_row(project)
    errors = []
    try:
        data_dir = atyp_cn.project_data_dir(project["user_id"], project["project_id"])
        landcover = preserve_landcover(data_dir)
        install_curve_numbers(data_dir, landcover)
        row["HQ_100_current_Landuse_CN"] = run_nam(project)
    except Exception as exc:
        errors.append(f"Landuse: {exc}")

    try:
        atyp_cn.generate_for_project(project["project_id"])
        row["HQ_100_current_Atyp_CN"] = run_nam(project)
    except Exception as exc:
        errors.append(f"Atyp: {exc}")

    row["Fehler"] = " | ".join(errors)
    return row


def write_row(path: str, row: Dict[str, Any], write_header: bool) -> None:
    with open(path, "a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        if write_header:
            writer.writeheader()
        writer.writerow(row)
        handle.flush()


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Export NAM HQ for land-use and Atyp curve numbers.")
    parser.add_argument("--user-id", type=int, default=2)
    parser.add_argument("--project-id", default=None, help="Run a single project instead of the whole user")
    parser.add_argument(
        "--output",
        default=os.path.join(_SCRIPT_DIR, "nam_hq_cn_comparison.csv"),
        help="CSV path",
    )
    args = parser.parse_args(argv)

    projects = load_projects(args.user_id)
    if args.project_id:
        projects = [project for project in projects if project["project_id"] == args.project_id]
    if not projects:
        print("No projects found", file=sys.stderr)
        return 1

    if os.path.exists(args.output):
        os.remove(args.output)

    print(f"Projects: {len(projects)}")
    print(f"Output: {args.output}")
    for index, project in enumerate(projects, start=1):
        print(f"\n[{index}/{len(projects)}] {project['title']} ({project['project_id']})", flush=True)
        try:
            row = compare_project(project)
        except Exception:
            traceback.print_exc()
            row = _result_row(project, fehler=traceback.format_exc(limit=1).strip())
        write_row(args.output, row, write_header=index == 1)
        print(
            f"  Landuse {row['HQ_100_current_Landuse_CN']} | "
            f"Atyp {row['HQ_100_current_Atyp_CN']}"
        )
        if row["Fehler"]:
            print(f"  Fehler: {row['Fehler']}")
    print(f"\nWrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
