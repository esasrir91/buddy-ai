"""CA importers & working-paper generators (India-first).

Deterministic helpers that turn raw client data into structured, reviewable
working papers:

- Bank statement (CSV) -> normalised, auto-classified transactions + summary.
- Tally voucher XML export (Day Book / ledger) -> transactions.
- Trial balance from ledger entries.
- GSTR-3B style tax summary from outward/inward supplies.
- TDS register from a payment list (uses CATools' section table).

All numbers are computed exactly; the agent must still tie them to source
documents and a CA must review/sign. File reads are confined to a base dir.
"""

from __future__ import annotations

import csv
import json
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

from buddy.tools import Toolkit
from buddy.verticals.ca.tools import TDS_SECTIONS

# Narration keyword -> accounting head (first match wins). Extend per client.
CLASSIFY_RULES: List[tuple] = [
    (("salary", "sal ", "payroll", "wages"), "Salaries & Wages"),
    (("rent",), "Rent"),
    (("gst", "igst", "cgst", "sgst", "tax", "tds"), "Duties & Taxes"),
    (("interest", "int.", "int "), "Interest"),
    (("emi", "loan", "repay"), "Loan / EMI"),
    (("electricity", "power", "bescom", "discom", "water"), "Utilities"),
    (("fuel", "petrol", "diesel", "hpcl", "iocl", "bpcl"), "Fuel & Conveyance"),
    (("charge", "fee", "commission", "chrg", "amc"), "Bank Charges"),
    (("purchase", "amazon", "flipkart", "vendor", "supplier"), "Purchases"),
    (("sales", "invoice", "receipt", "collection"), "Sales / Receipts"),
    (("upi", "imps", "neft", "rtgs", "transfer"), "Bank Transfer"),
]


def classify_narration(text: str) -> str:
    t = (text or "").lower()
    for keys, head in CLASSIFY_RULES:
        if any(k in t for k in keys):
            return head
    return "Unclassified / Suspense"


def _num(v) -> float:
    try:
        s = str(v).replace(",", "").replace("\u20b9", "").strip()
        return float(s) if s not in ("", "-", "nan") else 0.0
    except Exception:
        return 0.0


