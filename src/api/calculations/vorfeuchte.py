"""
Vorfeuchte (pre-moisture) handling for 100-year discharge events.

ARK1–ARK5 in documentation correspond to zone types "Atyp 1" … "Atyp 5".
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

# Canonical HAKESCH keys for Abflussreaktionsklassen 1–5
ATYP_KEYS: tuple[str, ...] = tuple(f"Atyp {i}" for i in range(1, 6))


def normalize_zone_typ_key(typ: str) -> str:
    """Map ARK1..ARK5 labels to Atyp 1..5 if needed."""
    t = str(typ).strip()
    upper = t.upper().replace(" ", "")
    if upper.startswith("ARK"):
        rest = upper[3:]
        if rest.isdigit() and 1 <= int(rest) <= 5:
            return f"Atyp {int(rest)}"
    return t


def shift_atyp_fractions_pre_moisture(
    fractions_list: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Shift area fractions p for ARK/Atyp 1–5 per Vorfeuchte rules (100y event).
    Other zone types (e.g. Siedlung) are left unchanged.

    p5_vf = 0
    p4_vf = 100%*p5_t + 25%*p4_t
    p3_vf = 75%*p4_t + 50%*p3_t
    p2_vf = 50%*p3_t + 50%*p2_t
    p1_vf = 50%*p2_t + 100%*p1_t
    """
    by_typ: Dict[str, float] = {}
    for f in fractions_list:
        t = normalize_zone_typ_key(str(f.get("typ", "")))
        pct = float(f.get("pct") or 0)
        by_typ[t] = by_typ.get(t, 0.0) + pct

    p1 = by_typ.get("Atyp 1", 0.0)
    p2 = by_typ.get("Atyp 2", 0.0)
    p3 = by_typ.get("Atyp 3", 0.0)
    p4 = by_typ.get("Atyp 4", 0.0)
    p5 = by_typ.get("Atyp 5", 0.0)

    p5_vf = 0.0
    p4_vf = 1.0 * p5 + 0.25 * p4
    p3_vf = 0.75 * p4 + 0.50 * p3
    p2_vf = 0.50 * p3 + 0.50 * p2
    p1_vf = 0.50 * p2 + 1.00 * p1

    vf_map = {
        "Atyp 1": p1_vf,
        "Atyp 2": p2_vf,
        "Atyp 3": p3_vf,
        "Atyp 4": p4_vf,
        "Atyp 5": p5_vf,
    }

    out: List[Dict[str, Any]] = []
    for f in fractions_list:
        raw_typ = str(f.get("typ", ""))
        t = normalize_zone_typ_key(raw_typ)
        if t in vf_map:
            out.append({"typ": t, "pct": vf_map[t]})
        else:
            out.append({"typ": raw_typ, "pct": float(f.get("pct") or 0)})
    return out


def _weighted_atyp_mean(
    fractions_list: Sequence[Mapping[str, Any]],
    zone_parameters: Mapping[str, Mapping[str, float]],
    param_key: str,
) -> Optional[float]:
    num = 0.0
    den = 0.0
    for f in fractions_list:
        t = normalize_zone_typ_key(str(f.get("typ", "")))
        if t not in ATYP_KEYS:
            continue
        p = float(f.get("pct") or 0)
        if p <= 0:
            continue
        zp = zone_parameters.get(t)
        if not zp or param_key not in zp:
            continue
        num += p * float(zp[param_key])
        den += p
    if den <= 0:
        return None
    return num / den


def default_uniform_atyp_fractions() -> List[Dict[str, float]]:
    """20% each Atyp 1–5 when no Clark fractions are available."""
    return [{"typ": f"Atyp {i}", "pct": 20.0} for i in range(1, 6)]


def pre_moisture_scale_psi_vo20(
    psi: float,
    Vo20: float,
    fractions_list: Optional[Sequence[Mapping[str, Any]]],
    zone_parameters: Mapping[str, Mapping[str, float]],
) -> tuple[float, float]:
    """
    Scale catchment psi and Vo20 using dry vs Vorfeuchte-shifted Atyp mix
    and HAKESCH reference psi / V0_20 per class.
    """
    base = list(fractions_list) if fractions_list is not None else default_uniform_atyp_fractions()
    shifted = shift_atyp_fractions_pre_moisture(base)

    dry_psi = _weighted_atyp_mean(base, zone_parameters, "psi")
    wet_psi = _weighted_atyp_mean(shifted, zone_parameters, "psi")
    dry_v0 = _weighted_atyp_mean(base, zone_parameters, "V0_20")
    wet_v0 = _weighted_atyp_mean(shifted, zone_parameters, "V0_20")

    r_psi = (wet_psi / dry_psi) if (dry_psi and wet_psi) else 1.0
    r_v0 = (wet_v0 / dry_v0) if (dry_v0 and wet_v0) else 1.0

    return float(psi * r_psi), float(Vo20 * r_v0)
