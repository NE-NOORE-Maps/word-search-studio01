"""High-resolution Pillow raster renderer for Sudoku puzzles and solutions.

Renders crisp 300 DPI print-ready images for Amazon KDP and fast 150 DPI
previews for the Streamlit UI. Supports classic grid lines, rounded boxes,
checkerboard block shading, diagonal highlights (Sudoku X), and window highlights (Windoku).
"""
from __future__ import annotations

import base64
import io
import os
from types import SimpleNamespace
from typing import Any, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

from engine.sudoku import SudokuPuzzle, SudokuType

MM = 25.4
_FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "fonts")


def _rgb(spec: str, default: Tuple[int, int, int] = (0, 0, 0)) -> Tuple[int, int, int]:
    """Convert hex string (e.g. '#17352b') to RGB tuple."""
    s = (spec or "").strip().lower()
    if s.startswith("#") and len(s) == 7:
        try:
            return (int(s[1:3], 16), int(s[3:5], 16), int(s[5:7], 16))
        except ValueError:
            return default
    if s in ("black", "#000000"):
        return (0, 0, 0)
    if s in ("white", "#ffffff"):
        return (255, 255, 255)
    return default


def _font_path(name: str) -> str:
    """Resolve a font name to a bundled TTF path (fallback: DejaVu Sans)."""
    for candidate in (name, "DejaVu Sans Bold", "DejaVu Sans"):
        p = os.path.join(_FONTS_DIR, f"{candidate}.ttf")
        if os.path.exists(p):
            return p
    return os.path.join(_FONTS_DIR, "DejaVu Sans.ttf")


__all__ = [
    "SUDOKU_PRESETS",
    "render_sudoku_image",
    "render_sudoku_solution_image",
    "render_sudoku_solution_page_image",
    "render_sudoku_puzzle_page_image",
    "sudoku_image_data_uri",
]

# Audience presets specifically designed for Sudoku publishing
SUDOKU_PRESETS = {
    "👔 Adult Classic": {
        "cell_style": "grid",
        "outer_line_width": 1.4,
        "block_line_width": 1.0,
        "inner_line_width": 0.4,
        "grid_color": "#111815",
        "shading_mode": "none",
        "shading_color": "#ecefe9",
        "font_scale": 64,
        "clue_font": "DejaVu Sans Bold",
        "clue_color": "#111815",
        "solution_color": "#1d4ed8", # Crisp royal blue
        "solution_mode": "color",
        "description": "Standard high-contrast publishing layout with bold 3×3 box dividers and balanced digits.",
    },
    "👓 Senior / Large Print": {
        "cell_style": "grid",
        "outer_line_width": 2.0,
        "block_line_width": 1.5,
        "inner_line_width": 0.7,
        "grid_color": "#000000",
        "shading_mode": "none",
        "shading_color": "#e8eae6",
        "font_scale": 82,
        "clue_font": "DejaVu Sans Bold",
        "clue_color": "#000000",
        "solution_color": "#1e3a8a",
        "solution_mode": "color",
        "description": "Extra-bold high-visibility borders with giant 82% digits for maximum reading comfort.",
    },
    "🏁 Checkerboard / Shaded Blocks": {
        "cell_style": "grid",
        "outer_line_width": 1.3,
        "block_line_width": 1.0,
        "inner_line_width": 0.4,
        "grid_color": "#1f2937",
        "shading_mode": "checkerboard",
        "shading_color": "#ebefe9",
        "font_scale": 65,
        "clue_font": "DejaVu Sans Bold",
        "clue_color": "#111815",
        "solution_color": "#047857", # Emerald green
        "solution_mode": "color",
        "description": "Alternating soft shaded 3×3 blocks to help solvers track regions effortlessly.",
    },
    "🎈 Kids Fun (Rounded Tiles)": {
        "cell_style": "rounded_boxes",
        "outer_line_width": 1.0,
        "block_line_width": 0.8,
        "inner_line_width": 0.5,
        "grid_color": "#334155",
        "shading_mode": "none",
        "shading_color": "#f1f5f9",
        "font_scale": 76,
        "clue_font": "DejaVu Sans Bold",
        "clue_color": "#0f172a",
        "solution_color": "#b91c1c", # Terracotta red
        "solution_mode": "color",
        "description": "Soft rounded cell cards with large friendly digits. Ideal for 4×4 and 6×6 kids books.",
    },
    "📐 Modern Minimalist": {
        "cell_style": "grid",
        "outer_line_width": 1.1,
        "block_line_width": 0.7,
        "inner_line_width": 0.3,
        "grid_color": "#4b5563",
        "shading_mode": "none",
        "shading_color": "#f3f4f6",
        "font_scale": 60,
        "clue_font": "DejaVu Sans",
        "clue_color": "#1f2937",
        "solution_color": "#4f46e5", # Indigo
        "solution_mode": "color",
        "description": "Clean, understated hairline aesthetic with contemporary proportion and neutral tones.",
    },
    "⚙️ Custom": {
        "cell_style": "grid",
        "outer_line_width": 1.4,
        "block_line_width": 1.0,
        "inner_line_width": 0.4,
        "grid_color": "#111815",
        "shading_mode": "none",
        "shading_color": "#ecefe9",
        "font_scale": 64,
        "clue_font": "DejaVu Sans Bold",
        "clue_color": "#111815",
        "solution_color": "#1d4ed8",
        "solution_mode": "color",
        "description": "Full manual control over every slider, border thickness, shading, and color.",
    },
}


