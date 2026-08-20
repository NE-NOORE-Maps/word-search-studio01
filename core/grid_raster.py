"""Rasterize a word-search grid to a single PNG (user request / plan §8).

When a Canva export renders the grid as many vector cells + individual letter
runs, Canva imports each as a separate object and the grid falls apart. Drawing
the grid as ONE raster image keeps it intact as a single Canva object, while the
title, subtitle and word bank stay as editable text.
"""
from __future__ import annotations

import base64
import io
import os
from typing import Optional

MM = 25.4
_FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "fonts")


def _rgb(spec: str, default=(0, 0, 0)):
    s = (spec or "").strip().lower()
    if s.startswith("#") and len(s) == 7:
        return (int(s[1:3], 16), int(s[3:5], 16), int(s[5:7], 16))
    if s in ("black", "#000000"):
        return (0, 0, 0)
    if s in ("white", "#ffffff"):
        return (255, 255, 255)
    return default


def _font_path(name: str) -> str:
    """Resolve a font name to a bundled TTF path (fallback: DejaVu Sans)."""
    for candidate in (name, "DejaVu Sans"):
        p = os.path.join(_FONTS_DIR, f"{candidate}.ttf")
        if os.path.exists(p):
            return p
    return os.path.join(_FONTS_DIR, "DejaVu Sans.ttf")


def render_grid_image(puzzle, style, cell_mm: float, dpi: int = 300):
    """Draw the grid (cells + letters) to a PIL image sized cols×rows cells.

    ``cell_mm`` is the cell size the layout chose; the image is rendered at
    ``dpi`` so it stays crisp when placed back at cell_mm on the page.
    """
    from PIL import Image, ImageDraw, ImageFont

    rows_n, cols_n = puzzle.rows, puzzle.cols
    cell_px = max(4, round(cell_mm / MM * dpi))
    w, h = cols_n * cell_px, rows_n * cell_px
    lw = max(1, round(style.grid_line_width / MM * dpi))
    lc = _rgb(style.grid_line_color)
    letter_c = _rgb(style.letter_color)

    img = Image.new("RGB", (w, h), (255, 255, 255))
    d = ImageDraw.Draw(img)

    # Optional alternating row shading, behind everything.
    if getattr(style, "row_shading", False):
        for r in range(rows_n):
            if r % 2 == 1:
                d.rectangle([0, r * cell_px, w, (r + 1) * cell_px], fill=(230, 230, 230))

    cs = style.cell_style
    if cs in ("boxes", "rounded_boxes"):
        radius = round(cell_px * 0.18) if cs == "rounded_boxes" else 0
        for r in range(rows_n):
            for c in range(cols_n):
                x0, y0 = c * cell_px, r * cell_px
                box = [x0, y0, x0 + cell_px - 1, y0 + cell_px - 1]
                if radius:
                    d.rounded_rectangle(box, radius=radius, outline=lc, width=lw)
                else:
                    d.rectangle(box, outline=lc, width=lw)
    elif cs == "grid":
        for r in range(rows_n + 1):
            y = min(r * cell_px, h - 1)
            d.line([(0, y), (w, y)], fill=lc, width=lw)
        for c in range(cols_n + 1):
            x = min(c * cell_px, w - 1)
            d.line([(x, 0), (x, h)], fill=lc, width=lw)
    # "none" => letters only.

    # Letters, centred in each cell.
    letter_pt = style.letter_size_pt
    font_px = round(letter_pt / 72.0 * dpi) if letter_pt else round(cell_px * 0.62)
    font = ImageFont.truetype(_font_path(style.letter_font), font_px)
    for r in range(rows_n):
        for c in range(cols_n):
            ch = puzzle.grid[r][c]
            cx, cy = c * cell_px + cell_px / 2, r * cell_px + cell_px / 2
            d.text((cx, cy), ch, font=font, fill=letter_c, anchor="mm")

    return img


