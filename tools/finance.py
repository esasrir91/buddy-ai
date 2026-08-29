"""FinanceTools - deterministic financial mathematics for the agent.

These are exact, audited calculations (NPV, IRR, DCF, WACC, CAPM, loan EMI,
depreciation, CAGR) implemented in pure Python so figures are *computed*, never
guessed by the language model. Every method returns a JSON string with the
inputs echoed back, so results are traceable and reviewable.

Shared across the CA, Valuation and Civil verticals.
"""

from __future__ import annotations

import json
from typing import List, Optional

from buddy.tools import Toolkit


def _npv(rate: float, cashflows: List[float]) -> float:
    return sum(cf / ((1.0 + rate) ** t) for t, cf in enumerate(cashflows))


class FinanceTools(Toolkit):
    def __init__(self, **kwargs):
        super().__init__(
            name="finance_tools",
            tools=[
                self.npv,
                self.irr,
                self.dcf_valuation,
                self.wacc,
                self.capm_cost_of_equity,
                self.loan_emi,
                self.depreciation_schedule,
                self.cagr,
            ],
            **kwargs,
        )

    def npv(self, rate: float, cashflows: List[float]) -> str:
        """Net Present Value of a series of cashflows.

        Args:
            rate (float): Discount rate per period (e.g. 0.12 for 12%).
            cashflows (List[float]): Cashflows by period; index 0 is today (t=0).

        Returns:
            str: JSON with the NPV.
        """
        try:
            value = _npv(rate, [float(c) for c in cashflows])
            return json.dumps({"npv": round(value, 2), "rate": rate, "periods": len(cashflows)})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def irr(self, cashflows: List[float], guess: float = 0.1) -> str:
        """Internal Rate of Return via bisection (robust, no numpy needed).

        Args:
            cashflows (List[float]): Cashflows by period; index 0 (t=0) is usually negative (the investment).
            guess (float): Unused starting hint, kept for API familiarity.

        Returns:
            str: JSON with the IRR as a decimal (e.g. 0.184 = 18.4%), or an error.
        """
        try:
            cf = [float(c) for c in cashflows]
            lo, hi = -0.9999, 10.0
            f_lo, f_hi = _npv(lo, cf), _npv(hi, cf)
            if f_lo * f_hi > 0:
                return json.dumps({"error": "IRR not bracketed; check that cashflows change sign."})
            for _ in range(200):
                mid = (lo + hi) / 2.0
                f_mid = _npv(mid, cf)
                if abs(f_mid) < 1e-7:
                    break
                if f_lo * f_mid < 0:
                    hi, f_hi = mid, f_mid
                else:
                    lo, f_lo = mid, f_mid
            return json.dumps({"irr": round(mid, 6), "irr_pct": round(mid * 100, 3)})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def dcf_valuation(
        self,
        free_cash_flows: List[float],
        discount_rate: float,
        terminal_growth: float = 0.04,
        net_debt: float = 0.0,
        shares_outstanding: Optional[float] = None,
    ) -> str:
        """Discounted Cash Flow enterprise & equity value (Gordon terminal value).

        Args:
            free_cash_flows (List[float]): Projected FCFs for years 1..N.
            discount_rate (float): WACC as a decimal (e.g. 0.13).
            terminal_growth (float): Perpetual growth rate g (must be < discount_rate).
            net_debt (float): Debt minus cash; subtracted to get equity value.
            shares_outstanding (float): If given, also returns per-share value.

        Returns:
            str: JSON with PV of explicit FCFs, terminal value, enterprise & equity value.
        """
        try:
            fcf = [float(c) for c in free_cash_flows]
            if discount_rate <= terminal_growth:
                return json.dumps({"error": "discount_rate must exceed terminal_growth."})
            pv_explicit = sum(cf / ((1 + discount_rate) ** (t + 1)) for t, cf in enumerate(fcf))
            tv = (fcf[-1] * (1 + terminal_growth)) / (discount_rate - terminal_growth)
            pv_tv = tv / ((1 + discount_rate) ** len(fcf))
            ev = pv_explicit + pv_tv
            equity = ev - net_debt
            out = {
                "pv_explicit_fcf": round(pv_explicit, 2),
                "terminal_value": round(tv, 2),
                "pv_terminal_value": round(pv_tv, 2),
                "enterprise_value": round(ev, 2),
                "equity_value": round(equity, 2),
                "assumptions": {"discount_rate": discount_rate, "terminal_growth": terminal_growth, "net_debt": net_debt},
            }
            if shares_outstanding:
                out["value_per_share"] = round(equity / float(shares_outstanding), 2)
            return json.dumps(out)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def wacc(
        self,
        equity_value: float,
        debt_value: float,
        cost_of_equity: float,
        cost_of_debt: float,
        tax_rate: float = 0.25,
    ) -> str:
        """Weighted Average Cost of Capital.

        Args:
            equity_value (float): Market value of equity.
            debt_value (float): Market value of debt.
            cost_of_equity (float): Ke as a decimal.
            cost_of_debt (float): Kd as a decimal (pre-tax).
            tax_rate (float): Corporate tax rate as a decimal.

        Returns:
            str: JSON with the WACC.
        """
        try:
            v = equity_value + debt_value
            if v == 0:
                return json.dumps({"error": "equity_value + debt_value must be > 0"})
            w = (equity_value / v) * cost_of_equity + (debt_value / v) * cost_of_debt * (1 - tax_rate)
            return json.dumps({"wacc": round(w, 6), "wacc_pct": round(w * 100, 3)})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def capm_cost_of_equity(self, risk_free: float, beta: float, equity_risk_premium: float) -> str:
        """Cost of equity via CAPM: Rf + beta * ERP.

        Args:
            risk_free (float): Risk-free rate as a decimal (e.g. 0.07 for an Indian 10Y G-Sec).
            beta (float): Levered beta of the company.
            equity_risk_premium (float): Market equity risk premium as a decimal.

        Returns:
            str: JSON with the cost of equity.
        """
        try:
            ke = risk_free + beta * equity_risk_premium
            return json.dumps({"cost_of_equity": round(ke, 6), "cost_of_equity_pct": round(ke * 100, 3)})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def loan_emi(self, principal: float, annual_rate_pct: float, tenure_months: int) -> str:
        """Equated Monthly Instalment for a reducing-balance loan.

        Args:
            principal (float): Loan principal.
            annual_rate_pct (float): Annual interest rate in percent (e.g. 9.5).
            tenure_months (int): Number of monthly instalments.

        Returns:
            str: JSON with EMI, total payment and total interest.
        """
        try:
            r = (annual_rate_pct / 100.0) / 12.0
            n = int(tenure_months)
            if r == 0:
                emi = principal / n
            else:
                emi = principal * r * (1 + r) ** n / ((1 + r) ** n - 1)
            total = emi * n
            return json.dumps({
                "emi": round(emi, 2),
                "total_payment": round(total, 2),
                "total_interest": round(total - principal, 2),
            })
        except Exception as e:
            return json.dumps({"error": str(e)})

    def depreciation_schedule(
        self,
        cost: float,
        rate_pct: float,
        years: int,
        method: str = "wdv",
        salvage: float = 0.0,
    ) -> str:
        """Year-wise depreciation schedule (India: WDV is common under the Income-tax Act; SLM under Companies Act).

        Args:
            cost (float): Asset cost (or opening WDV).
            rate_pct (float): Depreciation rate in percent.
            years (int): Number of years to project.
            method (str): "wdv" (written-down value / reducing balance) or "slm" (straight-line).
            salvage (float): Residual value (used by SLM).

        Returns:
            str: JSON with a per-year schedule of opening, depreciation and closing values.
        """
        try:
            rate = rate_pct / 100.0
            rows = []
            if method.lower() == "slm":
                annual = (cost - salvage) / years
                book = cost
                for y in range(1, years + 1):
                    dep = min(annual, book - salvage)
                    rows.append({"year": y, "opening": round(book, 2), "depreciation": round(dep, 2), "closing": round(book - dep, 2)})
                    book -= dep
            else:  # WDV
                book = cost
                for y in range(1, years + 1):
                    dep = book * rate
                    rows.append({"year": y, "opening": round(book, 2), "depreciation": round(dep, 2), "closing": round(book - dep, 2)})
                    book -= dep
            return json.dumps({"method": method.lower(), "rate_pct": rate_pct, "schedule": rows})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def cagr(self, begin_value: float, end_value: float, years: float) -> str:
        """Compound Annual Growth Rate.

        Args:
            begin_value (float): Starting value.
            end_value (float): Ending value.
            years (float): Number of years.

        Returns:
            str: JSON with the CAGR as a decimal and percent.
        """
        try:
            if begin_value <= 0 or years <= 0:
                return json.dumps({"error": "begin_value and years must be > 0"})
            g = (end_value / begin_value) ** (1.0 / years) - 1.0
            return json.dumps({"cagr": round(g, 6), "cagr_pct": round(g * 100, 3)})
        except Exception as e:
            return json.dumps({"error": str(e)})


__all__ = ["FinanceTools"]