def render_sudoku_image(
    puzzle: SudokuPuzzle,
    style: Any,
    cell_mm: float = 12.0,
    dpi: int = 300,
    solution: bool = False,
    include_header: bool = False,
    date_text: Optional[str] = None,
) -> Image.Image:
    """Render a Sudoku puzzle (or its solution) to a PIL Image at specified DPI.

    Args:
        puzzle: SudokuPuzzle instance
        style: Style attributes namespace
        cell_mm: Size of each cell in millimeters
        dpi: Target DPI (300 for print, 150-180 for preview)
        solution: If True, renders complete solution with distinct clue vs solved markings
        include_header: If True, draws title and difficulty badge above the grid
        date_text: Optional formatted date string to display in header
    """
    size = puzzle.size
    box_r = puzzle.box_rows
    box_c = puzzle.box_cols

    cell_px = max(6, round(cell_mm / MM * dpi))
    grid_w = size * cell_px
    grid_h = size * cell_px

    # Resolve style parameters with robust fallbacks
    cell_style = getattr(style, "cell_style", "grid")
    outer_lw = max(1, round(getattr(style, "outer_line_width", 1.4) / MM * dpi))
    block_lw = max(1, round(getattr(style, "block_line_width", 1.0) / MM * dpi))
    inner_lw = max(1, round(getattr(style, "inner_line_width", 0.4) / MM * dpi))

    grid_color = _rgb(getattr(style, "grid_color", "#111815"))
    clue_color = _rgb(getattr(style, "clue_color", "#111815"))
    sol_color = _rgb(getattr(style, "solution_color", "#1d4ed8"))
    shading_color = _rgb(getattr(style, "shading_color", "#ecefe9"))
    shading_mode = getattr(style, "shading_mode", "none")

    font_scale = getattr(style, "font_scale", 64) / 100.0
    font_name = getattr(style, "clue_font", "DejaVu Sans Bold")
    font_px = max(8, round(cell_px * font_scale))
    font = ImageFont.truetype(_font_path(font_name), font_px)

    # Calculate image dimensions (header vs pure grid)
    header_h_px = 0
    if include_header:
        header_h_px = round(16.0 / MM * dpi)

    total_w = grid_w
    total_h = grid_h + header_h_px

    img = Image.new("RGB", (total_w, total_h), (255, 255, 255))
    d = ImageDraw.Draw(img)

    # 1. Optional Header Rendering
    if include_header:
        # Title text
        title_font_px = max(10, round(header_h_px * 0.42))
        title_font = ImageFont.truetype(_font_path("DejaVu Sans Bold"), title_font_px)
        sub_font_px = max(8, round(header_h_px * 0.28))
        sub_font = ImageFont.truetype(_font_path("DejaVu Sans"), sub_font_px)

        title_display = f"{puzzle.title} · {date_text}" if date_text else puzzle.title
        d.text((10, header_h_px * 0.35), title_display, fill=clue_color, font=title_font, anchor="lm")
        diff_text = f"{puzzle.difficulty_label}  {puzzle.difficulty_stars}"
        d.text((grid_w - 10, header_h_px * 0.35), diff_text, fill=(75, 85, 99), font=sub_font, anchor="rm")
        d.line([(0, header_h_px - 2), (grid_w, header_h_px - 2)], fill=(220, 225, 222), width=1)

    y_offset = header_h_px

    # 2. Shading Layer (Cells, Checkerboard, Diagonals, Windows)
    # Check if variant requires specific shading
    apply_x = puzzle.is_x or shading_mode == "diagonal"
    apply_windoku = puzzle.is_windoku or shading_mode == "windows"
    apply_checker = shading_mode == "checkerboard"

    windows = [(1, 1), (1, 5), (5, 1), (5, 5)] if (apply_windoku and size == 9) else []

    for r in range(size):
        for c in range(size):
            is_shaded = False

            # Checkerboard 3x3 blocks
            if apply_checker:
                br_idx = r // box_r
                bc_idx = c // box_c
                if (br_idx + bc_idx) % 2 == 1:
                    is_shaded = True

            # Sudoku X diagonals
            if apply_x:
                if r == c or (r + c == size - 1):
                    is_shaded = True

            # Windoku 4 inner windows
            if apply_windoku:
                for wr, wc in windows:
                    if wr <= r < wr + 3 and wc <= c < wc + 3:
                        is_shaded = True
                        break

            if is_shaded:
                x0 = c * cell_px
                y0 = y_offset + r * cell_px
                x1 = x0 + cell_px
                y1 = y0 + cell_px
                d.rectangle([x0, y0, x1, y1], fill=shading_color)

    # 3. Grid Lines & Cell Borders
    if cell_style == "rounded_boxes":
        radius = round(cell_px * 0.18)
        pad = max(1, round(cell_px * 0.04))
        for r in range(size):
            for c in range(size):
                x0 = c * cell_px + pad
                y0 = y_offset + r * cell_px + pad
                x1 = (c + 1) * cell_px - pad
                y1 = y_offset + (r + 1) * cell_px - pad
                d.rounded_rectangle([x0, y0, x1, y1], radius=radius, outline=grid_color, width=inner_lw)

        # Draw thick box boundaries as accents
        for r in range(0, size + 1, box_r):
            y = min(y_offset + r * cell_px, total_h - 1)
            d.line([(0, y), (grid_w, y)], fill=grid_color, width=block_lw)
        for c in range(0, size + 1, box_c):
            x = min(c * cell_px, grid_w - 1)
            d.line([(x, y_offset), (x, total_h)], fill=grid_color, width=block_lw)

    elif cell_style == "boxes":
        pad = max(1, round(cell_px * 0.05))
        for r in range(size):
            for c in range(size):
                x0 = c * cell_px + pad
                y0 = y_offset + r * cell_px + pad
                x1 = (c + 1) * cell_px - pad
                y1 = y_offset + (r + 1) * cell_px - pad
                d.rectangle([x0, y0, x1, y1], outline=grid_color, width=inner_lw)

    else:
        # Standard Continuous Grid Lines
        # Thin inner cell lines
        for r in range(size + 1):
            y = min(y_offset + r * cell_px, total_h - 1)
            d.line([(0, y), (grid_w, y)], fill=grid_color, width=inner_lw)
        for c in range(size + 1):
            x = min(c * cell_px, grid_w - 1)
            d.line([(x, y_offset), (x, total_h)], fill=grid_color, width=inner_lw)

        # Thick 3×3 (or 2×2 / 2×3) block lines
        for r in range(0, size + 1, box_r):
            y = min(y_offset + r * cell_px, total_h - 1)
            d.line([(0, y), (grid_w, y)], fill=grid_color, width=block_lw)
        for c in range(0, size + 1, box_c):
            x = min(c * cell_px, grid_w - 1)
            d.line([(x, y_offset), (x, total_h)], fill=grid_color, width=block_lw)

        # Outer thick border frame
        half_out = outer_lw // 2
        d.rectangle(
            [half_out, y_offset + half_out, grid_w - half_out - 1, total_h - half_out - 1],
            outline=grid_color,
            width=outer_lw,
        )

    # 4. Digits / Symbols Rendering
    solution_mode = getattr(style, "solution_mode", "color")

    for r in range(size):
        for c in range(size):
            is_original_clue = bool(puzzle.clues_grid[r][c])
            symbol = puzzle.solution_grid[r][c] if solution else puzzle.clues_grid[r][c]

            if not symbol:
                continue

            cx = c * cell_px + cell_px / 2.0
            cy = y_offset + r * cell_px + cell_px / 2.0

            if solution:
                if is_original_clue:
                    # Clue: drawn in strong clue color
                    d.text((cx, cy), symbol, font=font, fill=clue_color, anchor="mm")
                else:
                    # Solved number: distinct color or styling
                    if solution_mode == "circled":
                        circle_r = cell_px * 0.40
                        d.ellipse(
                            [cx - circle_r, cy - circle_r, cx + circle_r, cy + circle_r],
                            outline=sol_color,
                            width=max(1, round(inner_lw * 1.5)),
                        )
                        d.text((cx, cy), symbol, font=font, fill=sol_color, anchor="mm")
                    elif solution_mode == "color":
                        d.text((cx, cy), symbol, font=font, fill=sol_color, anchor="mm")
                    else:
                        d.text((cx, cy), symbol, font=font, fill=clue_color, anchor="mm")
            else:
                # Regular puzzle view: all clues drawn in clue_color
                d.text((cx, cy), symbol, font=font, fill=clue_color, anchor="mm")

    return img


