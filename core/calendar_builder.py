"""Mini monthly calendar generator and date formatting utilities for activity books.

Provides:
- Cross-platform date formatting (e.g., '27-September', '27-sept-2026', '9-27-2026')
- High-resolution 300 DPI mini month calendar image generator with highlighted day badge
- Pre-configured color themes tailored for KDP activity and puzzle books
"""
from __future__ import annotations

import calendar
import datetime
import os
from typing import Any, Dict, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

_FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "fonts")


def _font_path(name: str) -> str:
    """Resolve a bundled TTF font path with fallback."""
    for candidate in (name, "DejaVu Sans Bold", "DejaVu Sans"):
        p = os.path.join(_FONTS_DIR, f"{candidate}.ttf")
        if os.path.exists(p):
            return p
    return os.path.join(_FONTS_DIR, "DejaVu Sans.ttf")


def _hex_to_rgb(hex_str: str, default: Tuple[int, int, int] = (0, 0, 0)) -> Tuple[int, int, int]:
    s = (hex_str or "").strip().lstrip("#")
    if len(s) == 6:
        try:
            return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
        except ValueError:
            pass
    return default


DATE_FORMAT_PRESETS = [
    "27-September",
    "27-september",
    "27-Sep-2026",
    "27-sept-2026",
    "9-27-2026",
    "09/27/2026",
    "September 27, 2026",
    "Sunday, September 27",
    "Sun, Sep 27, 2026",
    "2026-09-27",
]

CALENDAR_THEMES: Dict[str, Dict[str, str]] = {
    "Modern Emerald": {
        "header_color": "#184534",
        "badge_color": "#184534",
        "day_header_color": "#52796F",
        "text_color": "#1E293B",
        "highlight_text_color": "#FFFFFF",
        "border_color": "#D1D5DB",
        "bg_color": "#FFFFFF",
    },
    "Minimalist Slate": {
        "header_color": "#0F172A",
        "badge_color": "#0F172A",
        "day_header_color": "#64748B",
        "text_color": "#1E293B",
        "highlight_text_color": "#FFFFFF",
        "border_color": "#E2E8F0",
        "bg_color": "#FFFFFF",
    },
    "Classic Navy": {
        "header_color": "#1E3A8A",
        "badge_color": "#1D4ED8",
        "day_header_color": "#475569",
        "text_color": "#1E293B",
        "highlight_text_color": "#FFFFFF",
        "border_color": "#CBD5E1",
        "bg_color": "#FFFFFF",
    },
    "Warm Terracotta": {
        "header_color": "#9A3412",
        "badge_color": "#C2410C",
        "day_header_color": "#78716C",
        "text_color": "#1C1917",
        "highlight_text_color": "#FFFFFF",
        "border_color": "#E7E5E4",
        "bg_color": "#FFFFFF",
    },
    "Monochrome Black": {
        "header_color": "#000000",
        "badge_color": "#000000",
        "day_header_color": "#555555",
        "text_color": "#111111",
        "highlight_text_color": "#FFFFFF",
        "border_color": "#111111",
        "bg_color": "#FFFFFF",
    },
}


def format_puzzle_date(d: datetime.date, fmt_choice: str) -> str:
    """Format date consistently across all operating systems."""
    month_name = d.strftime("%B")
    month_abbr = d.strftime("%b")
    day = d.day
    day_pad = f"{d.day:02d}"
    month = d.month
    month_pad = f"{d.month:02d}"
    year = d.year
    weekday = d.strftime("%A")
    weekday_abbr = d.strftime("%a")

    if fmt_choice == "27-September":
        return f"{day}-{month_name}"
    elif fmt_choice == "27-september":
        return f"{day}-{month_name.lower()}"
    elif fmt_choice == "27-Sep-2026":
        return f"{day}-{month_abbr}-{year}"
    elif fmt_choice == "27-sept-2026":
        abbr_t = "sept" if d.month == 9 else month_abbr.lower()
        return f"{day}-{abbr_t}-{year}"
    elif fmt_choice == "9-27-2026":
        return f"{month}-{day}-{year}"
    elif fmt_choice == "09/27/2026":
        return f"{month_pad}/{day_pad}/{year}"
    elif fmt_choice == "September 27, 2026":
        return f"{month_name} {day}, {year}"
    elif fmt_choice == "Sunday, September 27":
        return f"{weekday}, {month_name} {day}"
    elif fmt_choice == "Sun, Sep 27, 2026":
        return f"{weekday_abbr}, {month_abbr} {day}, {year}"
    elif fmt_choice == "2026-09-27":
        return f"{year}-{month_pad}-{day_pad}"
    else:
        return f"{month_name} {day}, {year}"


