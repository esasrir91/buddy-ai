"""ExcelTools - read and write .xlsx workbooks for the agent.

Spreadsheets are the lingua franca of accountants, valuers and estimators, so
this toolkit lets an agent inspect sheets, read ranges/tables, and write results
back to an Excel file. Operations are confined to a base directory.

Requires ``openpyxl`` (``pip install openpyxl``). Reading also works via
``pandas`` if installed. Methods degrade gracefully with a clear message when a
dependency is missing rather than raising.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from buddy.tools import Toolkit


class ExcelTools(Toolkit):
    def __init__(self, base_path: Optional[str] = None, **kwargs):
        self.base_path = Path(base_path).resolve() if base_path else Path.cwd().resolve()
        super().__init__(
            name="excel_tools",
            tools=[
                self.list_sheets,
                self.read_sheet,
                self.write_sheet,
                self.append_rows,
            ],
            **kwargs,
        )

    def _safe(self, filename: str) -> Path:
        p = (self.base_path / filename).resolve()
        if self.base_path not in p.parents and p != self.base_path:
            raise ValueError("Path escapes the allowed base directory.")
        return p

    def list_sheets(self, filename: str) -> str:
        """List the sheet (tab) names in an Excel workbook.

        Args:
            filename (str): Workbook path relative to the base directory.

        Returns:
            str: JSON with the list of sheet names.
        """
        try:
            import openpyxl  # type: ignore
        except Exception:
            return json.dumps({"error": "openpyxl not installed. Run: pip install openpyxl"})
        try:
            wb = openpyxl.load_workbook(self._safe(filename), read_only=True, data_only=True)
            return json.dumps({"file": filename, "sheets": wb.sheetnames})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def read_sheet(self, filename: str, sheet: Optional[str] = None, max_rows: int = 200) -> str:
        """Read a worksheet as rows of values (first row treated as header).

        Args:
            filename (str): Workbook path relative to the base directory.
            sheet (str): Sheet name; defaults to the active/first sheet.
            max_rows (int): Maximum data rows to return (guards against huge files).

        Returns:
            str: JSON with headers and rows.
        """
        try:
            import openpyxl  # type: ignore
        except Exception:
            return json.dumps({"error": "openpyxl not installed. Run: pip install openpyxl"})
        try:
            wb = openpyxl.load_workbook(self._safe(filename), read_only=True, data_only=True)
            ws = wb[sheet] if sheet else wb.active
            rows = list(ws.iter_rows(values_only=True))
            if not rows:
                return json.dumps({"file": filename, "sheet": ws.title, "headers": [], "rows": []})
            headers = [str(h) if h is not None else f"col{i}" for i, h in enumerate(rows[0])]
            data = [list(r) for r in rows[1 : 1 + max_rows]]
            return json.dumps({"file": filename, "sheet": ws.title, "headers": headers, "rows": data, "truncated": len(rows) - 1 > max_rows})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def write_sheet(self, filename: str, headers: List[str], rows: List[List[Any]], sheet: str = "Sheet1") -> str:
        """Create (or overwrite) a workbook with a single sheet of tabular data.

        Args:
            filename (str): Output workbook path relative to the base directory.
            headers (List[str]): Column headers.
            rows (List[List[Any]]): Data rows (each a list of cell values).
            sheet (str): Sheet/tab name.

        Returns:
            str: JSON confirming the saved file and row count.
        """
        try:
            import openpyxl  # type: ignore
        except Exception:
            return json.dumps({"error": "openpyxl not installed. Run: pip install openpyxl"})
        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = sheet
            ws.append(list(headers))
            for r in rows:
                ws.append(list(r))
            out = self._safe(filename)
            out.parent.mkdir(parents=True, exist_ok=True)
            wb.save(out)
            return json.dumps({"saved": str(out), "sheet": sheet, "rows_written": len(rows)})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def append_rows(self, filename: str, rows: List[List[Any]], sheet: Optional[str] = None) -> str:
        """Append rows to an existing workbook/sheet (creates the file if missing).

        Args:
            filename (str): Workbook path relative to the base directory.
            rows (List[List[Any]]): Rows to append.
            sheet (str): Sheet name; defaults to the active sheet.

        Returns:
            str: JSON confirming rows appended.
        """
        try:
            import openpyxl  # type: ignore
        except Exception:
            return json.dumps({"error": "openpyxl not installed. Run: pip install openpyxl"})
        try:
            path = self._safe(filename)
            if path.exists():
                wb = openpyxl.load_workbook(path)
                ws = wb[sheet] if sheet and sheet in wb.sheetnames else wb.active
            else:
                wb = openpyxl.Workbook()
                ws = wb.active
                if sheet:
                    ws.title = sheet
            for r in rows:
                ws.append(list(r))
            path.parent.mkdir(parents=True, exist_ok=True)
            wb.save(path)
            return json.dumps({"saved": str(path), "rows_appended": len(rows)})
        except Exception as e:
            return json.dumps({"error": str(e)})


__all__ = ["ExcelTools"]