def render_sudoku_solution_image(
    puzzle: SudokuPuzzle,
    style: Any,
    cell_mm: float = 12.0,
    dpi: int = 300,
    include_header: bool = False,
) -> Image.Image:
    """Helper to render solution directly."""
    return render_sudoku_image(
        puzzle,
        style,
        cell_mm=cell_mm,
        dpi=dpi,
        solution=True,
        include_header=include_header,
    )


def sudoku_image_data_uri(
    puzzle: SudokuPuzzle,
    style: Any,
    cell_mm: float = 12.0,
    dpi: int = 170,
    solution: bool = False,
    include_header: bool = False,
) -> Optional[str]:
    """Generate base64 data URI of the rendered Sudoku."""
    try:
        img = render_sudoku_image(
            puzzle, style, cell_mm=cell_mm, dpi=dpi, solution=solution, include_header=include_header
        )
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/png;base64,{b64}"
    except Exception:
        return None


def render_sudoku_solution_page_image(
    puzzles_slice: list[SudokuPuzzle],
    style: Any,
    solutions_per_page: int = 6,
    page_num: int = 1,
    total_pages: int = 1,
    dpi: int = 150,
) -> Image.Image:
    """Render a composite solution book page with multiple Sudoku puzzle answers."""
    w = int(8.5 * dpi)
    h = int(11.0 * dpi)
    img = Image.new("RGB", (w, h), (255, 255, 255))
    d = ImageDraw.Draw(img)

    title_size = max(16, round(26.0 / 72.0 * dpi))
    sub_size = max(10, round(13.0 / 72.0 * dpi))
    lbl_size = max(9, round(11.5 / 72.0 * dpi))

    font_title = ImageFont.truetype(_font_path("DejaVu Sans Bold"), title_size)
    font_sub = ImageFont.truetype(_font_path("DejaVu Sans"), sub_size)
    font_lbl = ImageFont.truetype(_font_path("DejaVu Sans Bold"), lbl_size)

    d.text((w / 2, 45), "SOLUTIONS", fill=(20, 35, 30), font=font_title, anchor="mm")
    d.text((w / 2, 75), f"Answer Keys · Page {page_num} of {total_pages}", fill=(100, 115, 110), font=font_sub, anchor="mm")
    d.line([(60, 95), (w - 60, 95)], fill=(220, 225, 220), width=2)

    if solutions_per_page == 1:
        cols, rows = 1, 1
    elif solutions_per_page == 2:
        cols, rows = 2, 1
    elif solutions_per_page == 4:
        cols, rows = 2, 2
    elif solutions_per_page == 6:
        cols, rows = 2, 3
    else:  # 9
        cols, rows = 3, 3

    margin_x, margin_y = 60, 115
    cell_w = (w - 2 * margin_x) / cols
    cell_h = (h - margin_y - 60) / rows

    for idx, p in enumerate(puzzles_slice):
        if idx >= cols * rows:
            break
        col = idx % cols
        row = idx // cols
        cx = margin_x + col * cell_w
        cy = margin_y + row * cell_h

        lbl = f"{p.title} ({p.difficulty_label})"
        d.text((cx + cell_w / 2, cy + 16), lbl, fill=(30, 45, 40), font=font_lbl, anchor="mm")

        sol = render_sudoku_solution_image(p, style, cell_mm=10.0, dpi=dpi, include_header=False)
        avail_dim = min(cell_w - 30, cell_h - 40)
        sol_resized = sol.resize((int(avail_dim), int(avail_dim)), Image.Resampling.LANCZOS)

        ox = cx + (cell_w - avail_dim) / 2
        oy = cy + 28 + (cell_h - 35 - avail_dim) / 2
        img.paste(sol_resized, (int(ox), int(oy)))

    d.text((w / 2, h - 25), f"Page {page_num}", fill=(120, 120, 120), font=font_sub, anchor="mm")
    return img


