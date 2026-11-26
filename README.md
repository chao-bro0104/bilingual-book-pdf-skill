# bilingual-book-pdf

An Agent Skill for converting English books or long-form manuscripts (`.txt`, `.md`, or extracted text) into **publication-grade, print-ready facing-page English–Chinese bilingual PDFs**—with **original English on the left page** and **literary Chinese on the right page**, strictly synchronized paragraph-by-paragraph across every spread.

## Features

- **Physical Book Parity**: Page 1 is a minimalist recto (right-hand) Title Page; every spread thereafter places **Even pages on the left (English)** and **Odd pages on the right (Chinese)**.
- **Mirrored Binding Gutters**: `21mm` inside gutter, `15mm` outside fore-edge, `17mm` top/bottom (for A5), plus mirrored running headers and outer-corner page numbers.
- **Zero-Drift Spread Pagination & Adaptive Balance**: Measures rendered English and Chinese block heights directly in headless Chrome DOM before packing spreads, ensuring both pages start and end on the same paragraph with zero clipped lines, keep-with-next protection on headings and questions, and adaptive English line-height balancing when a facing Chinese page runs longer.
- **Dynamic Bilingual TOC & Bookmarks**: Two-pass measurement computes exact left/right start page numbers for every part, chapter, and appendix, plus embeds clickable PDF outline bookmarks.
- **Duplex Print Ready**: Automatically appends a blank final verso page if needed so the print PDF has an even page count.
- **Dual Output**:
  - `<slug>_Bilingual_Print.pdf` — Single-page A5 (`148×210mm`) or B5 (`176×250mm`) PDF ready for double-sided printing and binding.
  - `<slug>_Bilingual_SpreadPreview.pdf` — Vector-sharp 2-up spread preview (`Left EN | Right ZH`) for screen reading and visual QA.

## Structure

```text
bilingual-book-pdf/
├── SKILL.md                              # Main skill workflow instructions
├── references/
│   ├── schema_and_parser_guide.md        # book_structure.json schema & footnote/endnote cleaning
│   └── translation_style_guide.md        # Literary EN->ZH style guide & parallel subagent workflow
└── scripts/
    ├── validate_translations.py          # Coverage, type, CJK, and glossary validation CLI
    └── render_bilingual_book.py          # Two-pass Playwright + PyMuPDF book renderer CLI
```

## Prerequisites

- Python 3.9+
- Python packages: `playwright`, `pymupdf` (`fitz`)
- Google Chrome or Chromium installed locally (and Chinese serif fonts such as `Songti SC`, `STSong`, or `Noto Serif CJK SC`)

## Installation (Antigravity)

Clone this repository into your global Antigravity skills directory:

```bash
git clone https://github.com/chao-bro0104/bilingual-book-pdf-skill ~/.gemini/config/skills/bilingual-book-pdf
```

## Usage

In a new conversation, ask the agent with prompts such as:

- `用 bilingual-book-pdf 把这本英文书做成左英右中的可打印双语 PDF，先出一个 Demo 看看`
- `Convert this book into a print-ready facing-page English-Chinese bilingual PDF`

### Direct CLI Usage

```bash
# 1. Validate translations
python3 ~/.gemini/config/skills/bilingual-book-pdf/scripts/validate_translations.py \
  --book data/book_structure.json \
  --trans-dir data/translated

# 2. Render Print & SpreadPreview PDFs
python3 ~/.gemini/config/skills/bilingual-book-pdf/scripts/render_bilingual_book.py \
  --book data/book_structure.json \
  --trans-dir data/translated \
  --out-dir output \
  --size a5
```
