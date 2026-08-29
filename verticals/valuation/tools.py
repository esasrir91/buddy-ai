"""ValuationTools - market & scenario methods that complement FinanceTools' DCF.

Comparable-company multiples, the VC (venture) method, a DCF sensitivity matrix,
and a standards-aligned report section scaffold for a Registered Valuer's report.
Discounting math itself lives in FinanceTools (dcf_valuation/wacc/capm).
"""

from __future__ import annotations

import json
import statistics
from typing import Dict, List

from buddy.tools import Toolkit


class ValuationTools(Toolkit):
    def __init__(self, **kwargs):
        super().__init__(
            name="valuation_tools",
            tools=[
                self.comparable_company_value,
                self.vc_method_value,
                self.dcf_sensitivity,
                self.report_scaffold,
            ],
            **kwargs,
        )

    def comparable_company_value(self, metric_value: float, peer_multiples: List[float], multiple_type: str = "EV/EBITDA") -> str:
        """Imply value from peer trading multiples (relative valuation).

        Args:
            metric_value (float): The subject's metric (e.g. its EBITDA, revenue, or earnings).
            peer_multiples (List[float]): Observed multiples for comparable companies.
            multiple_type (str): Label, e.g. "EV/EBITDA", "EV/Revenue", "P/E".

        Returns:
            str: JSON with implied value at min/median/mean/max peer multiples.
        """
        try:
            m = [float(x) for x in peer_multiples if x is not None]
            if not m:
                return json.dumps({"error": "Provide at least one peer multiple."})
            med = statistics.median(m)
            mean = statistics.fmean(m)
            return json.dumps({
                "multiple_type": multiple_type,
                "metric_value": metric_value,
                "peer_stats": {"min": min(m), "median": round(med, 2), "mean": round(mean, 2), "max": max(m), "n": len(m)},
                "implied_value": {
                    "at_min": round(metric_value * min(m), 2),
                    "at_median": round(metric_value * med, 2),
                    "at_mean": round(metric_value * mean, 2),
                    "at_max": round(metric_value * max(m), 2),
                },
                "note": "EV-based multiples give Enterprise Value; subtract net debt for equity value.",
            })
        except Exception as e:
            return json.dumps({"error": str(e)})

    def vc_method_value(self, exit_earnings: float, exit_multiple: float, target_roi_x: float, years: float, investment: float = 0.0) -> str:
        """Venture-capital method: post-money today from a projected exit.

        Args:
            exit_earnings (float): Projected earnings/EBITDA at exit.
            exit_multiple (float): Exit valuation multiple applied to those earnings.
            target_roi_x (float): Investor's required return as a multiple (e.g. 10 for 10x).
            years (float): Years to exit (for reference/IRR context).
            investment (float): Optional new investment, to compute required ownership.

        Returns:
            str: JSON with terminal value, post-money and pre-money valuations.
        """
        try:
            terminal = float(exit_earnings) * float(exit_multiple)
            post_money = terminal / float(target_roi_x)
            out: Dict[str, object] = {
                "terminal_value_at_exit": round(terminal, 2),
                "post_money_today": round(post_money, 2),
                "years_to_exit": years,
            }
            if investment:
                out["pre_money_today"] = round(post_money - investment, 2)
                out["required_ownership_pct"] = round(investment / post_money * 100, 2)
            return json.dumps(out)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def dcf_sensitivity(self, free_cash_flows: List[float], discount_rates: List[float], terminal_growths: List[float], net_debt: float = 0.0) -> str:
        """Enterprise-value sensitivity matrix across discount rate x terminal growth.

        Args:
            free_cash_flows (List[float]): Projected FCFs for years 1..N.
            discount_rates (List[float]): Discount rates to test (decimals, e.g. [0.11,0.12,0.13]).
            terminal_growths (List[float]): Terminal growth rates to test (decimals).
            net_debt (float): Net debt to bridge EV to equity (reported but EV shown).

        Returns:
            str: JSON matrix of enterprise values keyed by (discount_rate, terminal_growth).
        """
        try:
            fcf = [float(c) for c in free_cash_flows]
            matrix = []
            for dr in discount_rates:
                row = {"discount_rate": dr, "values": []}
                for g in terminal_growths:
                    if dr <= g:
                        row["values"].append({"g": g, "ev": None, "note": "dr<=g"})
                        continue
                    pv = sum(c / ((1 + dr) ** (t + 1)) for t, c in enumerate(fcf))
                    tv = fcf[-1] * (1 + g) / (dr - g)
                    pv_tv = tv / ((1 + dr) ** len(fcf))
                    row["values"].append({"g": g, "ev": round(pv + pv_tv, 2)})
                matrix.append(row)
            return json.dumps({"net_debt": net_debt, "matrix": matrix})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def report_scaffold(self, standard: str = "ICAI VS / IBBI") -> str:
        """Return the standard section structure for a Registered Valuer's report.

        Args:
            standard (str): The valuation standard to align to (default ICAI VS / IBBI).

        Returns:
            str: JSON list of report sections to populate.
        """
        sections = [
            "Background, purpose & intended users of the valuation",
            "Identity of the valuer, registration no. & independence/declaration",
            "Valuation date, scope, and standards adopted",
            "Description of the asset/business and ownership",
            "Sources of information and procedures performed",
            "Assumptions, special assumptions & limiting conditions",
            "Valuation approach(es) and methodology (Income / Market / Cost)",
            "Key inputs (WACC, growth, multiples) with rationale",
            "Valuation workings and reconciliation of approaches",
            "Opinion of value (with range and date)",
            "Caveats, restrictions on use, and signature of Registered Valuer",
        ]
        return json.dumps({"standard": standard, "sections": sections})


__all__ = ["ValuationTools"]
