# Book JSON Schema & Parser Guide

## 1. Target `book_structure.json` Schema

The renderer script (`scripts/render_bilingual_book.py`) expects a single UTF-8 JSON file with `meta` and `sections`:

```json
{
  "meta": {
    "slug": "The_Book_of_Elon",
    "eyebrow": "Bilingual Facing-Page Edition",
    "title_en": "The Book of Elon",
    "subtitle_en": "A Guide to Purpose and Success",
    "title_zh": "埃隆之书",
    "subtitle_zh": "通往使命与成功指南",
    "footer_note": "Left Page: Original English · Right Page: Chinese Translation"
  },
  "sections": [ ... ]
}
```

### Section Types (`sections[]`)

1. **`epigraph_spread`** (occupies exactly 1 spread: Left EN, Right ZH):
   ```json
   {
     "id": "rutherford",
     "kind": "epigraph_spread",
     "en_quote": "“All of physics is either impossible or trivial...”",
     "en_author": "—Ernest Rutherford",
     "en_lead": "Now, here is Elon in his own words…",
     "zh_quote": "“物理学中的一切……”",
     "zh_author": "——欧内斯特·卢瑟福",
     "zh_lead": "现在，让我们聆听埃隆的亲口讲述……"
   }
   ```

2. **`part_opener`** (occupies 1 spread, creates a top-level TOC & PDF bookmark entry):
   ```json
   {
     "id": "part_i",
     "kind": "part_opener",
     "toc_en": "Part I: Pursue Purpose",
     "toc_zh": "第一部分：追寻使命",
     "en_label": "PART I",
     "en_title": "Pursue Purpose",
     "en_epigraph": "...",
     "zh_label": "第一部分",
     "zh_title": "追寻使命",
     "zh_epigraph": "..."
   }
   ```

3. **`flow`** (multi-spread paginated content starting on a fresh spread):
   ```json
   {
     "id": "ch_01",
     "kind": "flow",
     "toc_group_en": "Front Matter",
     "toc_group_zh": "卷首导读",
     "toc_en": "1. Living a Purposeful Life",
     "toc_zh": "第1章  活出有使命感的人生",
     "toc_level": 2,
     "hdr_en_main": "Part I · Pursue Purpose",
     "hdr_en_sub": "Living a Purposeful Life",
     "hdr_zh_main": "第一部分 · 追寻使命",
     "hdr_zh_sub": "活出有使命感的人生",
     "blocks": [ ... ]
   }
   ```
   - `toc_group_en` / `toc_group_zh` (optional): renders a small uppercase/bold group label in the TOC immediately before this entry (e.g., `Front Matter` before `Notes on This Book`, `Back Matter` before `Want More?`).
   - `toc_level`: `1` for top-level essays/appendices, `2` for chapters under a `part_opener`.

### Flow Block Types (`blocks[]`)
Every block in a `flow` section MUST have a unique `"uid"` (e.g. `"ch_01__0000"`) and `"type"`, plus `"en"` (and `"zh"` inline or in `data/translated/*.json`):

| `type` | Required Fields | Keep-with-next | Notes |
| :--- | :--- | :---: | :--- |
| `essay_title` | `en_kicker`, `zh_kicker`, `en`, optional `en_byline`/`zh_byline` | Yes | Front/back essays (*Notes*, *Foreword*, *Appreciation*) |
| `chapter_title` | `en_kicker`, `zh_kicker`, `en` | Yes | Numbered chapters (`CHAPTER 01` / `第一章`) or Bonus sections |
| `section_title` | `en` | Yes | Subheadings inside a chapter/essay |
| `highlight` | `en` (`str` or `list[str]`) | No | Left-border italic/bold pull-quote |
| `question` | `en` | Yes | Bold interview/dialogue prompt (`Q: ...` / `问：...`) |
| `para` | `en` | No | Standard body paragraph |
| `bullet` | `en` | No | Em-dash hanging-indent bullet |
| `numbered` | `num` (e.g. `"01"`), `en` | No | Tabular numbered maxim/item |
| `timeline` | `en` | No | Left-bordered timeline entry; prefix before `—`/`——` is bolded |
| `book_entry` | `en` | Yes | Bold recommended book title kept together with commentary |
| `signoff` | `en` (`list[str]`) | No | Author closing signature lines |

---

## 2. Cleaning Raw Book Text (Footnotes & Endnotes)

When parsing `.txt` or extracted ebook text:
1. **Locate the true body start**: Plain-text exports often contain the Table of Contents first, then repeat the first heading (`Notes on This Book` or `Chapter 1`) at the actual start. Always skip past the TOC occurrence.
2. **Strip endnote blocks before inline cleaning**:
   - Endnote blocks usually start with `^\d{1,4}\s+` followed by a quote or author name (`1 Elon Musk...`, `80 “Third Row...`).
   - Guard against stripping valid timeline years (`^(19|20)\d{2}\s*(\(age|\u2014)`).
3. **Strip inline footnote numbers safely**:
   - Strip digits immediately after sentence/quote/symbol punctuation before whitespace, `)`, or end-of-line:
     `re.sub(r"([.?!…\"”’,\u2665♥️])\d{1,4}(?=[\s\)]|$)", r"\1", s)`
   - Notice `,\d+` only triggers at whitespace/end, so `$1,000` and `86,400` are untouched.
   - Manually audit any remaining `[a-zA-Z]\d+` tokens at word boundaries (`re.finditer(r"([a-zA-Z]+\d+)(?=\s|$)", s)`): protect legitimate tokens (`CO2`, `H2O`, `CH4`, `O2`, `Zip2`, `H100s`, `Web2`, `MVac`) and strip author-attached footnotes (e.g., `—Ernest Rutherford1`, `Will and Ariel Durant1036`).
4. **Chunking for Translation**:
   - Pre-fill any blocks already translated (e.g., from an approved Demo).
   - Split remaining blocks into `data/chunks/chunk_01.json`..`chunk_NN.json` with ~75–85 blocks and ≤2,700 English words per chunk so parallel translation subagents finish reliably in one turn.
