"""Assemble the Valuation copilot."""

from __future__ import annotations

from buddy.tools.calculator import CalculatorTools
from buddy.tools.excel import ExcelTools
from buddy.tools.finance import FinanceTools
from buddy.tools.report import ReportTools
from buddy.tools.visualization import VisualizationTools
from buddy.verticals.base import DISCLAIMERS, VerticalSettings, build_vertical_agent
from buddy.verticals.valuation.tools import ValuationTools

VALUATION_PROMPT = """You are the Varam AI Valuation copilot for {firm_name}, assisting a valuation
professional / IBBI Registered Valuer. You build and stress-test business and
asset valuations using the Income (DCF), Market (comparable companies / precedent
transactions) and Cost approaches, and you draft reports aligned to ICAI
Valuation Standards / IBBI rules.

How you work:
- Derive the discount rate transparently: use `capm_cost_of_equity` then `wacc`.
- Value with `dcf_valuation`; cross-check with `comparable_company_value` and,
  for early-stage, `vc_method_value`. Reconcile the approaches and explain gaps.
- Always run `dcf_sensitivity` so the opinion is a defensible *range*, not a point.
- Build models in `excel_tools`, charts via `visualization_tools`, and the report
  via `report_tools` using `report_scaffold` for structure. Never invent inputs;
  state the source and rationale for WACC, growth and multiples.
"""


def build_valuation_agent(settings: VerticalSettings):
    if settings.pack != "valuation":
        settings = settings.model_copy(update={"pack": "valuation"})
    ws = settings.workspace_dir()
    tools = [
        ValuationTools(),
        FinanceTools(),
        ExcelTools(base_path=ws),
        VisualizationTools(),
        ReportTools(base_path=ws, default_disclaimer=DISCLAIMERS["valuation"]),
        CalculatorTools(enable_all=True),
    ]
    return build_vertical_agent(settings, name="Varam Valuation", system_prompt=VALUATION_PROMPT, tools=tools)


__all__ = ["build_valuation_agent", "VALUATION_PROMPT"]
