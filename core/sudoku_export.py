"""Batch export builder for Sudoku workbooks, images, PDF book, and ZIP bundles.
"""
from __future__ import annotations

import os
import zipfile
from pathlib import Path
from typing import Any, List, Optional, Tuple

import xlsxwriter
from core.canva_bulk import get_canva_instructions_text, package_canva_batches_zip, write_bulk_excel
from core.sudoku_raster import render_sudoku_image, render_sudoku_solution_image
from core.sudoku_pdf import build_sudoku_pdf
from engine.sudoku import SudokuPuzzle


def build_sudoku_workbooks(
    puzzles: List[SudokuPuzzle],
    out_dir: str,
    puzzles_per_page: int = 1,
    solutions_per_page: int = 6,
    style: Any = None,
    trim_choice: str = "8.5 x 11 inches (Letter)",
    include_instructions: bool = True,
    include_solution_in_same_excel: bool = True,
    date_config: Optional[dict] = None,
    progress_bar: Optional[Any] = None,
    canva_batch_size: int = 100,
) -> Tuple[str, Optional[str], str, bytes]:
    """Render all 300 DPI Sudoku images, create Canva Excel, Solutions Excel, KDP PDF, and ZIP bundle.

    If include_solution_in_same_excel is True, the solution images are embedded directly in the same
    Excel file alongside the puzzle image for 1-click Canva Bulk Create mapping.
    """
    os.makedirs(out_dir, exist_ok=True)
    img_dir = os.path.join(out_dir, "images")
    os.makedirs(img_dir, exist_ok=True)

    grid_paths: List[str] = []
    sol_paths: List[str] = []
    cal_paths: List[str] = []
    cal_imgs: List[Any] = []
    date_strings: List[str] = []
    total = len(puzzles)

    date_enabled = bool(date_config and date_config.get("enabled"))
    cal_mode = "text"
    if date_enabled:
        from core.calendar_builder import get_puzzle_date_info, render_mini_month_calendar
        s_date = date_config.get("start_date")
        if not s_date:
            import datetime
            s_date = datetime.date(2026, 1, 1)
        prog = date_config.get("progression", "daily")
        f_choice = date_config.get("format_choice", "27-September")
        cal_mode = date_config.get("mode", "text")
        theme = date_config.get("calendar_theme", "Modern Emerald")
        sunday_start = date_config.get("first_day_sunday", True)
        border_outline = date_config.get("show_card_border", True)
        cal_show_yr = date_config.get("show_year", True)

        for i in range(total):
            info = get_puzzle_date_info(i, s_date, progression=prog, format_choice=f_choice)
            date_strings.append(info["date_str"])
            if cal_mode == "calendar_image":
                cal_img = render_mini_month_calendar(
                    year=info["year"],
                    month=info["month"],
                    highlight_day=info["highlight_day"],
                    theme=theme,
                    first_day_sunday=sunday_start,
                    show_card_border=border_outline,
                    show_year=cal_show_yr,
                )
                cp = os.path.join(img_dir, f"page_{i+1:03d}_calendar.png")
                cal_img.save(cp)
                cal_paths.append(cp)
                cal_imgs.append(cal_img)

    # 1. Render all 300 DPI PNG images
    for i, puzzle in enumerate(puzzles, 1):
        gp = os.path.join(img_dir, f"page_{i:03d}_grid.png")
        sp = os.path.join(img_dir, f"page_{i:03d}_solution.png")
        d_txt = date_strings[i - 1] if date_enabled else None

        render_sudoku_image(puzzle, style, cell_mm=12.0, dpi=300, solution=False, date_text=d_txt).save(gp)
        render_sudoku_solution_image(puzzle, style, cell_mm=12.0, dpi=300).save(sp)

        grid_paths.append(gp)
        sol_paths.append(sp)

        if progress_bar:
            progress_bar.progress(int((i / total) * 45), text=f"Rendering high-res images: {i} of {total}...")

    # 2. Build Canva Bulk Create Workbook
    if progress_bar:
        progress_bar.progress(50, text="Generating Canva Bulk Create workbook...")

    if puzzles_per_page <= 1:
        text_columns = ["page", "puzzle_num", "title"]
        if date_enabled:
            text_columns.append("date")
        text_columns.extend(["difficulty", "clues_count"])
        if puzzles and puzzles[0].wordoku_word:
            text_columns.append("wordoku_word")

        image_columns = ["grid_image"]
        if date_enabled and cal_mode == "calendar_image":
            image_columns.append("calendar_image")
        if include_solution_in_same_excel:
            image_columns.append("solution_image")

        rows = []
        for i, puzzle in enumerate(puzzles, 1):
            row = {
                "page": i,
                "puzzle_num": puzzle.puzzle_id,
                "title": puzzle.title,
                "difficulty": puzzle.difficulty_label,
                "clues_count": puzzle.clues_count,
                "grid_image": grid_paths[i - 1],
            }
            if date_enabled:
                row["date"] = date_strings[i - 1]
            if date_enabled and cal_mode == "calendar_image":
                row["calendar_image"] = cal_paths[i - 1]
            if include_solution_in_same_excel:
                row["solution_image"] = sol_paths[i - 1]
            if puzzle.wordoku_word:
                row["wordoku_word"] = puzzle.wordoku_word
            rows.append(row)
    else:
        text_columns = ["page", "puzzle_range"]
        image_columns = []
        for k in range(1, puzzles_per_page + 1):
            col_group = [f"title_{k}"]
            if date_enabled:
                col_group.append(f"date_{k}")
            col_group.extend([f"difficulty_{k}", f"clues_{k}"])
            text_columns.extend(col_group)

            image_columns.append(f"grid_image_{k}")
            if date_enabled and cal_mode == "calendar_image":
                image_columns.append(f"calendar_image_{k}")
            if include_solution_in_same_excel:
                image_columns.append(f"solution_image_{k}")

        rows = []
        page_idx = 1
        for start_idx in range(0, total, puzzles_per_page):
            chunk = puzzles[start_idx : start_idx + puzzles_per_page]
            p_nums = [str(p.puzzle_id) for p in chunk]
            p_range_str = f"Puzzles {p_nums[0]}-{p_nums[-1]}" if len(p_nums) > 1 else f"Puzzle {p_nums[0]}"
            row = {
                "page": page_idx,
                "puzzle_range": p_range_str,
            }
            for k in range(1, puzzles_per_page + 1):
                c_idx = start_idx + k - 1
                if c_idx < total:
                    p = puzzles[c_idx]
                    row[f"title_{k}"] = p.title
                    if date_enabled:
                        row[f"date_{k}"] = date_strings[c_idx]
                    row[f"difficulty_{k}"] = p.difficulty_label
                    row[f"clues_{k}"] = p.clues_count
                    row[f"grid_image_{k}"] = grid_paths[c_idx]
                    if date_enabled and cal_mode == "calendar_image":
                        row[f"calendar_image_{k}"] = cal_paths[c_idx]
                    if include_solution_in_same_excel:
                        row[f"solution_image_{k}"] = sol_paths[c_idx]
                else:
                    row[f"title_{k}"] = ""
                    if date_enabled:
                        row[f"date_{k}"] = ""
                    row[f"difficulty_{k}"] = ""
                    row[f"clues_{k}"] = ""
                    row[f"grid_image_{k}"] = ""
                    if date_enabled and cal_mode == "calendar_image":
                        row[f"calendar_image_{k}"] = ""
                    if include_solution_in_same_excel:
                        row[f"solution_image_{k}"] = ""
            rows.append(row)
            page_idx += 1

    canva_path = os.path.join(out_dir, "sudoku_canva_bulk.xlsx")
    canva_files = write_bulk_excel(canva_path, rows, text_columns, image_columns, max_rows=canva_batch_size)
    if len(canva_files) > 1:
        instructions = get_canva_instructions_text(
            len(canva_files), len(rows), canva_batch_size, title="Sudoku Activity Book"
        )
        canva_zip_path = os.path.join(out_dir, "sudoku_canva_bulk_batches.zip")
        package_canva_batches_zip(canva_files, canva_zip_path, instructions)
        canva_output_path = canva_zip_path
    else:
        canva_output_path = canva_files[0]

    solutions_path = None
    if not include_solution_in_same_excel:
        # Separate Solutions Excel Workbook with embedded thumbnails
        if progress_bar:
            progress_bar.progress(70, text="Generating separate solutions workbook...")

        solutions_path = os.path.join(out_dir, "sudoku_solutions.xlsx")
        wb = xlsxwriter.Workbook(solutions_path)
        ws = wb.add_worksheet("Solutions")

        cols_count = max(1, min(9, solutions_per_page))
        solution_headers = ["page_number", "title"] + [f"solution_{j}" for j in range(1, cols_count + 1)]
        for c, header in enumerate(solution_headers):
            ws.write(0, c, header)
        ws.set_column(0, 0, 12)
        ws.set_column(1, 1, 25)
        ws.set_column(2, 1 + cols_count, 32)

        for page_start in range(0, total, cols_count):
            row_idx = page_start // cols_count + 1
            ws.set_row(row_idx, 160)
            first_puzzle = puzzles[page_start]
            ws.write(row_idx, 0, page_start + 1)
            ws.write(row_idx, 1, first_puzzle.title)

            for offset in range(cols_count):
                index = page_start + offset
                if index >= len(sol_paths):
                    break
                ws.insert_image(
                    row_idx,
                    2 + offset,
                    sol_paths[index],
                    {
                        "x_scale": 0.10,
                        "y_scale": 0.10,
                        "x_offset": 5,
                        "y_offset": 5,
                        "positioning": 1,
                    },
                )
        wb.close()
    else:
        pass

    # 4. Generate KDP PDF Interior Book
    if progress_bar:
        progress_bar.progress(85, text="Building print-ready KDP PDF book...")

    pdf_bytes = build_sudoku_pdf(
        puzzles,
        style=style,
        trim_choice=trim_choice,
        puzzles_per_page=puzzles_per_page,
        solutions_per_page=solutions_per_page,
        include_instructions=include_instructions,
        show_solution_divider=True,
        date_strings=date_strings if date_enabled else None,
        calendar_images=cal_imgs if (date_enabled and cal_mode == "calendar_image") else None,
    )
    pdf_path = os.path.join(out_dir, "sudoku_kdp_interior.pdf")
    Path(pdf_path).write_bytes(pdf_bytes)

    # 5. Build Combined ZIP Archive
    if progress_bar:
        progress_bar.progress(95, text="Creating final ZIP bundle...")

    zip_path = os.path.join(out_dir, "sudoku_complete_bundle.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        if len(canva_files) > 1:
            for cf in canva_files:
                z.write(cf, f"canva_batches/{os.path.basename(cf)}")
            z.write(canva_output_path, os.path.basename(canva_output_path))
        else:
            z.write(canva_output_path, os.path.basename(canva_output_path))
        if solutions_path:
            z.write(solutions_path, os.path.basename(solutions_path))
        z.write(pdf_path, os.path.basename(pdf_path))
        for p in grid_paths + sol_paths + cal_paths:
            z.write(p, f"images/{os.path.basename(p)}")

    if progress_bar:
        progress_bar.progress(100, text="Export complete!")

    return canva_output_path, solutions_path, zip_path, pdf_bytes
