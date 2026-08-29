"""CivilTools - deterministic civil-engineering estimation & code-check helpers.

Bill of Quantities, rate analysis, concrete material take-off (nominal mixes),
reinforcement bar weight, and an indicative IS 456 limiting-moment check. These
support planning/estimation only - a licensed engineer must verify loads, codes
and site conditions and certify the final design.
"""

from __future__ import annotations

import json
from typing import Dict, List

from buddy.tools import Toolkit

# Nominal concrete mixes (cement:sand:coarse aggregate) by grade.
NOMINAL_MIXES: Dict[str, List[float]] = {
    "M5": [1, 5, 10], "M7.5": [1, 4, 8], "M10": [1, 3, 6],
    "M15": [1, 2, 4], "M20": [1, 1.5, 3], "M25": [1, 1, 2],
}
DRY_VOLUME_FACTOR = 1.54  # wet -> dry volume for concrete
CEMENT_M3_PER_BAG = 0.0347  # 50 kg bag ≈ 0.0347 m³

# IS 456 limiting moment factor for Fe-grade steel (Mu,lim = k * fck * b * d²).
K_LIMIT = {250: 0.149, 415: 0.138, 500: 0.133}


class CivilTools(Toolkit):
    def __init__(self, **kwargs):
        super().__init__(
            name="civil_tools",
            tools=[
                self.boq_total,
                self.rate_analysis,
                self.concrete_materials,
                self.rebar_weight,
                self.beam_moment_capacity,
            ],
            **kwargs,
        )

    def boq_total(self, rows: List[Dict[str, object]]) -> str:
        """Total a Bill of Quantities.

        Args:
            rows (List[Dict]): Each item {"description","quantity","unit","rate"}.

        Returns:
            str: JSON with per-line amounts and the grand total.
        """
        try:
            lines, total = [], 0.0
            for r in rows:
                qty = float(r.get("quantity", 0))
                rate = float(r.get("rate", 0))
                amt = qty * rate
                total += amt
                lines.append({"description": r.get("description", ""), "quantity": qty, "unit": r.get("unit", ""), "rate": rate, "amount": round(amt, 2)})
            return json.dumps({"items": lines, "grand_total": round(total, 2)})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def rate_analysis(self, material: float, labour: float, equipment: float = 0.0, overhead_pct: float = 10.0, profit_pct: float = 10.0) -> str:
        """Build a unit rate from component costs plus overhead and profit.

        Args:
            material (float): Material cost per unit of work.
            labour (float): Labour cost per unit.
            equipment (float): Equipment/plant cost per unit.
            overhead_pct (float): Site/establishment overhead in percent.
            profit_pct (float): Contractor profit in percent.

        Returns:
            str: JSON with the built-up unit rate.
        """
        try:
            direct = material + labour + equipment
            with_oh = direct * (1 + overhead_pct / 100.0)
            rate = with_oh * (1 + profit_pct / 100.0)
            return json.dumps({"direct_cost": round(direct, 2), "with_overhead": round(with_oh, 2), "unit_rate": round(rate, 2)})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def concrete_materials(self, wet_volume_m3: float, grade: str = "M20") -> str:
        """Estimate cement/sand/aggregate for a concrete volume (nominal mix).

        Args:
            wet_volume_m3 (float): Finished (wet) concrete volume in cubic metres.
            grade (str): Concrete grade, e.g. "M20" (uses nominal mix ratios).

        Returns:
            str: JSON with cement (bags & m³), sand and coarse aggregate volumes.
        """
        try:
            mix = NOMINAL_MIXES.get(grade.upper())
            if not mix:
                return json.dumps({"error": f"Unknown grade '{grade}'. Known: {list(NOMINAL_MIXES)}"})
            dry = wet_volume_m3 * DRY_VOLUME_FACTOR
            total_parts = sum(mix)
            cement_m3 = dry * mix[0] / total_parts
            sand_m3 = dry * mix[1] / total_parts
            agg_m3 = dry * mix[2] / total_parts
            return json.dumps({
                "grade": grade.upper(),
                "mix_ratio": f"{mix[0]}:{mix[1]}:{mix[2]}",
                "dry_volume_m3": round(dry, 3),
                "cement_m3": round(cement_m3, 3),
                "cement_bags": round(cement_m3 / CEMENT_M3_PER_BAG, 1),
                "sand_m3": round(sand_m3, 3),
                "coarse_aggregate_m3": round(agg_m3, 3),
                "note": "Nominal-mix estimate; use design mix & wastage allowance for execution.",
            })
        except Exception as e:
            return json.dumps({"error": str(e)})

    def rebar_weight(self, diameter_mm: float, length_m: float, count: int = 1) -> str:
        """Weight of reinforcement bars using the d²/162 rule.

        Args:
            diameter_mm (float): Bar diameter in mm.
            length_m (float): Length of one bar in metres.
            count (int): Number of bars.

        Returns:
            str: JSON with weight per metre and total weight in kg.
        """
        try:
            per_m = (diameter_mm ** 2) / 162.0
            total = per_m * length_m * count
            return json.dumps({"kg_per_m": round(per_m, 3), "total_kg": round(total, 2), "diameter_mm": diameter_mm, "count": count})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def beam_moment_capacity(self, b_mm: float, d_mm: float, fck: float, fy: int = 415) -> str:
        """Indicative IS 456 limiting moment of resistance of a singly-reinforced section.

        Args:
            b_mm (float): Width of the section in mm.
            d_mm (float): Effective depth in mm.
            fck (float): Concrete characteristic strength in N/mm² (e.g. 20 for M20).
            fy (int): Steel grade (250/415/500).

        Returns:
            str: JSON with the limiting moment Mu,lim in kN·m. Indicative only.
        """
        try:
            k = K_LIMIT.get(int(fy))
            if k is None:
                return json.dumps({"error": f"Unsupported fy {fy}. Use 250, 415 or 500."})
            mu_nmm = k * fck * b_mm * (d_mm ** 2)
            return json.dumps({
                "fy": fy,
                "k_factor": k,
                "Mu_lim_kNm": round(mu_nmm / 1e6, 2),
                "note": "Indicative limiting moment (singly reinforced). A licensed engineer must do the full IS 456 design.",
            })
        except Exception as e:
            return json.dumps({"error": str(e)})


__all__ = ["CivilTools", "NOMINAL_MIXES", "K_LIMIT"]
