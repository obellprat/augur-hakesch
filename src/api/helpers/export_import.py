"""
Project export and import for AUGUR.
Exports project data (DB + TIF files) to a ZIP archive; imports with new IDs and user linkage.
"""

import io
import json
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from helpers.prisma import prisma

EXPORT_VERSION = 1
PROJECT_FILES = [
    "dem.tif",
    "curvenumbers.tif",
    "isozones_cog.tif",
    "time_values.tif",
    "catchment.geojson",
    "soil.shp",
    "soil.shx",
    "soil.dbf",
    "soil.prj",
]


def _get_project_data_dir(user_id: int, project_id: str) -> Path:
    """Resolve project data directory (supports multiple base paths)."""
    for base in ["data", "src/api/data", "."]:
        p = Path(base) / str(user_id) / project_id
        if p.exists():
            return p
    return Path("data") / str(user_id) / project_id


def _serialize(obj: Any) -> Any:
    """Convert datetime and other non-JSON-serializable types."""
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize(v) for v in obj]
    return obj


def export_project(project_id: str, user_id: int) -> bytes:
    """
    Export a project to a ZIP archive containing SQLite DB and project files.
    Returns the ZIP file as bytes.
    """
    project = prisma.project.find_first(
        where={"id": project_id, "userId": user_id},
        include={
            "Point": True,
            "IDF_Parameters": True,
            "Mod_Fliesszeit": {
                "include": {
                    "Annuality": True,
                    "Mod_Fliesszeit_Result": True,
                    "Mod_Fliesszeit_Result_1_5": True,
                    "Mod_Fliesszeit_Result_2": True,
                    "Mod_Fliesszeit_Result_3": True,
                    "Mod_Fliesszeit_Result_4": True,
                }
            },
            "Koella": {
                "include": {
                    "Annuality": True,
                    "Koella_Result": True,
                    "Koella_Result_1_5": True,
                    "Koella_Result_2": True,
                    "Koella_Result_3": True,
                    "Koella_Result_4": True,
                }
            },
            "ClarkWSL": {
                "include": {
                    "Annuality": True,
                    "ClarkWSL_Result": True,
                    "ClarkWSL_Result_1_5": True,
                    "ClarkWSL_Result_2": True,
                    "ClarkWSL_Result_3": True,
                    "ClarkWSL_Result_4": True,
                    "Fractions": True,
                }
            },
            "NAM": {
                "include": {
                    "Annuality": True,
                    "WaterBalanceMode": True,
                    "StormCenterMode": True,
                    "RoutingMethod": True,
                    "NAM_Result": True,
                    "NAM_Result_1_5": True,
                    "NAM_Result_2": True,
                    "NAM_Result_3": True,
                    "NAM_Result_4": True,
                }
            },
        },
    )

    if not project:
        raise ValueError("Project not found")

    # Collect reference data used by this project
    annuality_ids = set()
    for mf in project.Mod_Fliesszeit or []:
        if mf.Annuality:
            annuality_ids.add(mf.Annuality.id)
    for k in project.Koella or []:
        if k.Annuality:
            annuality_ids.add(k.Annuality.id)
    for c in project.ClarkWSL or []:
        if c.Annuality:
            annuality_ids.add(c.Annuality.id)
    for n in project.NAM or []:
        if n.Annuality:
            annuality_ids.add(n.Annuality.id)

    zone_typs = set()
    for c in project.ClarkWSL or []:
        for f in c.Fractions or []:
            zone_typs.add(f.ZoneParameterTyp)

    annualities = []
    if annuality_ids:
        annualities = prisma.annualities.find_many(
            where={"id": {"in": list(annuality_ids)}}
        )

    zone_params = []
    if zone_typs:
        zone_params = prisma.zoneparameter.find_many(
            where={"typ": {"in": list(zone_typs)}}
        )

    # NAM reference modes
    wb_modes = prisma.waterbalancemode.find_many()
    sc_modes = prisma.stormcentermode.find_many()
    routing_methods = prisma.routingmethod.find_many()

    export_data = {
        "version": EXPORT_VERSION,
        "project": _serialize(project.model_dump(mode="json")),
        "annualities": [_serialize(a.model_dump(mode="json")) for a in annualities],
        "zone_parameters": [
            _serialize(z.model_dump(mode="json")) for z in zone_params
        ],
        "water_balance_modes": [
            _serialize(m.model_dump(mode="json")) for m in wb_modes
        ],
        "storm_center_modes": [
            _serialize(m.model_dump(mode="json")) for m in sc_modes
        ],
        "routing_methods": [
            _serialize(m.model_dump(mode="json")) for m in routing_methods
        ],
    }

    # SQLite for portability (write via tempfile since sqlite3 needs a path)
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        disk_conn = sqlite3.connect(tmp_path)
        disk_conn.execute(
            "CREATE TABLE project_export (key TEXT PRIMARY KEY, value TEXT)"
        )
        disk_conn.execute(
            "INSERT INTO project_export (key, value) VALUES (?, ?)",
            ("data", json.dumps(export_data)),
        )
        disk_conn.commit()
        disk_conn.close()
        with open(tmp_path, "rb") as f:
            sqlite_bytes = f.read()
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    # Collect project files
    project_dir = _get_project_data_dir(user_id, project_id)
    files_in_archive = []
    file_data: dict[str, bytes] = {}

    for fname in PROJECT_FILES:
        fpath = project_dir / fname
        if fpath.exists():
            files_in_archive.append(fname)
            file_data[fname] = fpath.read_bytes()

    manifest = {
        "version": EXPORT_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "project_id": project_id,
        "project_title": project.title,
        "files": files_in_archive,
    }

    # Build ZIP
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))
        zf.writestr("project_data.db", sqlite_bytes)
        for fname, data in file_data.items():
            zf.writestr(f"files/{fname}", data)

    return zip_buf.getvalue()