class CAImportTools(Toolkit):
    def __init__(self, base_path: Optional[str] = None, **kwargs):
        self.base_path = Path(base_path).resolve() if base_path else Path.cwd().resolve()
        super().__init__(
            name="ca_import_tools",
            tools=[
                self.import_bank_statement,
                self.import_tally_xml,
                self.trial_balance,
                self.gst3b_summary,
                self.tds_register,
            ],
            **kwargs,
        )

    def _safe(self, filename: str) -> Path:
        p = (self.base_path / filename).resolve()
        if self.base_path not in p.parents and p != self.base_path:
            raise ValueError("Path escapes the allowed base directory.")
        if not p.is_file():
            raise ValueError(f"File not found: {filename}")
        return p

    def import_bank_statement(
        self,
        filename: str,
        date_col: str = "Date",
        narration_col: str = "Narration",
        debit_col: str = "Debit",
        credit_col: str = "Credit",
        max_rows: int = 500,
    ) -> str:
        """Parse a bank-statement CSV into classified transactions + a head-wise summary.

        Args:
            filename (str): CSV path relative to the workspace.
            date_col (str): Column header for the value/transaction date.
            narration_col (str): Column header for the description/narration.
            debit_col (str): Column header for money out (debit).
            credit_col (str): Column header for money in (credit).
            max_rows (int): Max rows to return.

        Returns:
            str: JSON with transactions (date, narration, debit, credit, head) and
                 totals by head, plus total debit/credit.
        """
        try:
            path = self._safe(filename)
            txns: List[Dict[str, object]] = []
            by_head_debit: Dict[str, float] = defaultdict(float)
            by_head_credit: Dict[str, float] = defaultdict(float)
            tot_d = tot_c = 0.0
            with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
                reader = csv.DictReader(f)
                for i, row in enumerate(reader):
                    if i >= max_rows:
                        break
                    narration = row.get(narration_col, "") or ""
                    d = _num(row.get(debit_col))
                    c = _num(row.get(credit_col))
                    head = classify_narration(narration)
                    by_head_debit[head] += d
                    by_head_credit[head] += c
                    tot_d += d
                    tot_c += c
                    txns.append({
                        "date": row.get(date_col, ""),
                        "narration": narration.strip()[:120],
                        "debit": round(d, 2),
                        "credit": round(c, 2),
                        "head": head,
                    })
            summary = {h: {"debit": round(by_head_debit[h], 2), "credit": round(by_head_credit.get(h, 0), 2)}
                       for h in set(by_head_debit) | set(by_head_credit)}
            return json.dumps({
                "count": len(txns),
                "transactions": txns,
                "by_head": summary,
                "total_debit": round(tot_d, 2),
                "total_credit": round(tot_c, 2),
                "note": "Auto-classification is heuristic - review and reassign heads before posting.",
            })
        except Exception as e:
            return json.dumps({"error": str(e)})

    def import_tally_xml(self, filename: str, max_rows: int = 1000) -> str:
        """Parse a Tally voucher XML export (Day Book / ledger) into transactions.

        Args:
            filename (str): Tally XML export path relative to the workspace.
            max_rows (int): Max vouchers to return.

        Returns:
            str: JSON with vouchers (date, type, party, amount) and a count.
        """
        try:
            path = self._safe(filename)
            text = path.read_text(encoding="utf-8", errors="ignore")
            # Tally XML can be malformed for strict parsers; recover where possible.
            try:
                root = ET.fromstring(text)
            except ET.ParseError:
                root = ET.fromstring("<ROOT>" + text + "</ROOT>")
            vouchers: List[Dict[str, object]] = []
            for v in root.iter("VOUCHER"):
                if len(vouchers) >= max_rows:
                    break
                def _t(tag):
                    el = v.find(tag)
                    return el.text.strip() if el is not None and el.text else ""
                amount = 0.0
                amt_el = v.find(".//AMOUNT")
                if amt_el is not None and amt_el.text:
                    amount = _num(amt_el.text)
                vouchers.append({
                    "date": _t("DATE"),
                    "voucher_type": v.get("VCHTYPE", "") or _t("VOUCHERTYPENAME"),
                    "party": _t("PARTYLEDGERNAME") or _t("PARTYNAME"),
                    "narration": _t("NARRATION")[:120],
                    "amount": round(abs(amount), 2),
                })
            return json.dumps({"count": len(vouchers), "vouchers": vouchers,
                               "note": "Parsed from Tally export - verify against the books."})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def trial_balance(self, entries: List[Dict[str, object]]) -> str:
        """Build a trial balance from ledger entries.

        Args:
            entries (List[Dict]): Each {"ledger", "debit", "credit"}.

        Returns:
            str: JSON with per-ledger net balances and the Dr/Cr totals (should match).
        """
        try:
            ledg_d: Dict[str, float] = defaultdict(float)
            ledg_c: Dict[str, float] = defaultdict(float)
            for e in entries:
                name = str(e.get("ledger", "?"))
                ledg_d[name] += _num(e.get("debit"))
                ledg_c[name] += _num(e.get("credit"))
            rows = []
            tot_d = tot_c = 0.0
            for name in sorted(set(ledg_d) | set(ledg_c)):
                net = ledg_d[name] - ledg_c[name]
                dr = round(net, 2) if net > 0 else 0.0
                cr = round(-net, 2) if net < 0 else 0.0
                tot_d += dr
                tot_c += cr
                rows.append({"ledger": name, "debit": dr, "credit": cr})
            return json.dumps({
                "trial_balance": rows,
                "total_debit": round(tot_d, 2),
                "total_credit": round(tot_c, 2),
                "balanced": abs(tot_d - tot_c) < 0.01,
            })
        except Exception as e:
            return json.dumps({"error": str(e)})

    def gst3b_summary(self, outward: List[Dict[str, object]], inward: List[Dict[str, object]]) -> str:
        """Summarise output tax, ITC and net GST payable (GSTR-3B style).

        Args:
            outward (List[Dict]): Sales rows {"taxable","cgst","sgst","igst"}.
            inward (List[Dict]): Purchase rows with eligible ITC {"cgst","sgst","igst"}.

        Returns:
            str: JSON with output tax, ITC, and net payable by head.
        """
        try:
            def agg(rows, *keys):
                return {k: round(sum(_num(r.get(k)) for r in rows), 2) for k in keys}
            out = agg(outward, "taxable", "cgst", "sgst", "igst")
            itc = agg(inward, "cgst", "sgst", "igst")
            net = {k: round(out.get(k, 0) - itc.get(k, 0), 2) for k in ("cgst", "sgst", "igst")}
            net_total = round(sum(max(0, v) for v in net.values()), 2)
            return json.dumps({
                "output_tax": out,
                "input_tax_credit": itc,
                "net_payable_by_head": net,
                "net_cash_payable": net_total,
                "note": "Indicative 3B working - confirm ITC eligibility and reconcile with GSTR-2B.",
            })
        except Exception as e:
            return json.dumps({"error": str(e)})

    def tds_register(self, payments: List[Dict[str, object]]) -> str:
        """Build a TDS register from a list of payments.

        Args:
            payments (List[Dict]): Each {"party","section","amount","payee_type"?,"sub_type"?}.

        Returns:
            str: JSON with per-payment TDS and the total TDS to deposit.
        """
        try:
            rows, total = [], 0.0
            for p in payments:
                section = str(p.get("section", ""))
                sec = TDS_SECTIONS.get(section)
                amount = _num(p.get("amount"))
                if not sec:
                    rows.append({"party": p.get("party"), "section": section, "error": "unknown section"})
                    continue
                if section == "194C":
                    rate = sec["rate_individual_huf"] if p.get("payee_type") == "individual_huf" else sec["rate_other"]
                elif section == "194J":
                    rate = sec["rate_technical"] if p.get("sub_type") == "technical" else sec["rate_professional"]
                else:
                    rate = sec.get("rate")
                tds = round(amount * float(rate) / 100.0, 2)
                total += tds
                rows.append({"party": p.get("party"), "section": section, "amount": round(amount, 2), "rate_pct": rate, "tds": tds})
            return json.dumps({"register": rows, "total_tds": round(total, 2),
                               "note": "Verify rates/thresholds and PAN/206AB status before deposit."})
        except Exception as e:
            return json.dumps({"error": str(e)})


__all__ = ["CAImportTools", "classify_narration", "CLASSIFY_RULES"]
