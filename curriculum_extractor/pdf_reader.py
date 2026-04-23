"""
pdf_reader.py — Extracts tables from PDF pages using pdfplumber.
"""

import pdfplumber
from typing import NamedTuple


class RawTable(NamedTuple):
    page_num: int
    headers: list[str | None]
    rows: list[list[str | None]]
    num_cols: int


def _all_empty(row: list[str | None]) -> bool:
    """Return True if every cell in the row is None or empty string."""
    return all(c is None or str(c).strip() == "" for c in row)


def _is_decorative_7col(table_rows: list[list[str | None]]) -> bool:
    """
    Detect single-row 7-column decorative tables (C2 page headers).
    These appear as a row of 7 cells where all cells are empty or None.
    """
    if len(table_rows) == 1 and len(table_rows[0]) == 7:
        return _all_empty(table_rows[0])
    return False


def extract_tables(pdf_path: str, start_page: int, end_page: int) -> list[RawTable]:
    """
    Extracts tables from pages [start_page, end_page) (0-indexed).

    Filters out:
    - Tables with < 3 rows
    - Tables where all cells in row[0] are empty or None
    - 7-column 1-row decorative tables (C2 page headers)
    - Tables where all cells are empty strings

    Returns headers (row[0]) + rows (row[1:]) separately.
    """
    result: list[RawTable] = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            actual_end = min(end_page, total_pages)

            for page_idx in range(start_page, actual_end):
                page = pdf.pages[page_idx]
                tables = page.extract_tables()

                if not tables:
                    continue

                for raw_table in tables:
                    if not raw_table:
                        continue

                    # Filter: less than 3 rows
                    if len(raw_table) < 3:
                        continue

                    # Filter: 7-column 1-row decorative table
                    if _is_decorative_7col(raw_table):
                        continue

                    # Filter: header row is all empty
                    if _all_empty(raw_table[0]):
                        continue

                    # Filter: entire table is empty
                    if all(_all_empty(row) for row in raw_table):
                        continue

                    headers = raw_table[0]
                    rows = raw_table[1:]
                    num_cols = len(headers)

                    result.append(RawTable(
                        page_num=page_idx,
                        headers=headers,
                        rows=rows,
                        num_cols=num_cols,
                    ))

    except Exception as e:
        print(f"[pdf_reader] Error extracting tables from {pdf_path} "
              f"pages {start_page}-{end_page}: {e}")

    return result