def import_project(zip_bytes: bytes, user_id: int) -> dict:
    """
    Import a project from a ZIP archive.
    Creates new IDs and links the project to the importing user.
    Returns {"project_id": str, "title": str}.
    """
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        if "manifest.json" not in zf.namelist():
            raise ValueError("Invalid export: missing manifest.json")
        if "project_data.db" not in zf.namelist():
            raise ValueError("Invalid export: missing project_data.db")

        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        db_data = zf.read("project_data.db")

    # Load export data from SQLite
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp.write(db_data)
        tmp_path = tmp.name
    try:
        conn = sqlite3.connect(tmp_path)
        row = conn.execute(
            "SELECT value FROM project_export WHERE key='data'"
        ).fetchone()
        conn.close()
        if not row:
            raise ValueError("Invalid export: empty project_data.db")
        export_data = json.loads(row[0])
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    proj = export_data["project"]
    annualities_export = export_data.get("annualities", [])
    zone_params_export = export_data.get("zone_parameters", [])
    wb_modes_export = export_data.get("water_balance_modes", [])
    sc_modes_export = export_data.get("storm_center_modes", [])
    routing_export = export_data.get("routing_methods", [])

    # Ensure reference data exists; build annuality id mapping (old_id -> new_id)
    ann_map: dict[int, int] = {}
    for a in annualities_export:
        existing = prisma.annualities.find_unique(where={"number": a["number"]})
        if existing:
            ann_map[a["id"]] = existing.id
        else:
            created = prisma.annualities.create(
                data={"description": a["description"], "number": a["number"]}
            )
            ann_map[a["id"]] = created.id

    for z in zone_params_export:
        existing = prisma.zoneparameter.find_unique(where={"typ": z["typ"]})
        if not existing:
            prisma.zoneparameter.create(
                data={
                    "typ": z["typ"],
                    "V0_20": z["V0_20"],
                    "WSV": z["WSV"],
                    "psi": z["psi"],
                    "alpha": z["alpha"],
                }
            )

    for m in wb_modes_export:
        existing = prisma.waterbalancemode.find_unique(where={"mode": m["mode"]})
        if not existing:
            prisma.waterbalancemode.create(
                data={"mode": m["mode"], "description": m["description"]}
            )

    for m in sc_modes_export:
        existing = prisma.stormcentermode.find_unique(where={"mode": m["mode"]})
        if not existing:
            prisma.stormcentermode.create(
                data={"mode": m["mode"], "description": m["description"]}
            )

    for r in routing_export:
        existing = prisma.routingmethod.find_unique(where={"method": r["method"]})
        if not existing:
            prisma.routingmethod.create(
                data={"method": r["method"], "description": r["description"]}
            )

    # Create Point
    point_data = proj.get("Point") or {}
    point = prisma.point.create(
        data={
            "northing": float(point_data.get("northing", 0)),
            "easting": float(point_data.get("easting", 0)),
        }
    )

    # Create IDF_Parameters
    idf_data = proj.get("IDF_Parameters") or {}
    idf_params = prisma.idf_parameters.create(
        data={
            "P_low_1h": float(idf_data.get("P_low_1h", 0)),
            "P_high_1h": float(idf_data.get("P_high_1h", 0)),
            "P_low_24h": float(idf_data.get("P_low_24h", 0)),
            "P_high_24h": float(idf_data.get("P_high_24h", 0)),
            "rp_low": float(idf_data.get("rp_low", 0)),
            "rp_high": float(idf_data.get("rp_high", 0)),
        }
    )

    # Create Project (Prisma generates new nanoid)
    project = prisma.project.create(
        data={
            "title": proj.get("title", "Imported Project"),
            "description": proj.get("description", ""),
            "pointId": point.id,
            "userId": user_id,
            "idfParameterId": idf_params.id,
            "isozones_taskid": proj.get("isozones_taskid", ""),
            "isozones_running": False,
            "catchment_geojson": proj.get("catchment_geojson", ""),
            "catchment_area": float(proj.get("catchment_area", 0)),
            "branches_geojson": proj.get("branches_geojson", ""),
            "channel_length": float(proj.get("channel_length", 0)),
            "cummulative_channel_length": float(
                proj.get("cummulative_channel_length", 0)
            ),
            "delta_h": float(proj.get("delta_h", 0)),
        }
    )

    new_project_id = project.id

    # Mod_Fliesszeit: create Results first, then Mod_Fliesszeit
    for mf in proj.get("Mod_Fliesszeit") or []:
        old_x = mf.get("x")
        if old_x not in ann_map:
            continue
        new_x = ann_map[old_x]

        result_ids = {}
        for suffix, key in [
            ("", "Mod_Fliesszeit_Result"),
            ("_1_5", "Mod_Fliesszeit_Result_1_5"),
            ("_2", "Mod_Fliesszeit_Result_2"),
            ("_3", "Mod_Fliesszeit_Result_3"),
            ("_4", "Mod_Fliesszeit_Result_4"),
        ]:
            res = mf.get(key)
            if res:
                r = prisma.mod_fliesszeit_result.create(
                    data={
                        "HQ": float(res.get("HQ", 0)),
                        "Tc": float(res.get("Tc", 0)),
                        "TB": float(res.get("TB", 0)),
                        "TFl": float(res.get("TFl", 0)),
                        "i": float(res.get("i", 0)),
                        "Vox": float(res.get("Vox", 0)),
                    }
                )
                result_ids[key] = r.id

        mf_data = {
            "x": new_x,
            "Vo20": float(mf.get("Vo20", 0)),
            "psi": float(mf.get("psi", 0)),
            "project_id": new_project_id,
            "TB_start": int(mf.get("TB_start", 30)),
            "istep": int(mf.get("istep", 5)),
            "tol": int(mf.get("tol", 5)),
            "max_iter": int(mf.get("max_iter", 1000)),
        }
        key_map = {
            "Mod_Fliesszeit_Result": "mod_fliesszeit_result_id",
            "Mod_Fliesszeit_Result_1_5": "mod_fliesszeit_result_1_5_id",
            "Mod_Fliesszeit_Result_2": "mod_fliesszeit_result_2_id",
            "Mod_Fliesszeit_Result_3": "mod_fliesszeit_result_3_id",
            "Mod_Fliesszeit_Result_4": "mod_fliesszeit_result_4_id",
        }
        for export_key, prisma_key in key_map.items():
            if export_key in result_ids:
                mf_data[prisma_key] = result_ids[export_key]
        prisma.mod_fliesszeit.create(data=mf_data)

    # Koella
    for k in proj.get("Koella") or []:
        old_x = k.get("x")
        if old_x not in ann_map:
            continue
        new_x = ann_map[old_x]

        result_ids = {}
        for key in [
            "Koella_Result",
            "Koella_Result_1_5",
            "Koella_Result_2",
            "Koella_Result_3",
            "Koella_Result_4",
        ]:
            res = k.get(key)
            if res:
                r = prisma.koella_result.create(
                    data={
                        "HQ": float(res.get("HQ", 0)),
                        "Tc": float(res.get("Tc", 0)),
                        "TB": float(res.get("TB", 0)),
                        "TFl": float(res.get("TFl", 0)),
                        "FLeff": float(res.get("FLeff", 0)),
                        "i_final": float(res.get("i_final", 0)),
                        "i_korrigiert": float(res.get("i_korrigiert", 0)),
                    }
                )
                result_ids[key] = r.id

        koella_data = {
            "x": new_x,
            "Vo20": float(k.get("Vo20", 0)),
            "glacier_area": int(k.get("glacier_area", 0)),
            "project_id": new_project_id,
            "TB_start": int(k.get("TB_start", 30)),
            "tol": int(k.get("tol", 5)),
            "istep": int(k.get("istep", 5)),
            "max_iter": int(k.get("max_iter", 1000)),
        }
        if "Koella_Result" in result_ids:
            koella_data["koella_result_id"] = result_ids["Koella_Result"]
        if "Koella_Result_1_5" in result_ids:
            koella_data["koella_result_1_5_id"] = result_ids["Koella_Result_1_5"]
        if "Koella_Result_2" in result_ids:
            koella_data["koella_result_2_id"] = result_ids["Koella_Result_2"]
        if "Koella_Result_3" in result_ids:
            koella_data["koella_result_3_id"] = result_ids["Koella_Result_3"]
        if "Koella_Result_4" in result_ids:
            koella_data["koella_result_4_id"] = result_ids["Koella_Result_4"]
        prisma.koella.create(data=koella_data)

    # ClarkWSL: create ClarkWSL first (without result ids), then Fractions, then Results, then update ClarkWSL
    for c in proj.get("ClarkWSL") or []:
        old_x = c.get("x")
        if old_x not in ann_map:
            continue
        new_x = ann_map[old_x]

        clark_data = {
            "x": new_x,
            "project_id": new_project_id,
            "dt": int(c.get("dt", 10)),
            "pixel_area_m2": int(c.get("pixel_area_m2", 25)),
        }
        clark = prisma.clarkwsl.create(data=clark_data)

        for frac in c.get("Fractions") or []:
            prisma.fractions.create(
                data={
                    "ZoneParameterTyp": frac["ZoneParameterTyp"],
                    "pct": float(frac.get("pct", 0)),
                    "clarkwsl_id": clark.id,
                }
            )

        result_ids = {}
        for key in [
            "ClarkWSL_Result",
            "ClarkWSL_Result_1_5",
            "ClarkWSL_Result_2",
            "ClarkWSL_Result_3",
            "ClarkWSL_Result_4",
        ]:
            res = c.get(key)
            if res:
                r = prisma.clarkwsl_result.create(
                    data={
                        "Q": float(res.get("Q", 0)),
                        "W": float(res.get("W", 0)),
                        "K": float(res.get("K", 0)),
                        "Tc": float(res.get("Tc", 0)),
                    }
                )
                result_ids[key] = r.id

        update_data = {}
        if "ClarkWSL_Result" in result_ids:
            update_data["clarkwsl_result_id"] = result_ids["ClarkWSL_Result"]
        if "ClarkWSL_Result_1_5" in result_ids:
            update_data["clarkwsl_result_1_5_id"] = result_ids[
                "ClarkWSL_Result_1_5"
            ]
        if "ClarkWSL_Result_2" in result_ids:
            update_data["clarkwsl_result_2_id"] = result_ids["ClarkWSL_Result_2"]
        if "ClarkWSL_Result_3" in result_ids:
            update_data["clarkwsl_result_3_id"] = result_ids["ClarkWSL_Result_3"]
        if "ClarkWSL_Result_4" in result_ids:
            update_data["clarkwsl_result_4_id"] = result_ids["ClarkWSL_Result_4"]
        if update_data:
            prisma.clarkwsl.update(where={"id": clark.id}, data=update_data)

    # NAM
    for n in proj.get("NAM") or []:
        old_x = n.get("x")
        if old_x not in ann_map:
            continue
        new_x = ann_map[old_x]

        result_ids = {}
        for key in [
            "NAM_Result",
            "NAM_Result_1_5",
            "NAM_Result_2",
            "NAM_Result_3",
            "NAM_Result_4",
        ]:
            res = n.get(key)
            if res:
                r = prisma.nam_result.create(
                    data={
                        "HQ": float(res.get("HQ", 0)),
                        "Tc": float(res.get("Tc", 0)),
                        "TB": float(res.get("TB", 0)),
                        "TFl": float(res.get("TFl", 0)),
                        "i": float(res.get("i", 0)),
                        "S": float(res.get("S", 0)),
                        "Ia": float(res.get("Ia", 0)),
                        "Pe": float(res.get("Pe", 0)),
                        "HQ_time": res.get("HQ_time"),
                        "effective_curve_number": res.get("effective_curve_number"),
                    }
                )
                result_ids[key] = r.id

        nam_data = {
            "x": new_x,
            "project_id": new_project_id,
            "precipitation_factor": float(n.get("precipitation_factor", 0.7)),
            "water_balance_mode": n.get("water_balance_mode", "cumulative"),
            "storm_center_mode": n.get("storm_center_mode", "centroid"),
            "routing_method": n.get("routing_method", "time_values"),
            "readiness_to_drain": int(n.get("readiness_to_drain", 0)),
            "use_own_soil_data": bool(n.get("use_own_soil_data", False)),
        }
        if "NAM_Result" in result_ids:
            nam_data["nam_result_id"] = result_ids["NAM_Result"]
        if "NAM_Result_1_5" in result_ids:
            nam_data["nam_result_1_5_id"] = result_ids["NAM_Result_1_5"]
        if "NAM_Result_2" in result_ids:
            nam_data["nam_result_2_id"] = result_ids["NAM_Result_2"]
        if "NAM_Result_3" in result_ids:
            nam_data["nam_result_3_id"] = result_ids["NAM_Result_3"]
        if "NAM_Result_4" in result_ids:
            nam_data["nam_result_4_id"] = result_ids["NAM_Result_4"]
        prisma.nam.create(data=nam_data)

    # Extract files to data/{user_id}/{new_project_id}/
    project_dir = Path("data") / str(user_id) / new_project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        for name in zf.namelist():
            if name.startswith("files/") and not name.endswith("/"):
                fname = name[6:]  # strip "files/"
                target = project_dir / fname
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(zf.read(name))

    return {"project_id": new_project_id, "title": project.title}
