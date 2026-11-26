---
name: bilingual-book-pdf
description: >-
  Convert English books or long-form manuscripts (.txt, .md, or extracted text)
  into publication-grade, print-ready facing-page English-Chinese bilingual PDFs
  (left page original English, right page literary Chinese, strict spread-level
  paragraph alignment, mirrored binding gutters, bilingual TOC, and 2-up spread
  preview). Use whenever the user asks to translate and typeset an English book
  into a printable bilingual PDF, facing-page edition, or side-by-side book.
---

# Bilingual Facing-Page Book PDF Pipeline

This skill produces two synchronized PDFs from an English book:
1. **`<slug>_Bilingual_Print.pdf`**: Print-ready single-page PDF (`A5` default, `148×210mm`, or `B5`, `176×250mm`) with physical book parity (Page 1 = Title Page on right; Even = Left English; Odd = Right Chinese; mirrored binding gutters; PDF bookmarks; even duplex total pages).
2. **`<slug>_Bilingual_SpreadPreview.pdf`**: Vector-sharp 2-up spread preview (`Left EN | Right ZH`) for screen reading and visual QA.

## Workflow

### Step 1: Confirm Scope & Demo Strategy
Before parsing or translating a full book, confirm with the user (or apply their explicit instructions):
- **Book Title**: Exact English title/subtitle and Chinese title/subtitle for the Title Page.
- **Scope**: Which front matter (e.g., *Notes on This Book*, *Foreword*, *Preface*), main parts/chapters, and back matter/appendices to keep vs. strip (default: strip copyright, ISBN, publisher promos, dedication, raw plain-text TOC, and endnote/footnote numbers).
- **Trim Size & Style**: Default `a5` (`148×210mm`, ideal for portable 32开 paperback); optional `b5` (`176×250mm`).
- **Demo First (Recommended for full books)**: Generate a 15–30 page Demo (Title + Front Matter + Chapter 1 opening) to verify translation tone, margins, and typography before running full-book parallel translation.

### Step 2: Parse & Clean into `book_structure.json`
Write a book-specific parser script following [schema_and_parser_guide.md](./references/schema_and_parser_guide.md) to:
1. Strip endnote blocks and inline footnote numbers safely (verify `$1,000`, `CO2`, years, and model numbers are untouched).
2. Classify structural blocks (`essay_title`, `chapter_title`, `section_title`, `highlight`, `question`, `para`, `bullet`, `numbered`, `timeline`, `book_entry`, `signoff`) plus `epigraph_spread` and `part_opener` dividers.
3. Save `data/book_structure.json` and partition untranslated blocks into balanced chunks (~75–85 blocks, ≤2,700 words each) in `data/chunks/chunk_XX.json`.

### Step 3: Parallel Literary Translation
Follow [translation_style_guide.md](./references/translation_style_guide.md):
1. Build a book-specific terminology glossary (names, technical concepts, products, recurring phrases).
2. Define a dedicated custom subagent via `define_subagent(Name="book_translator", EnableWriteTools=True, ...)` embedding the style guide and glossary.
   - **Important**: Do **not** use `run_workflow` with `type_name="self"` for chunk translation if running in plan-execute mode (child `self` agents can deadlock on inherited plan-review hooks). Always use a dedicated custom subagent via `define_subagent` + `invoke_subagent`.
3. Launch waves of 5–7 parallel `invoke_subagent` calls writing `data/translated/chunk_XX_zh.json`, ending the turn to let reactive notifications wake you.

### Step 4: Validate 100% Translation Coverage
Run the validation CLI:
```bash
python3 ~/.gemini/config/skills/bilingual-book-pdf/scripts/validate_translations.py \
  --book data/book_structure.json \
  --trans-dir data/translated
```
Confirm exit code `0` (`Missing: 0`, `Bad type/list len: 0`, `No CJK chars: 0`, `Questions not starting with 问：: 0`). Fix any flagged blocks before rendering.

### Step 5: Render Print & Spread Preview PDFs
Run the Playwright + PyMuPDF rendering engine:
```bash
python3 ~/.gemini/config/skills/bilingual-book-pdf/scripts/render_bilingual_book.py \
  --book data/book_structure.json \
  --trans-dir data/translated \
  --out-dir <output_dir> \
  --size a5
```
Options:
- `--size a5|b5` (default `a5`)
- `--no-toc` (omit Bilingual Table of Contents, e.g., for short Demos)
- `--chrome /path/to/chrome` (auto-detects Google Chrome on macOS by default)

The script runs two passes: Pass 1 measures every English and Chinese block in Chrome DOM to compute synchronized Left/Right spreads and exact TOC page numbers; Pass 2 renders batched PDFs, asserts **0 DOM overflows**, merges via PyMuPDF, embeds PDF bookmarks, appends a blank final verso page if needed for duplex printing, builds `<slug>_Bilingual_SpreadPreview.pdf`, and saves representative spread PNGs in `<output_dir>/preview_samples/`.

### Step 6: Visual QA & Delivery
1. Inspect PNGs in `<output_dir>/preview_samples/` with `read_file` (Title page, TOC spreads, front matter, chapter openers, special lists/timelines, back matter). Verify balanced EN/ZH heights, crisp Chinese punctuation, and accurate TOC page numbers.
2. Deliver clickable links to both `<slug>_Bilingual_Print.pdf` and `<slug>_Bilingual_SpreadPreview.pdf`, plus duplex printing tips (size, 100% scale, long-edge binding, 80–100g off-white paper).