def get_puzzle_date_info(
    puzzle_idx: int,
    start_date: datetime.date,
    progression: str = "daily",
    format_choice: str = "27-September",
) -> Dict[str, Any]:
    """Calculate date metadata for puzzle at 0-based index."""
    if progression == "monthly":
        total_months = (start_date.year * 12 + start_date.month - 1) + puzzle_idx
        y = total_months // 12
        m = total_months % 12 + 1
        d = datetime.date(y, m, 1)
        highlight_day = None
    else:
        d = start_date + datetime.timedelta(days=puzzle_idx)
        highlight_day = d.day

    return {
        "date": d,
        "date_str": format_puzzle_date(d, format_choice),
        "year": d.year,
        "month": d.month,
        "day": d.day,
        "highlight_day": highlight_day,
        "month_name": d.strftime("%B"),
        "month_abbr": d.strftime("%b"),
    }


def render_mini_month_calendar(
    year: int,
    month: int,
    highlight_day: Optional[int] = None,
    width: int = 420,
    height: int = 340,
    theme: str = "Modern Emerald",
    first_day_sunday: bool = True,
    show_card_border: bool = True,
) -> Image.Image:
    """Render a clean, modern mini month calendar card image with optional highlighted day."""
    thm = CALENDAR_THEMES.get(theme, CALENDAR_THEMES["Modern Emerald"])
    c_header = _hex_to_rgb(thm["header_color"])
    c_badge = _hex_to_rgb(thm["badge_color"])
    c_dh = _hex_to_rgb(thm["day_header_color"])
    c_text = _hex_to_rgb(thm["text_color"])
    c_htext = _hex_to_rgb(thm["highlight_text_color"])
    c_border = _hex_to_rgb(thm["border_color"])
    c_bg = _hex_to_rgb(thm["bg_color"])

    img = Image.new("RGB", (width, height), c_bg)
    draw = ImageDraw.Draw(img)

    # Optional card border
    if show_card_border:
        draw.rounded_rectangle([(3, 3), (width - 4, height - 4)], radius=14, outline=c_border, width=2, fill=c_bg)

    # Month title
    month_name = datetime.date(year, month, 1).strftime("%B").upper()
    title_text = f"{month_name} {year}"

    f_title = ImageFont.truetype(_font_path("DejaVu Sans Bold"), int(height * 0.088))
    f_dh = ImageFont.truetype(_font_path("DejaVu Sans Bold"), int(height * 0.065))
    f_num = ImageFont.truetype(_font_path("DejaVu Sans"), int(height * 0.070))
    f_num_bold = ImageFont.truetype(_font_path("DejaVu Sans Bold"), int(height * 0.072))

    # Header position
    top_header_y = int(height * 0.11)
    draw.text((width / 2.0, top_header_y), title_text, fill=c_header, font=f_title, anchor="mm")

    # Divider line
    div_y = int(height * 0.19)
    draw.line([(int(width * 0.08), div_y), (int(width * 0.92), div_y)], fill=c_border, width=1)

    # Day of week headers
    headers = ["S", "M", "T", "W", "T", "F", "S"] if first_day_sunday else ["M", "T", "W", "T", "F", "S", "S"]
    pad_x = width * 0.07
    avail_w = width - 2 * pad_x
    col_w = avail_w / 7.0

    dh_y = int(height * 0.26)
    for c_i, h_txt in enumerate(headers):
        cx = pad_x + c_i * col_w + col_w / 2.0
        draw.text((cx, dh_y), h_txt, fill=c_dh, font=f_dh, anchor="mm")

    # Calendar weeks
    cal_obj = calendar.Calendar(firstweekday=calendar.SUNDAY if first_day_sunday else calendar.MONDAY)
    weeks = cal_obj.monthdayscalendar(year, month)

    start_grid_y = int(height * 0.38)
    row_h = (height * 0.88 - start_grid_y) / max(5, len(weeks))

    for r_i, week in enumerate(weeks):
        for c_i, day_num in enumerate(week):
            if day_num == 0:
                continue

            cx = pad_x + c_i * col_w + col_w / 2.0
            cy = start_grid_y + r_i * row_h

            if highlight_day and day_num == highlight_day:
                badge_radius = min(col_w * 0.44, row_h * 0.44)
                draw.ellipse(
                    [(cx - badge_radius, cy - badge_radius), (cx + badge_radius, cy + badge_radius)],
                    fill=c_badge,
                )
                draw.text((cx, cy), str(day_num), fill=c_htext, font=f_num_bold, anchor="mm")
            else:
                draw.text((cx, cy), str(day_num), fill=c_text, font=f_num, anchor="mm")

    return img
