#!/usr/bin/env python3
"""
Print Standard vs. Vorfeuchte (100-jährlich) discharge metrics for all projects
owned by user id=2 (Testgebiete).

Run from repository root with API environment (DATABASE_URL, etc.):

  cd src/api && python3 scripts/compare_vorfeuchte_user2.py

This script runs calculations in-process (no Celery). Clark-WSL and NAM are
computed too *if* their required raster assets are available for the project.
"""

from __future__ import annotations

import sys
import io
import warnings
import csv
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from calculations.discharge import (  # noqa: E402
    HAKESCH_ZONE_PARAMS,
    clark_wsl_modified,
    koella_standardVo,
    modifizierte_fliesszeit_standardVo,
)
from calculations.nam import nam  # noqa: E402
from helpers.prisma import prisma  # noqa: E402
from routers.discharge import _clark_fractions_for_annuity  # noqa: E402


def _row_annuity_100(rows, ann_rel):
    for row in rows or []:
        ann = getattr(row, ann_rel, None)
        if ann is not None and float(ann.number) == 100.0:
            return row
    return None


def main() -> None:
    warnings.filterwarnings("ignore", category=RuntimeWarning)

    prisma.connect()
    try:
        projects = prisma.project.find_many(
            where={"userId": 2},
            include={
                "IDF_Parameters": True,
                "Point": True,
                "Mod_Fliesszeit": {"include": {"Annuality": True}},
                "Koella": {"include": {"Annuality": True}},
                "ClarkWSL": {"include": {"Annuality": True, "Fractions": True}},
                "NAM": {"include": {"Annuality": True}},
            },
        )
    finally:
        prisma.disconnect()

    if not projects:
        # Emit header-only CSV for consistency
        writer = csv.DictWriter(
            sys.stdout,
            fieldnames=[
                "ProjektName",
                "ProjektId",
                "modFliesszeit_standard",
                "modFliesszeit_vorfeuchte",
                "koella_standard",
                "koella_vorfeuchte",
                "clarkwsl_standard",
                "clarkwsl_vorfeuchte",
                "nam_standard",
                "nam_vorfeuchte",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        return

    writer = csv.DictWriter(
        sys.stdout,
        fieldnames=[
            "ProjektName",
            "ProjektId",
            "modFliesszeit_standard",
            "modFliesszeit_vorfeuchte",
            "koella_standard",
            "koella_vorfeuchte",
            "clarkwsl_standard",
            "clarkwsl_vorfeuchte",
            "nam_standard",
            "nam_vorfeuchte",
        ],
        lineterminator="\n",
    )
    writer.writeheader()

    for p in projects:
        if not p.IDF_Parameters or not p.Point:
            continue
        row = {
            "ProjektName": p.title,
            "ProjektId": p.id,
            "modFliesszeit_standard": "",
            "modFliesszeit_vorfeuchte": "",
            "koella_standard": "",
            "koella_vorfeuchte": "",
            "clarkwsl_standard": "",
            "clarkwsl_vorfeuchte": "",
            "nam_standard": "",
            "nam_vorfeuchte": "",
        }
        idf = p.IDF_Parameters
        pt = p.Point
        fracs_fn = lambda ann: _clark_fractions_for_annuity(p, ann)  # noqa: E731

        mf = _row_annuity_100(p.Mod_Fliesszeit, "Annuality")
        if mf:
            f100 = fracs_fn(mf.Annuality.number)
            std = modifizierte_fliesszeit_standardVo(
                None,
                idf.P_low_1h,
                idf.P_high_1h,
                idf.P_low_24h,
                idf.P_high_24h,
                idf.rp_low,
                idf.rp_high,
                100,
                mf.Vo20,
                p.channel_length,
                p.delta_h,
                mf.psi,
                p.catchment_area,
                mf.id,
                project_easting=pt.easting,
                project_northing=pt.northing,
                climate_scenario="current",
                use_pre_moisture=False,
                atyp_fractions=f100,
            )
            wet = modifizierte_fliesszeit_standardVo(
                None,
                idf.P_low_1h,
                idf.P_high_1h,
                idf.P_low_24h,
                idf.P_high_24h,
                idf.rp_low,
                idf.rp_high,
                100,
                mf.Vo20,
                p.channel_length,
                p.delta_h,
                mf.psi,
                p.catchment_area,
                mf.id,
                project_easting=pt.easting,
                project_northing=pt.northing,
                climate_scenario="current",
                use_pre_moisture=True,
                atyp_fractions=f100,
            )
            row["modFliesszeit_standard"] = f"{std['HQ']:.6f}"
            row["modFliesszeit_vorfeuchte"] = f"{wet['HQ']:.6f}"

        k = _row_annuity_100(p.Koella, "Annuality")
        if k:
            f100 = fracs_fn(k.Annuality.number)
            std = koella_standardVo(
                None,
                idf.P_low_1h,
                idf.P_high_1h,
                idf.P_low_24h,
                idf.P_high_24h,
                idf.rp_low,
                idf.rp_high,
                100,
                k.Vo20,
                p.cummulative_channel_length / 1000,
                p.catchment_area,
                k.glacier_area,
                k.id,
                project_easting=pt.easting,
                project_northing=pt.northing,
                climate_scenario="current",
                use_pre_moisture=False,
                atyp_fractions=f100,
            )
            wet = koella_standardVo(
                None,
                idf.P_low_1h,
                idf.P_high_1h,
                idf.P_low_24h,
                idf.P_high_24h,
                idf.rp_low,
                idf.rp_high,
                100,
                k.Vo20,
                p.cummulative_channel_length / 1000,
                p.catchment_area,
                k.glacier_area,
                k.id,
                project_easting=pt.easting,
                project_northing=pt.northing,
                climate_scenario="current",
                use_pre_moisture=True,
                atyp_fractions=f100,
            )
            row["koella_standard"] = f"{std['HQ']:.6f}"
            row["koella_vorfeuchte"] = f"{wet['HQ']:.6f}"

        cw = _row_annuity_100(p.ClarkWSL, "Annuality")
        if cw:
            try:
                fractions = [
                    {"typ": f.ZoneParameterTyp, "pct": f.pct}
                    for f in cw.Fractions
                ]
                # clark_wsl_modified is a Celery task; use .run() for local execution
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    std = clark_wsl_modified.run(
                        P_low_1h=idf.P_low_1h,
                        P_high_1h=idf.P_high_1h,
                        P_low_24h=idf.P_low_24h,
                        P_high_24h=idf.P_high_24h,
                        rp_low=idf.rp_low,
                        rp_high=idf.rp_high,
                        discharge_types_parameters=HAKESCH_ZONE_PARAMS,
                        x=100,
                        fractions_dict=fractions,
                        clark_wsl=cw.id,
                        project_id=p.id,
                        user_id=2,  # userId for data/<user>/<project>/...
                        project_easting=pt.easting,
                        project_northing=pt.northing,
                        climate_scenario="current",
                        dt=cw.dt,
                        pixel_area_m2=cw.pixel_area_m2,
                        use_pre_moisture=False,
                        persist_result=False,
                    )
                    wet = clark_wsl_modified.run(
                        P_low_1h=idf.P_low_1h,
                        P_high_1h=idf.P_high_1h,
                        P_low_24h=idf.P_low_24h,
                        P_high_24h=idf.P_high_24h,
                        rp_low=idf.rp_low,
                        rp_high=idf.rp_high,
                        discharge_types_parameters=HAKESCH_ZONE_PARAMS,
                        x=100,
                        fractions_dict=fractions,
                        clark_wsl=cw.id,
                        project_id=p.id,
                        user_id=2,
                        project_easting=pt.easting,
                        project_northing=pt.northing,
                        climate_scenario="current",
                        dt=cw.dt,
                        pixel_area_m2=cw.pixel_area_m2,
                        use_pre_moisture=True,
                        persist_result=False,
                    )
                row["clarkwsl_standard"] = f"{max(std['Q']):.6f}"
                row["clarkwsl_vorfeuchte"] = f"{max(wet['Q']):.6f}"
            except Exception as e:
                # keep empty cells; could be missing rasters etc.
                _ = e

        nm = _row_annuity_100(p.NAM, "Annuality")
        if nm:
            try:
                # nam is a Celery task; use .run() for local execution
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    std = nam.run(
                        P_low_1h=idf.P_low_1h,
                        P_high_1h=idf.P_high_1h,
                        P_low_24h=idf.P_low_24h,
                        P_high_24h=idf.P_high_24h,
                        rp_low=idf.rp_low,
                        rp_high=idf.rp_high,
                        x=100,
                        curve_number=70.0,
                        catchment_area=p.catchment_area,
                        channel_length=p.channel_length,
                        delta_h=p.delta_h,
                        nam_id=nm.id,
                        project_id=p.id,
                        user_id=2,
                        water_balance_mode=nm.water_balance_mode,
                        precipitation_factor=nm.precipitation_factor,
                        storm_center_mode=nm.storm_center_mode,
                        routing_method=nm.routing_method,
                        readiness_to_drain=nm.readiness_to_drain,
                        discharge_point=(pt.easting, pt.northing),
                        discharge_point_crs="EPSG:2056",
                        project_easting=pt.easting,
                        project_northing=pt.northing,
                        climate_scenario="current",
                        debug=False,
                        use_pre_moisture=False,
                        persist_result=False,
                    )
                    wet = nam.run(
                        P_low_1h=idf.P_low_1h,
                        P_high_1h=idf.P_high_1h,
                        P_low_24h=idf.P_low_24h,
                        P_high_24h=idf.P_high_24h,
                        rp_low=idf.rp_low,
                        rp_high=idf.rp_high,
                        x=100,
                        curve_number=70.0,
                        catchment_area=p.catchment_area,
                        channel_length=p.channel_length,
                        delta_h=p.delta_h,
                        nam_id=nm.id,
                        project_id=p.id,
                        user_id=2,
                        water_balance_mode=nm.water_balance_mode,
                        precipitation_factor=nm.precipitation_factor,
                        storm_center_mode=nm.storm_center_mode,
                        routing_method=nm.routing_method,
                        readiness_to_drain=nm.readiness_to_drain,
                        discharge_point=(pt.easting, pt.northing),
                        discharge_point_crs="EPSG:2056",
                        project_easting=pt.easting,
                        project_northing=pt.northing,
                        climate_scenario="current",
                        debug=False,
                        use_pre_moisture=True,
                        persist_result=False,
                    )
                row["nam_standard"] = f"{std['HQ']:.6f}"
                row["nam_vorfeuchte"] = f"{wet['HQ']:.6f}"
            except Exception as e:
                _ = e

        writer.writerow(row)

if __name__ == "__main__":
    main()
