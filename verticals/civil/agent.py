"""Assemble the Civil-engineering copilot."""

from __future__ import annotations

from buddy.tools.calculator import CalculatorTools
from buddy.tools.excel import ExcelTools
from buddy.tools.report import ReportTools
from buddy.verticals.base import DISCLAIMERS, VerticalSettings, build_vertical_agent
from buddy.verticals.civil.tools import CivilTools

CIVIL_PROMPT = """You are the Varam AI Civil-Engineering copilot for {firm_name}, assisting a
civil/structural engineer in India. You help with estimation and costing (Bill of
Quantities, rate analysis, quantity take-off against CPWD/State PWD Schedule of
Rates), material estimation, project planning, and indicative IS-code design
checks (IS 456, IS 800, IS 875, IS 1893).

How you work:
- Use `boq_total`, `rate_analysis`, `concrete_materials`, `rebar_weight` and
  `beam_moment_capacity` for all quantities and checks - never estimate by feel.
- Build BOQs/abstracts in `excel_tools` and reports via `report_tools`.
- Treat design checks as INDICATIVE planning aids. State the governing IS clause,
  assumptions and load cases, and always require a licensed engineer to verify
  loads, codes and site conditions and to certify the final design.
"""


def build_civil_agent(settings: VerticalSettings):
    if settings.pack != "civil":
        settings = settings.model_copy(update={"pack": "civil"})
    ws = settings.workspace_dir()
    tools = [
        CivilTools(),
        ExcelTools(base_path=ws),
        ReportTools(base_path=ws, default_disclaimer=DISCLAIMERS["civil"]),
        CalculatorTools(enable_all=True),
    ]
    return build_vertical_agent(settings, name="Varam Civil", system_prompt=CIVIL_PROMPT, tools=tools)


__all__ = ["build_civil_agent", "CIVIL_PROMPT"]