def render_sudoku_puzzle_page_image(
    puzzles_slice: list[SudokuPuzzle],
    style: Any,
    puzzles_per_page: int = 1,
    page_num: int = 1,
    total_pages: int = 1,
    dpi: int = 150,
    include_instructions: bool = True,
    date_strings: Optional[list[str]] = None,
    calendar_images: Optional[list[Image.Image]] = None,
) -> Image.Image:
    """Render a composite book interior page showing 1, 2, 4, or 6 Sudoku puzzles with optional dates/calendars."""
    w = int(8.5 * dpi)
    h = int(11.0 * dpi)
    img = Image.new("RGB", (w, h), (255, 255, 255))
    d = ImageDraw.Draw(img)

    title_size = max(16, round(24.0 / 72.0 * dpi))
    sub_size = max(10, round(12.5 / 72.0 * dpi))
    lbl_size = max(9, round(11.0 / 72.0 * dpi))
    inst_size = max(8, round(9.5 / 72.0 * dpi))

    font_title = ImageFont.truetype(_font_path("DejaVu Sans Bold"), title_size)
    font_sub = ImageFont.truetype(_font_path("DejaVu Sans"), sub_size)
    font_lbl = ImageFont.truetype(_font_path("DejaVu Sans Bold"), lbl_size)
    font_inst = ImageFont.truetype(_font_path("DejaVu Sans"), inst_size)

    if puzzles_per_page == 1 and puzzles_slice:
        p = puzzles_slice[0]
        d_txt = date_strings[0] if (date_strings and len(date_strings) > 0 and date_strings[0]) else None
        cal_img = calendar_images[0] if (calendar_images and len(calendar_images) > 0 and calendar_images[0]) else None

        if cal_img:
            cal_w = int(w * 0.32)
            cal_h = int(cal_w * 0.80)
            cal_res = cal_img.resize((cal_w, cal_h), Image.Resampling.LANCZOS)
            cal_x = w - 60 - cal_w
            cal_y = 35
            img.paste(cal_res, (cal_x, cal_y))

            header_x = 60
            if d_txt:
                d.text((header_x, 50), d_txt, fill=(20, 35, 30), font=font_title)
                d.text((header_x, 85), f"{p.title}  ·  {p.difficulty_label} {p.difficulty_stars}", fill=(90, 105, 98), font=font_sub)
            else:
                d.text((header_x, 50), p.title, fill=(20, 35, 30), font=font_title)
                d.text((header_x, 85), f"Difficulty: {p.difficulty_label}   {p.difficulty_stars}", fill=(90, 105, 98), font=font_sub)

            top_offset = 35 + cal_h + 15
            if include_instructions:
                d.text((w / 2, top_offset + 12), "Fill in the grid so every row, column, and block contains each number exactly once.", fill=(110, 125, 118), font=font_inst, anchor="mm")
                top_offset += 28
        else:
            if d_txt:
                d.text((w / 2, 45), d_txt, fill=(20, 35, 30), font=font_title, anchor="mm")
                d.text((w / 2, 78), f"{p.title}  ·  {p.difficulty_label} {p.difficulty_stars}", fill=(90, 105, 98), font=font_sub, anchor="mm")
            else:
                d.text((w / 2, 50), p.title, fill=(20, 35, 30), font=font_title, anchor="mm")
                d.text((w / 2, 85), f"Difficulty: {p.difficulty_label}   {p.difficulty_stars}", fill=(90, 105, 98), font=font_sub, anchor="mm")

            top_offset = 100
            if include_instructions:
                d.text((w / 2, 115), "Fill in the grid so every row, column, and block contains each number exactly once.", fill=(110, 125, 118), font=font_inst, anchor="mm")
                top_offset = 135

        p_img = render_sudoku_image(p, style, cell_mm=12.0, dpi=dpi, solution=False, include_header=False)
        avail = min(w - 120, h - top_offset - 80)
        p_resized = p_img.resize((int(avail), int(avail)), Image.Resampling.LANCZOS)
        ox = (w - avail) / 2
        oy = top_offset + (h - top_offset - 60 - avail) / 2
        img.paste(p_resized, (int(ox), int(oy)))

    elif puzzles_per_page == 2:
        cols, rows = 1, 2
        margin_x, margin_y = 60, 45
        cell_w = w - 2 * margin_x
        cell_h = (h - margin_y - 60) / rows

        for idx, p in enumerate(puzzles_slice[:2]):
            cy = margin_y + idx * cell_h
            d_txt = date_strings[idx] if (date_strings and idx < len(date_strings) and date_strings[idx]) else ""
            cal_img = calendar_images[idx] if (calendar_images and idx < len(calendar_images) and calendar_images[idx]) else None

            if cal_img:
                cal_w = int(cell_w * 0.22)
                cal_h = int(cal_w * 0.80)
                cal_res = cal_img.resize((cal_w, cal_h), Image.Resampling.LANCZOS)
                img.paste(cal_res, (int(w - margin_x - cal_w), int(cy + 10)))
                lbl = f"{d_txt} · {p.title} ({p.difficulty_label})" if d_txt else f"{p.title} · {p.difficulty_label} {p.difficulty_stars}"
                d.text((margin_x + 10, cy + 22), lbl, fill=(20, 35, 30), font=font_lbl)
            else:
                lbl = f"{d_txt}  ·  {p.title}  ·  {p.difficulty_label} {p.difficulty_stars}" if d_txt else f"{p.title}  ·  {p.difficulty_label} {p.difficulty_stars}"
                d.text((w / 2, cy + 18), lbl, fill=(20, 35, 30), font=font_lbl, anchor="mm")

            p_img = render_sudoku_image(p, style, cell_mm=10.0, dpi=dpi, solution=False, include_header=False)
            avail = min(cell_w - 40, cell_h - 45)
            p_resized = p_img.resize((int(avail), int(avail)), Image.Resampling.LANCZOS)
            ox = (w - avail) / 2
            oy = cy + 30 + (cell_h - 45 - avail) / 2
            img.paste(p_resized, (int(ox), int(oy)))

    elif puzzles_per_page == 4:
        cols, rows = 2, 2
        margin_x, margin_y = 50, 40
        cell_w = (w - 2 * margin_x) / cols
        cell_h = (h - margin_y - 50) / rows

        for idx, p in enumerate(puzzles_slice[:4]):
            col = idx % cols
            row = idx // cols
            cx = margin_x + col * cell_w
            cy = margin_y + row * cell_h

            d_txt = date_strings[idx] if (date_strings and idx < len(date_strings) and date_strings[idx]) else ""
            cal_img = calendar_images[idx] if (calendar_images and idx < len(calendar_images) and calendar_images[idx]) else None

            if cal_img:
                cal_w = int(cell_w * 0.24)
                cal_h = int(cal_w * 0.80)
                cal_res = cal_img.resize((cal_w, cal_h), Image.Resampling.LANCZOS)
                img.paste(cal_res, (int(cx + cell_w - cal_w - 6), int(cy + 4)))
                lbl = f"{d_txt} #{p.puzzle_id}" if d_txt else f"{p.title} ({p.difficulty_label})"
                d.text((cx + 10, cy + 16), lbl, fill=(20, 35, 30), font=font_lbl)
            else:
                lbl = f"{d_txt}  ·  {p.title} ({p.difficulty_label})" if d_txt else f"{p.title} ({p.difficulty_label})"
                d.text((cx + cell_w / 2, cy + 15), lbl, fill=(20, 35, 30), font=font_lbl, anchor="mm")

            p_img = render_sudoku_image(p, style, cell_mm=10.0, dpi=dpi, solution=False, include_header=False)
            avail = min(cell_w - 28, cell_h - 38)
            p_resized = p_img.resize((int(avail), int(avail)), Image.Resampling.LANCZOS)
            ox = cx + (cell_w - avail) / 2
            oy = cy + 26 + (cell_h - 38 - avail) / 2
            img.paste(p_resized, (int(ox), int(oy)))

    else:  # 6
        cols, rows = 2, 3
        margin_x, margin_y = 50, 35
        cell_w = (w - 2 * margin_x) / cols
        cell_h = (h - margin_y - 45) / rows

        for idx, p in enumerate(puzzles_slice[:6]):
            col = idx % cols
            row = idx // cols
            cx = margin_x + col * cell_w
            cy = margin_y + row * cell_h

            d_txt = date_strings[idx] if (date_strings and idx < len(date_strings) and date_strings[idx]) else ""
            cal_img = calendar_images[idx] if (calendar_images and idx < len(calendar_images) and calendar_images[idx]) else None

            if cal_img:
                cal_w = int(cell_w * 0.22)
                cal_h = int(cal_w * 0.80)
                cal_res = cal_img.resize((cal_w, cal_h), Image.Resampling.LANCZOS)
                img.paste(cal_res, (int(cx + cell_w - cal_w - 4), int(cy + 4)))
                lbl = f"{d_txt} #{p.puzzle_id}" if d_txt else f"#{p.puzzle_id} ({p.difficulty_label})"
                d.text((cx + 6, cy + 13), lbl, fill=(20, 35, 30), font=font_lbl)
            else:
                lbl = f"{d_txt} · {p.title}" if d_txt else f"{p.title} ({p.difficulty_label})"
                d.text((cx + cell_w / 2, cy + 12), lbl, fill=(20, 35, 30), font=font_lbl, anchor="mm")

            p_img = render_sudoku_image(p, style, cell_mm=10.0, dpi=dpi, solution=False, include_header=False)
            avail = min(cell_w - 22, cell_h - 30)
            p_resized = p_img.resize((int(avail), int(avail)), Image.Resampling.LANCZOS)
            ox = cx + (cell_w - avail) / 2
            oy = cy + 22 + (cell_h - 30 - avail) / 2
            img.paste(p_resized, (int(ox), int(oy)))

    d.text((w / 2, h - 25), f"Page {page_num}", fill=(120, 120, 120), font=font_sub, anchor="mm")
    return img


