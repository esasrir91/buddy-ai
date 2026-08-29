"""CATools - India-first deterministic accounting/tax helpers for the CA copilot.

Covers the everyday arithmetic a Chartered Accountant needs done *exactly*: GST
tax splits, indicative TDS computation, financial-statement ratios, and the
statutory compliance calendar. Rates change with the Finance Act / notifications,
so outputs flag that the user must confirm against current law.
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional

from buddy.tools import Toolkit

# Indicative TDS sections (resident payees). RATES CHANGE - always verify against
# the current Finance Act / CBDT notifications before relying on these.
TDS_SECTIONS: Dict[str, Dict[str, object]] = {
    "194C": {"nature": "Payment to contractor", "rate_individual_huf": 1.0, "rate_other": 2.0, "threshold_single": 30000, "threshold_annual": 100000},
    "194J": {"nature": "Professional/technical fees", "rate_professional": 10.0, "rate_technical": 2.0, "threshold_annual": 30000},
    "194H": {"nature": "Commission or brokerage", "rate": 2.0, "threshold_annual": 20000},
    "194I_land_building": {"nature": "Rent - land/building", "rate": 10.0, "threshold_annual": 240000},
    "194I_plant_machinery": {"nature": "Rent - plant/machinery", "rate": 2.0, "threshold_annual": 240000},
    "194A": {"nature": "Interest (other than securities)", "rate": 10.0, "threshold_annual": 40000},
    "194Q": {"nature": "Purchase of goods", "rate": 0.1, "threshold_annual": 5000000},
}

GST_RATES = [0, 5, 12, 18, 28]


class CATools(Toolkit):
    def __init__(self, **kwargs):
        super().__init__(
            name="ca_tools",
            tools=[
                self.gst_breakup,
                self.tds_compute,
                self.financial_ratios,
                self.compliance_calendar,
                self.reconcile_invoices,
            ],
            **kwargs,
        )

    def gst_breakup(self, amount: float, rate_pct: float, intra_state: bool = True, amount_is_inclusive: bool = False) -> str:
        """Split a GST amount into CGST+SGST (intra-state) or IGST (inter-state).

        Args:
            amount (float): Taxable value, or gross amount if amount_is_inclusive=True.
            rate_pct (float): GST rate in percent (0/5/12/18/28).
            intra_state (bool): True for CGST+SGST within a state; False for IGST inter-state.
            amount_is_inclusive (bool): If True, back-calculate the taxable value out of a GST-inclusive amount.

        Returns:
            str: JSON with taxable value, tax components and total.
        """
        try:
            if amount_is_inclusive:
                taxable = amount * 100.0 / (100.0 + rate_pct)
            else:
                taxable = float(amount)
            tax = taxable * rate_pct / 100.0
            out: Dict[str, object] = {"taxable_value": round(taxable, 2), "rate_pct": rate_pct}
            if intra_state:
                out["cgst"] = round(tax / 2, 2)
                out["sgst"] = round(tax / 2, 2)
            else:
                out["igst"] = round(tax, 2)
            out["total_tax"] = round(tax, 2)
            out["invoice_total"] = round(taxable + tax, 2)
            if rate_pct not in GST_RATES:
                out["note"] = "Non-standard GST rate - confirm the correct slab."
            return json.dumps(out)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def tds_compute(self, section: str, amount: float, payee_type: str = "other", sub_type: str = "") -> str:
        """Compute indicative TDS for a payment under a given section.

        Args:
            section (str): Section key, e.g. "194C", "194J", "194I_land_building".
            amount (float): Payment amount (before TDS).
            payee_type (str): "individual_huf" or "other" (matters for 194C).
            sub_type (str): For 194J use "professional" or "technical".

        Returns:
            str: JSON with the applicable rate, TDS amount and net payable. Verify against current law.
        """
        try:
            sec = TDS_SECTIONS.get(section)
            if not sec:
                return json.dumps({"error": f"Unknown section '{section}'. Known: {list(TDS_SECTIONS)}"})
            if section == "194C":
                rate = sec["rate_individual_huf"] if payee_type == "individual_huf" else sec["rate_other"]
            elif section == "194J":
                rate = sec["rate_technical"] if sub_type == "technical" else sec["rate_professional"]
            else:
                rate = sec.get("rate")
            tds = float(amount) * float(rate) / 100.0
            return json.dumps({
                "section": section,
                "nature": sec["nature"],
                "rate_pct": rate,
                "tds": round(tds, 2),
                "net_payable": round(float(amount) - tds, 2),
                "note": "Indicative only - confirm rate, thresholds, PAN/206AB status and current Finance Act.",
            })
        except Exception as e:
            return json.dumps({"error": str(e)})

    def financial_ratios(self, financials: Dict[str, float]) -> str:
        """Compute common financial-statement ratios from supplied figures.

        Args:
            financials (Dict[str,float]): Any of: current_assets, current_liabilities,
                inventory, total_debt, total_equity, ebit, interest, revenue, net_profit,
                total_assets, cogs.

        Returns:
            str: JSON of the ratios that could be computed (others omitted).
        """
        try:
            f = {k: float(v) for k, v in financials.items()}
            r: Dict[str, float] = {}

            def safe(n, d):
                return round(n / d, 3) if d else None

            if "current_assets" in f and "current_liabilities" in f:
                r["current_ratio"] = safe(f["current_assets"], f["current_liabilities"])
                if "inventory" in f:
                    r["quick_ratio"] = safe(f["current_assets"] - f["inventory"], f["current_liabilities"])
            if "total_debt" in f and "total_equity" in f:
                r["debt_equity"] = safe(f["total_debt"], f["total_equity"])
            if "ebit" in f and "interest" in f:
                r["interest_coverage"] = safe(f["ebit"], f["interest"])
            if "net_profit" in f and "revenue" in f:
                r["net_profit_margin_pct"] = safe(f["net_profit"] * 100, f["revenue"])
            if "net_profit" in f and "total_equity" in f:
                r["roe_pct"] = safe(f["net_profit"] * 100, f["total_equity"])
            if "revenue" in f and "total_assets" in f:
                r["asset_turnover"] = safe(f["revenue"], f["total_assets"])
            r = {k: v for k, v in r.items() if v is not None}
            if not r:
                return json.dumps({"error": "Not enough inputs. Provide e.g. current_assets & current_liabilities."})
            return json.dumps({"ratios": r})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def compliance_calendar(self, month: str = "") -> str:
        """Return the recurring Indian statutory due dates (indicative).

        Args:
            month (str): Optional month label for context (e.g. "April 2026").

        Returns:
            str: JSON list of common monthly/quarterly compliance due dates.
        """
        dues = [
            {"item": "TDS/TCS payment", "due": "7th of next month"},
            {"item": "GSTR-1 (monthly)", "due": "11th of next month"},
            {"item": "GSTR-3B (monthly)", "due": "20th of next month"},
            {"item": "PF & ESI payment", "due": "15th of next month"},
            {"item": "PT (where applicable)", "due": "varies by state"},
            {"item": "Advance tax instalments", "due": "15 Jun / 15 Sep / 15 Dec / 15 Mar"},
            {"item": "TDS return (24Q/26Q)", "due": "end of month following the quarter"},
        ]
        return json.dumps({"month": month, "due_dates": dues, "note": "Indicative - confirm against the latest GST/CBDT calendar and any extensions."})

    def reconcile_invoices(self, books: List[Dict[str, object]], portal: List[Dict[str, object]], key: str = "invoice_no") -> str:
        """Reconcile two invoice lists (e.g. purchase register vs GSTR-2B) by a key.

        Args:
            books (List[Dict]): Records from the books (each with `key` and "amount").
            portal (List[Dict]): Records from the GST portal/2B (each with `key` and "amount").
            key (str): Field name used to match records (default "invoice_no").

        Returns:
            str: JSON of matched, mismatched-amount, only-in-books and only-in-portal records.
        """
        try:
            b = {str(x.get(key)): float(x.get("amount", 0)) for x in books}
            p = {str(x.get(key)): float(x.get("amount", 0)) for x in portal}
            matched, mismatch = [], []
            for k in set(b) & set(p):
                if abs(b[k] - p[k]) < 0.01:
                    matched.append(k)
                else:
                    mismatch.append({key: k, "books": b[k], "portal": p[k], "diff": round(b[k] - p[k], 2)})
            return json.dumps({
                "matched": matched,
                "amount_mismatch": mismatch,
                "only_in_books": sorted(set(b) - set(p)),
                "only_in_portal": sorted(set(p) - set(b)),
            })
        except Exception as e:
            return json.dumps({"error": str(e)})


__all__ = ["CATools", "TDS_SECTIONS", "GST_RATES"]
