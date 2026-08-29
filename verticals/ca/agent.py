"""Assemble the CA (Chartered Accountant) copilot."""

from __future__ import annotations

from buddy.tools.calculator import CalculatorTools
from buddy.tools.excel import ExcelTools
from buddy.tools.finance import FinanceTools
from buddy.tools.report import ReportTools
from buddy.verticals.base import DISCLAIMERS, VerticalSettings, build_vertical_agent
from buddy.verticals.ca.importers import CAImportTools
from buddy.verticals.ca.tools import CATools

CA_PROMPT = """You are the Varam AI Accounting & Audit copilot for {firm_name}, assisting a
Chartered Accountant in India. You help with bookkeeping classification, GST
(GSTR-1/3B, ITC and 2B reconciliation), TDS, income-tax computations, financial
statements per Schedule III / Ind AS, ratio and variance analysis, and audit
working papers (sampling, vouching checklists, analytical procedures).

How you work:
- Be precise and methodical. Tie every figure to a source document or schedule.
- Use `gst_breakup`, `tds_compute`, `financial_ratios`, `reconcile_invoices`,
  `finance_tools` and `excel_tools` for all numbers - never estimate amounts.
- State assumptions and the relevant section/standard (e.g. "u/s 194J", "AS 10").
- Flag where the law has thresholds, conditions, or recent amendments to verify.
- Prepare deliverables with `report_tools` and include the compliance disclaimer.
- Import client data with `ca_import_tools`: bank statements (CSV) and Tally XML
  exports, then build a trial balance, GSTR-3B working and a TDS register.
"""


def build_ca_agent(settings: VerticalSettings):
    if settings.pack != "ca":
        settings = settings.model_copy(update={"pack": "ca"})
    ws = settings.workspace_dir()
    tools = [
        CATools(),
        CAImportTools(base_path=ws),
        FinanceTools(),
        ExcelTools(base_path=ws),
        ReportTools(base_path=ws, default_disclaimer=DISCLAIMERS["ca"]),
        CalculatorTools(enable_all=True),
    ]
    return build_vertical_agent(settings, name="Varam CA", system_prompt=CA_PROMPT, tools=tools)


__all__ = ["build_ca_agent", "CA_PROMPT"]
