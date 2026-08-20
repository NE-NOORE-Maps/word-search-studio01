"""Shared Excel writer for Canva Bulk Create image fields.

Canva reads images from floating pictures anchored to spreadsheet cells.  A CSV
that merely contains a local PNG filename cannot populate an image frame.
"""
from __future__ import annotations

import os
from collections.abc import Iterable, Sequence
from typing import Any


def write_bulk_excel(
    out_path: str,
    rows: Sequence[dict[str, Any]],
    text_columns: Sequence[str],
    image_columns: Sequence[str],
    *,
    max_rows: int = 0,
) -> list[str]:
    """Create one or more Canva-compatible workbooks with embedded images."""
    import xlsxwriter

    def write_part(path: str, part_rows: Iterable[dict[str, Any]]) -> str:
        workbook = xlsxwriter.Workbook(path)
        sheet = workbook.add_worksheet("Bulk Create")
        headers = [*text_columns, *image_columns]
        for column, header in enumerate(headers):
            sheet.write(0, column, header)
        for row_index, row in enumerate(part_rows, start=1):
            for column, name in enumerate(text_columns):
                sheet.write(row_index, column, row.get(name, ""))
            sheet.set_row(row_index, 150)
            for offset, name in enumerate(image_columns):
                column = len(text_columns) + offset
                image_path = row.get(name)
                if image_path and os.path.isfile(image_path):
                    sheet.insert_image(row_index, column, image_path, {
                        "x_scale": 0.09,
                        "y_scale": 0.09,
                        "positioning": 1,
                        "x_offset": 5,
                        "y_offset": 5,
                    })
                else:
                    sheet.write(row_index, column, "No image")
        for column in range(len(text_columns), len(headers)):
            sheet.set_column(column, column, 30)
        workbook.close()
        return path

    if max_rows <= 0 or len(rows) <= max_rows:
        return [write_part(out_path, rows)]

    base, ext = os.path.splitext(out_path)
    return [
        write_part(f"{base}_part{part}{ext}", rows[start:start + max_rows])
        for part, start in enumerate(range(0, len(rows), max_rows), start=1)
    ]
