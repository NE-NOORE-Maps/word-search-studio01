# KDP Activity Studio · Word Search & Sudoku

KDP Activity Studio is a complete publishing platform for Amazon KDP, Etsy, and Canva creators. It produces print-ready interior PDF books, Canva Bulk Create workbooks, and high-resolution raster image bundles for both **Word Search** and **Sudoku** puzzles.

## Navigation & Architecture

A clean top navigation bar allows 1-click switching between:
- 🔤 **Word Search Studio**
- 🔢 **Sudoku Studio**

Both studios feature a compact, ordered two-column layout:
- **Left Column**: Step-by-step configuration cards, dimensions, audience presets, and visual styling.
- **Right Column**: Live interactive preview with instant Puzzle vs Solution mode, metrics strip, and export options.

---

## 🔢 Sudoku Studio Features

### 1. Game Types & Variants
- **Classic 9×9**: Standard 3×3 box Sudoku, the gold standard for adult puzzle books.
- **Kids Mini 4×4**: 2×2 subgrids, numbers 1–4, designed for early learners and children's activity books.
- **Junior 6×6**: 2×3 subgrids, numbers 1–6, ideal for middle-grade kids and beginners.
- **Wordoku (Letter 9×9)**: Uses 9 distinct letters from a target anagram keyword (e.g. `PUBLISHER`, `CHEMISTRY`, `ALGORITHM`) with custom word support.
- **Sudoku X (Diagonal)**: 9×9 board where both main diagonals must also contain unique numbers 1–9.
- **Windoku (Hyper Sudoku)**: 9×9 board with four 3×3 shaded internal windows that must each contain unique numbers 1–9.

### 2. Difficulty Levels & Symmetry
- **Very Easy**, **Easy**, **Medium**, **Hard**, and **Expert / Evil**
- **180° Rotational Symmetry**: Generates authentic publisher-grade symmetric clue distributions.
- **Custom Clue Count**: Optional manual slider to pinpoint the exact number of initial clues.
- **100% Unique Solutions Guaranteed**: Verified with fast MRV backtracking solver.

### 3. Audience Presets & Visual Customization
- **Audience Presets**:
  - `👔 Adult Classic`: Crisp black outer borders, 1.0mm 3×3 box lines, 0.4mm inner lines, balanced 64% font.
  - `👓 Senior / Large Print`: Extra-bold 2.0mm borders, 82% giant font scale for vision comfort.
  - `🏁 Checkerboard / Shaded Blocks`: Alternating soft shaded 3×3 blocks for easy region tracking.
  - `🎈 Kids Fun (Rounded Tiles)`: Friendly rounded cell cards with large playful digits.
  - `📐 Modern Minimalist`: Understated hairline borders with contemporary neutral tones.
  - `⚙️ Custom`: Full manual sliders for borders, cell lines, shading tones, fonts, and colors.
- **Solution Marking Modes**:
  - Distinct solution color (e.g. Royal Blue, Emerald Green, Terracotta Red)
  - Circled solution digits
  - Uniform black

### 4. Export Capabilities
- **Canva Bulk Create Excel**: Ready for Canva Bulk Create with embedded image thumbnails and text metadata (`page`, `puzzle_num`, `title`, `difficulty`, `clues_count`).
- **Solutions Excel**: Multi-solution workbook with embedded thumbnails (1, 2, 4, 6, or 9 per page).
- **Print-Ready KDP Interior PDF Book**: Multi-page PDF book formatted for standard KDP trim sizes (8.5" × 11" Letter or 6" × 9" Pocket) with page numbers, titles, difficulty badges, and a dedicated multi-solution section.
- **Complete ZIP Bundle**: Contains Canva Excel, Solutions Excel, KDP PDF book, and all 300 DPI PNG assets.

---

## 🔤 Word Search Studio Features

- **Multilingual Support**: English, German (`Ä, Ö, Ü, ß -> SS`), Spanish (`Ñ`), French, and Italian.
- **Word Input**: Themed CSV (`theme,word`), simple CSV (`word`), or pasted word list.
- **Grid Dimensions**: Standard 10×10, 12×10, 12×12, 13×13, 14×14, 15×15, 16×16, Auto, or Custom Rows × Cols.
- **Audience Presets**: Kids Fun, Adult Classic, Senior / Large Print, Minimalist, and Custom.
- **Export**: Canva Bulk Create workbook, Solutions workbook, and combined ZIP download.

---

## Run Locally

```powershell
pip install -r requirements.txt
streamlit run app.py
```

Or run using the Windows launcher:
```powershell
.\run_word_search.bat
```

## Running Tests

Run the complete automated test suite:
```powershell
python smoke_test.py
```
