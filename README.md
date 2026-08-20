# Word Search Studio

Word Search Studio is a standalone Streamlit interface extracted from the larger KDP Activity Studio workflow. It is intentionally limited to word-search production so it can be tested and uploaded independently later.

## Features

The interface uses a compact two-column workspace to reduce scrolling. It accepts either a themed CSV (`theme,word`), a simple CSV (`word`), or a pasted list of words. It supports easy, medium, and hard puzzle generation, configurable words per page, optional word-bank display, and word-bank columns from **1 through 5**. The preview is scaled to fit the available screen area and includes the theme/title, puzzle grid, and word bank together.

The Canva export produces an Excel workbook with editable `page`, `title`, and `word_1` through `word_N` columns, together with embedded `grid_image` PNGs. Solutions are generated separately in a `word_search_solutions.xlsx` workbook, with a selectable number of solution images per row/page from 1 through 5. A combined ZIP download contains the Canva workbook, solutions workbook, and all PNG assets.

## Run locally

From the repository root, install the requirements if needed and launch:

```powershell
streamlit run app.py
```

The tool uses the main studio’s proven raster grid renderer and Canva-compatible image embedding logic. It does not load the multi-activity book UI. The standalone folder also contains a bundled `engine`, `core`, and font set, so the folder can be deployed independently rather than depending on the full main studio repository.

## Public deployment

Deploy this directory as the application root. The Streamlit entry point is `app.py`, and the dependency file is `requirements.txt`. For Streamlit Community Cloud, upload this folder as a GitHub repository and select `app.py` as the main file. For a VPS, run `streamlit run app.py` from inside this folder or place it behind a reverse proxy such as Caddy.

The standalone package includes the puzzle engine, main-studio raster grid renderer, bundled fonts, CSV examples, AdSense placeholder support, and Windows launcher. Do not upload only `app.py`; include the complete folder so the fallback engine and fonts are available.

## CSV formats

The interface includes download buttons for both example formats and a collapsed, copyable prompt template for each input type. Puzzle generation retries with deterministic alternate seeds to reduce skipped words before showing a warning.

The themed format is:

```csv
theme,word
Ocean,SHARK
Ocean,WHALE
Farm,COW
```

The simple format is:

```csv
word
SHARK
WHALE
COW
```

In Canva, upload the Excel workbook to **Bulk Create**, map the title and word columns to text placeholders, and use the embedded image columns for the puzzle and solution artwork.

## Google AdSense banner

The app includes a 300 × 250 square ad slot beneath the export controls. Before configuration, it appears as a neutral placeholder. The live AdSense unit is enabled through the environment variables `GOOGLE_ADSENSE_CLIENT` and `GOOGLE_ADSENSE_SLOT`.

After the app is hosted on your own domain, create or connect the site in Google AdSense and wait for Google to review it. Google provides the publisher ID and ad-unit code from the AdSense dashboard.[1] Set the values before starting Streamlit:

```powershell
$env:GOOGLE_ADSENSE_CLIENT = "ca-pub-XXXXXXXXXXXXXXXX"
$env:GOOGLE_ADSENSE_SLOT = "1234567890"
streamlit run app.py
```

For the Windows launcher, add these two `set` lines near the top of `run_word_search.bat`:

```bat
set "GOOGLE_ADSENSE_CLIENT=ca-pub-XXXXXXXXXXXXXXXX"
set "GOOGLE_ADSENSE_SLOT=1234567890"
```

Copy `ads.txt.example` to `ads.txt`, replace the placeholder publisher ID, and serve it at the root of the hosted domain. Google documents `ads.txt` as the place to declare authorized sellers for the publisher account.[2] The site must be hosted and approved before expecting real ads; local development generally shows only the placeholder or an empty ad unit.

[1]: https://support.google.com/adsense/answer/9274019 "Get and copy AdSense code"
[2]: https://support.google.com/adsense/answer/12171612 "Ads.txt guide"
