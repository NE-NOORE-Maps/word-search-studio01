"""Generate publication-ready Amazon KDP interior PDF books for Sudoku.

Features:
- Standard KDP trim sizes: 8.5" x 11" (Letter) and 6" x 9" (Trade)
- Clean, centered puzzle pages with titles, difficulty badges, and running page numbers
- Optional instructions block
- Dedicated Solutions section with selectable solutions per page (4, 6, or 9 per page)
"""
from __future__ import annotations

import io
from typing import List, Any, Optional
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from engine.sudoku import SudokuPuzzle
from core.sudoku_raster import render_sudoku_image, render_sudoku_solution_image

# Trim dimensions in points (72 pt = 1 inch)
TRIM_SIZES = {
    "8.5 x 11 inches (Letter)": (8.5 * 72, 11.0 * 72),
    "6 x 9 inches (Trade / Pocket)": (6.0 * 72, 9.0 * 72),
}


def build_sudoku_pdf(
    puzzles: List[SudokuPuzzle],
    style: Any,
    trim_choice: str = "8.5 x 11 inches (Letter)",
    puzzles_per_page: int = 1,
    solutions_per_page: int = 6,
    include_instructions: bool = True,
    show_solution_divider: bool = True,
    date_strings: Optional[List[str]] = None,
    calendar_images: Optional[List[Image.Image]] = None,
    progress_callback: Optional[Any] = None,
) -> bytes:
    """Generate a multi-page KDP-compliant PDF book with puzzle pages and solution pages."""
    page_w, page_h = TRIM_SIZES.get(trim_choice, (8.5 * 72, 11.0 * 72))
    margin = 36.0  # 0.5 inch safe margin

    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=(page_w, page_h))

    total_puzzles = len(puzzles)
    current_page_num = 1

    # Pre-render images at 300 DPI for high quality
    puzzle_imgs = []
    solution_imgs = []

    for idx, p in enumerate(puzzles):
        # Render clean grid without embedded header (PDF provides native typography)
        p_img = render_sudoku_image(p, style, cell_mm=12.0, dpi=300, solution=False, include_header=False)
        s_img = render_sudoku_solution_image(p, style, cell_mm=10.0, dpi=300, include_header=False)
        puzzle_imgs.append(p_img)
        solution_imgs.append(s_img)

        if progress_callback:
            progress_callback(int((idx / max(1, total_puzzles)) * 50), f"Rendering puzzle {idx + 1} of {total_puzzles}...")

    # -------------------------------------------------------------
    # 1. PUZZLE PAGES (1, 2, 4, or 6 games per page)
    # -------------------------------------------------------------
    if puzzles_per_page == 1:
        for idx, p in enumerate(puzzles):
            d_txt = date_strings[idx] if (date_strings and idx < len(date_strings) and date_strings[idx]) else None
            cal_img = calendar_images[idx] if (calendar_images and idx < len(calendar_images) and calendar_images[idx]) else None

            if cal_img:
                cal_w = 140.0 if page_w > 500 else 105.0
                cal_h = cal_w * 0.80
                pdf.drawImage(
                    ImageReader(cal_img),
                    page_w - margin - cal_w,
                    page_h - margin - cal_h - 10,
                    width=cal_w,
                    height=cal_h,
                    preserveAspectRatio=True,
                )
                if d_txt:
                    pdf.setFont("Helvetica-Bold", 18 if page_w > 500 else 14)
                    pdf.setFillColorRGB(0.08, 0.12, 0.10)
                    pdf.drawString(margin, page_h - margin - 22, d_txt)

                    pdf.setFont("Helvetica", 11 if page_w > 500 else 9)
                    pdf.setFillColorRGB(0.35, 0.40, 0.38)
                    pdf.drawString(margin, page_h - margin - 38, f"{p.title}  ·  {p.difficulty_label} {p.difficulty_stars}")
                else:
                    pdf.setFont("Helvetica-Bold", 18 if page_w > 500 else 14)
                    pdf.setFillColorRGB(0.08, 0.12, 0.10)
                    pdf.drawString(margin, page_h - margin - 22, p.title)

                    pdf.setFont("Helvetica", 11 if page_w > 500 else 9)
                    pdf.setFillColorRGB(0.35, 0.40, 0.38)
                    pdf.drawString(margin, page_h - margin - 38, f"Difficulty: {p.difficulty_label}   {p.difficulty_stars}")

                top_offset = margin + cal_h + 20
                if include_instructions:
                    pdf.setFont("Helvetica-Oblique", 8.5 if page_w > 500 else 7.5)
                    pdf.setFillColorRGB(0.45, 0.50, 0.48)
                    inst = "Fill in the grid so that every row, column, and block contains each number exactly once."
                    pdf.drawString(margin, page_h - top_offset, inst)
                    top_offset += 16
            else:
                if d_txt:
                    pdf.setFont("Helvetica-Bold", 20 if page_w > 500 else 16)
                    pdf.setFillColorRGB(0.08, 0.12, 0.10)
                    pdf.drawCentredString(page_w / 2.0, page_h - margin - 24, d_txt)

                    pdf.setFont("Helvetica", 11 if page_w > 500 else 9)
                    pdf.setFillColorRGB(0.35, 0.40, 0.38)
                    pdf.drawCentredString(page_w / 2.0, page_h - margin - 42, f"{p.title}  ·  {p.difficulty_label} {p.difficulty_stars}")
                else:
                    pdf.setFont("Helvetica-Bold", 20 if page_w > 500 else 16)
                    pdf.setFillColorRGB(0.08, 0.12, 0.10)
                    pdf.drawCentredString(page_w / 2.0, page_h - margin - 24, p.title)

                    pdf.setFont("Helvetica", 11 if page_w > 500 else 9)
                    pdf.setFillColorRGB(0.35, 0.40, 0.38)
                    pdf.drawCentredString(page_w / 2.0, page_h - margin - 42, f"Difficulty: {p.difficulty_label}   {p.difficulty_stars}")

                top_offset = margin + 54
                if include_instructions:
                    pdf.setFont("Helvetica-Oblique", 9 if page_w > 500 else 7.5)
                    pdf.setFillColorRGB(0.45, 0.50, 0.48)
                    inst = "Fill in the grid so that every row, column, and block contains each number exactly once."
                    if p.puzzle_type.value == "wordoku_9x9":
                        inst = f"Fill the grid so every row, column, and block contains all 9 letters of '{p.wordoku_word}'."
                    elif p.puzzle_type.value == "sudoku_x":
                        inst = "Standard rules apply, plus each main diagonal must contain numbers 1 to 9."
                    elif p.puzzle_type.value == "windoku":
                        inst = "Standard rules apply, plus each shaded 3x3 inner window contains numbers 1 to 9."
                    pdf.drawCentredString(page_w / 2.0, page_h - top_offset, inst)
                    top_offset += 16

            # Draw Puzzle Grid (Centered)
            avail_w = page_w - 2 * margin
            avail_h = page_h - top_offset - margin - 40  # leave room for footer
            grid_dim = min(avail_w, avail_h, 440.0 if page_w > 500 else 320.0)

            gx = (page_w - grid_dim) / 2.0
            gy = page_h - top_offset - 10 - grid_dim

            pdf.drawImage(
                ImageReader(puzzle_imgs[idx]),
                gx,
                gy,
                width=grid_dim,
                height=grid_dim,
                preserveAspectRatio=True,
            )

            # Footer: Page Number
            pdf.setFont("Helvetica", 9)
            pdf.setFillColorRGB(0.4, 0.4, 0.4)
            pdf.drawCentredString(page_w / 2.0, margin, str(current_page_num))

            pdf.showPage()
            current_page_num += 1

            if progress_callback:
                progress_callback(50 + int((idx / max(1, total_puzzles)) * 30), f"Building PDF page {idx + 1}...")

    elif puzzles_per_page == 2:
        # 2 puzzles per page: stacked vertically (1 column, 2 rows)
        for page_start in range(0, total_puzzles, 2):
            avail_w = page_w - 2 * margin
            avail_h = page_h - 2 * margin - 30
            slot_h = avail_h / 2.0

            for offset in range(2):
                idx = page_start + offset
                if idx >= total_puzzles:
                    break
                p = puzzles[idx]
                sy = page_h - margin - (offset + 1) * slot_h
                d_txt = date_strings[idx] if (date_strings and idx < len(date_strings) and date_strings[idx]) else ""
                cal_img = calendar_images[idx] if (calendar_images and idx < len(calendar_images) and calendar_images[idx]) else None

                pdf.setFont("Helvetica-Bold", 13 if page_w > 500 else 11)
                pdf.setFillColorRGB(0.08, 0.12, 0.10)
                if cal_img:
                    cal_w = 70.0 if page_w > 500 else 55.0
                    cal_h = cal_w * 0.80
                    pdf.drawImage(ImageReader(cal_img), page_w - margin - cal_w - 5, sy + slot_h - cal_h - 6, width=cal_w, height=cal_h, preserveAspectRatio=True)
                    lbl = f"{d_txt} · {p.title} ({p.difficulty_label})" if d_txt else f"{p.title}  ·  {p.difficulty_label} {p.difficulty_stars}"
                    pdf.drawString(margin + 5, sy + slot_h - 18, lbl)
                else:
                    lbl = f"{d_txt}  ·  {p.title}  ·  {p.difficulty_label} {p.difficulty_stars}" if d_txt else f"{p.title}  ·  {p.difficulty_label} {p.difficulty_stars}"
                    pdf.drawCentredString(page_w / 2.0, sy + slot_h - 18, lbl)

                slot_top_pad = 28
                if include_instructions and offset == 0:
                    pdf.setFont("Helvetica-Oblique", 8)
                    pdf.setFillColorRGB(0.45, 0.50, 0.48)
                    inst = "Fill each row, column, and 3x3 box with numbers 1 to 9."
                    if p.puzzle_type.value == "wordoku_9x9":
                        inst = f"Fill each row, column, and box with letters of '{p.wordoku_word}'."
                    pdf.drawCentredString(page_w / 2.0, sy + slot_h - 32, inst)
                    slot_top_pad = 40

                puz_dim = min(avail_w - 20, slot_h - slot_top_pad - 10, 260.0 if page_w > 500 else 190.0)
                gx = (page_w - puz_dim) / 2.0
                gy = sy + (slot_h - slot_top_pad - puz_dim) / 2.0

                pdf.drawImage(
                    ImageReader(puzzle_imgs[idx]),
                    gx,
                    gy,
                    width=puz_dim,
                    height=puz_dim,
                    preserveAspectRatio=True,
                )

            # Footer: Page Number
            pdf.setFont("Helvetica", 9)
            pdf.setFillColorRGB(0.4, 0.4, 0.4)
            pdf.drawCentredString(page_w / 2.0, margin, str(current_page_num))

            pdf.showPage()
            current_page_num += 1

            if progress_callback:
                progress_callback(50 + int((page_start / max(1, total_puzzles)) * 30), f"Building PDF page {current_page_num}...")

    elif puzzles_per_page == 4:
        # 4 puzzles per page: 2 columns x 2 rows
        cols_n, rows_n = 2, 2
        for page_start in range(0, total_puzzles, 4):
            avail_w = page_w - 2 * margin
            avail_h = page_h - 2 * margin - 30
            cell_w = avail_w / cols_n
            cell_h = avail_h / rows_n

            for offset in range(4):
                idx = page_start + offset
                if idx >= total_puzzles:
                    break
                p = puzzles[idx]
                col_i = offset % cols_n
                row_i = offset // cols_n

                cx = margin + col_i * cell_w
                cy = page_h - margin - (row_i + 1) * cell_h
                d_txt = date_strings[idx] if (date_strings and idx < len(date_strings) and date_strings[idx]) else ""
                cal_img = calendar_images[idx] if (calendar_images and idx < len(calendar_images) and calendar_images[idx]) else None

                pdf.setFont("Helvetica-Bold", 10.5 if page_w > 500 else 9.0)
                pdf.setFillColorRGB(0.08, 0.12, 0.10)
                if cal_img:
                    cal_w = 46.0 if page_w > 500 else 36.0
                    cal_h = cal_w * 0.80
                    pdf.drawImage(ImageReader(cal_img), cx + cell_w - cal_w - 4, cy + cell_h - cal_h - 4, width=cal_w, height=cal_h, preserveAspectRatio=True)
                    lbl = f"{d_txt} #{p.puzzle_id}" if d_txt else f"{p.title} ({p.difficulty_label})"
                    pdf.drawString(cx + 6, cy + cell_h - 14, lbl)
                else:
                    lbl = f"{d_txt}  ·  {p.title} ({p.difficulty_label})" if d_txt else f"{p.title} ({p.difficulty_label})"
                    pdf.drawCentredString(cx + cell_w / 2.0, cy + cell_h - 14, lbl)

                puz_dim = min(cell_w - 18, cell_h - 28, 200.0 if page_w > 500 else 150.0)
                gx = cx + (cell_w - puz_dim) / 2.0
                gy = cy + (cell_h - 22 - puz_dim) / 2.0

                pdf.drawImage(
                    ImageReader(puzzle_imgs[idx]),
                    gx,
                    gy,
                    width=puz_dim,
                    height=puz_dim,
                    preserveAspectRatio=True,
                )

            # Footer: Page Number
            pdf.setFont("Helvetica", 9)
            pdf.setFillColorRGB(0.4, 0.4, 0.4)
            pdf.drawCentredString(page_w / 2.0, margin, str(current_page_num))

            pdf.showPage()
            current_page_num += 1

            if progress_callback:
                progress_callback(50 + int((page_start / max(1, total_puzzles)) * 30), f"Building PDF page {current_page_num}...")

    else:  # 6
        # 6 puzzles per page: 2 columns x 3 rows
        cols_n, rows_n = 2, 3
        for page_start in range(0, total_puzzles, 6):
            avail_w = page_w - 2 * margin
            avail_h = page_h - 2 * margin - 30
            cell_w = avail_w / cols_n
            cell_h = avail_h / rows_n

            for offset in range(6):
                idx = page_start + offset
                if idx >= total_puzzles:
                    break
                p = puzzles[idx]
                col_i = offset % cols_n
                row_i = offset // cols_n

                cx = margin + col_i * cell_w
                cy = page_h - margin - (row_i + 1) * cell_h
                d_txt = date_strings[idx] if (date_strings and idx < len(date_strings) and date_strings[idx]) else ""
                cal_img = calendar_images[idx] if (calendar_images and idx < len(calendar_images) and calendar_images[idx]) else None

                pdf.setFont("Helvetica-Bold", 9.0 if page_w > 500 else 8.0)
                pdf.setFillColorRGB(0.08, 0.12, 0.10)
                if cal_img:
                    cal_w = 38.0 if page_w > 500 else 30.0
                    cal_h = cal_w * 0.80
                    pdf.drawImage(ImageReader(cal_img), cx + cell_w - cal_w - 3, cy + cell_h - cal_h - 3, width=cal_w, height=cal_h, preserveAspectRatio=True)
                    lbl = f"{d_txt} #{p.puzzle_id}" if d_txt else f"#{p.puzzle_id} ({p.difficulty_label})"
                    pdf.drawString(cx + 4, cy + cell_h - 12, lbl)
                else:
                    lbl = f"{d_txt} · {p.title}" if d_txt else f"{p.title} ({p.difficulty_label})"
                    pdf.drawCentredString(cx + cell_w / 2.0, cy + cell_h - 12, lbl)

                puz_dim = min(cell_w - 14, cell_h - 22, 160.0 if page_w > 500 else 120.0)
                gx = cx + (cell_w - puz_dim) / 2.0
                gy = cy + (cell_h - 18 - puz_dim) / 2.0

                pdf.drawImage(
                    ImageReader(puzzle_imgs[idx]),
                    gx,
                    gy,
                    width=puz_dim,
                    height=puz_dim,
                    preserveAspectRatio=True,
                )

            # Footer: Page Number
            pdf.setFont("Helvetica", 9)
            pdf.setFillColorRGB(0.4, 0.4, 0.4)
            pdf.drawCentredString(page_w / 2.0, margin, str(current_page_num))

            pdf.showPage()
            current_page_num += 1

            if progress_callback:
                progress_callback(50 + int((page_start / max(1, total_puzzles)) * 30), f"Building PDF page {current_page_num}...")

    # -------------------------------------------------------------
    # 2. SOLUTIONS SECTION
    # -------------------------------------------------------------
    if show_solution_divider:
        # Solutions Title Page
        pdf.setFont("Helvetica-Bold", 32 if page_w > 500 else 24)
        pdf.setFillColorRGB(0.08, 0.12, 0.10)
        pdf.drawCentredString(page_w / 2.0, page_h / 2.0 + 20, "SOLUTIONS")

        pdf.setFont("Helvetica", 12 if page_w > 500 else 10)
        pdf.setFillColorRGB(0.4, 0.4, 0.4)
        pdf.drawCentredString(page_w / 2.0, page_h / 2.0 - 10, "Complete Answer Keys")

        pdf.setFont("Helvetica", 9)
        pdf.drawCentredString(page_w / 2.0, margin, str(current_page_num))

        pdf.showPage()
        current_page_num += 1

    # Multi-puzzle solution pages
    cols_n = 2 if solutions_per_page in (2, 4, 6) else 3
    if solutions_per_page == 1:
        cols_n = 1
        rows_n = 1
    elif solutions_per_page == 2:
        rows_n = 1
    elif solutions_per_page == 4:
        rows_n = 2
    elif solutions_per_page == 6:
        rows_n = 3
    else: # 9
        cols_n = 3
        rows_n = 3

    for page_start in range(0, total_puzzles, solutions_per_page):
        # Section header on solution pages
        pdf.setFont("Helvetica-Bold", 14 if page_w > 500 else 12)
        pdf.setFillColorRGB(0.08, 0.12, 0.10)
        pdf.drawCentredString(page_w / 2.0, page_h - margin - 14, "SOLUTIONS")

        sol_avail_w = page_w - 2 * margin
        sol_avail_h = page_h - 2 * margin - 35
        cell_box_w = sol_avail_w / cols_n
        cell_box_h = sol_avail_h / rows_n

        for offset in range(solutions_per_page):
            p_idx = page_start + offset
            if p_idx >= total_puzzles:
                break

            col_i = offset % cols_n
            row_i = offset // cols_n

            cell_x = margin + col_i * cell_box_w
            cell_y = page_h - margin - 30 - (row_i + 1) * cell_box_h

            # Label for individual solution
            pdf.setFont("Helvetica-Bold", 9 if page_w > 500 else 7.5)
            pdf.setFillColorRGB(0.15, 0.20, 0.18)
            label_text = f"{puzzles[p_idx].title} ({puzzles[p_idx].difficulty_label})"
            pdf.drawCentredString(cell_x + cell_box_w / 2.0, cell_y + cell_box_h - 12, label_text)

            # Miniature solution grid
            sol_dim = min(cell_box_w - 16, cell_box_h - 22)
            img_x = cell_x + (cell_box_w - sol_dim) / 2.0
            img_y = cell_y + (cell_box_h - 18 - sol_dim) / 2.0

            pdf.drawImage(
                ImageReader(solution_imgs[p_idx]),
                img_x,
                img_y,
                width=sol_dim,
                height=sol_dim,
                preserveAspectRatio=True,
            )

        # Footer
        pdf.setFont("Helvetica", 9)
        pdf.setFillColorRGB(0.4, 0.4, 0.4)
        pdf.drawCentredString(page_w / 2.0, margin, str(current_page_num))

        pdf.showPage()
        current_page_num += 1

    if progress_callback:
        progress_callback(100, "PDF Book complete!")

    pdf.save()
    return buf.getvalue()