def grid_image_data_uri(
    puzzle, style, cell_mm: float, dpi: int = 300
) -> Optional[str]:
    """Return a base64 PNG data URI of the grid, or None on failure."""
    try:
        img = render_grid_image(puzzle, style, cell_mm, dpi)
    except Exception:  # noqa: BLE001
        return None
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def render_solution_image(puzzle, style, cell_mm: float, dpi: int = 300):
    """Rasterize the solution grid to keep it intact in Canva."""
    from PIL import Image, ImageDraw, ImageFont

    rows_n, cols_n = puzzle.rows, puzzle.cols
    cell_px = max(4, round(cell_mm / MM * dpi))
    w, h = cols_n * cell_px, rows_n * cell_px
    lw = max(1, round(style.grid_line_width / MM * dpi))
    lc = _rgb(style.grid_line_color)
    
    sol_style = style.solution_style
    sol_color = _rgb(style.solution_color)
    letter_c = _rgb(style.letter_color)

    img = Image.new("RGB", (w, h), (255, 255, 255))
    d = ImageDraw.Draw(img)

    solved_cells = set()
    for p in puzzle.placements:
        for rc in p.cells():
            solved_cells.add(rc)

    # Draw markers on a transparent overlay for highlighter effect
    overlay = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    d_over = ImageDraw.Draw(overlay)
    marker_rgba = (128, 128, 128, 80)  # fixed low opacity grey for B/W print visibility

    if sol_style == "capsule":
        for p in puzzle.placements:
            cells = p.cells()
            (r_a, c_a), (r_b, c_b) = cells[0], cells[-1]
            cx_a = c_a * cell_px + cell_px / 2
            cy_a = r_a * cell_px + cell_px / 2
            cx_b = c_b * cell_px + cell_px / 2
            cy_b = r_b * cell_px + cell_px / 2
            
            cap_r = cell_px * 0.4
            d_over.line([(cx_a, cy_a), (cx_b, cy_b)], fill=marker_rgba, width=round(cap_r*2))
            d_over.ellipse([cx_a - cap_r, cy_a - cap_r, cx_a + cap_r, cy_a + cap_r], fill=marker_rgba)
            d_over.ellipse([cx_b - cap_r, cy_b - cap_r, cx_b + cap_r, cy_b + cap_r], fill=marker_rgba)

    elif sol_style == "box":
        for (r, c) in solved_cells:
            box = [c * cell_px, r * cell_px, (c + 1) * cell_px - 1, (r + 1) * cell_px - 1]
            d_over.rectangle(box, outline=marker_rgba, width=max(2, round(1.0 / MM * dpi)))

    # Composite the markers onto the base RGB image
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    d = ImageDraw.Draw(img)

    for r in range(rows_n + 1):
        y = min(r * cell_px, h - 1)
        d.line([(0, y), (w, y)], fill=lc, width=lw)
    for c in range(cols_n + 1):
        x = min(c * cell_px, w - 1)
        d.line([(x, 0), (x, h)], fill=lc, width=lw)

    letter_pt = style.letter_size_pt
    font_px = round(letter_pt / 72.0 * dpi) if letter_pt else round(cell_px * 0.62)
    font_normal = ImageFont.truetype(_font_path(style.letter_font), font_px)
    
    # Simple boldify for PIL
    b_font = style.letter_font
    if "Bold" not in b_font and not b_font.endswith("-Bold"):
        if b_font == "DejaVu Sans": b_font = "DejaVu Sans Bold"
        elif b_font == "DejaVu Serif": b_font = "DejaVu Serif Bold"
    font_bold = ImageFont.truetype(_font_path(b_font), font_px)

    for r in range(rows_n):
        for c in range(cols_n):
            ch = puzzle.grid[r][c]
            solved = (r, c) in solved_cells
            cx, cy = c * cell_px + cell_px / 2, r * cell_px + cell_px / 2
            
            fnt = font_bold if (sol_style == "bold" and solved) else font_normal
            col = sol_color if (sol_style == "bold" and solved) else letter_c
            d.text((cx, cy), ch, font=fnt, fill=col, anchor="mm")

    return img
