#!/usr/bin/env python3
"""Render print-ready bilingual facing-page PDF and 2-up spread preview from book_structure.json."""

from __future__ import annotations

import argparse
import html
import json
import shutil
from pathlib import Path
import fitz  # PyMuPDF
from playwright.sync_api import sync_playwright

PAGE_SPECS = {
    "a5": {
        "w_mm": 148.0,
        "h_mm": 210.0,
        "pad_top_mm": 17.0,
        "pad_bot_mm": 17.0,
        "gutter_mm": 21.0,
        "outer_mm": 15.0,
        "body_h_mm": 155.0,
        "en_pt": 9.5,
        "zh_pt": 9.75,
        "en_lh_base": 1.64,
        "en_lh_max": 1.86,
        "en_pb_mm": 2.65,
    },
    "b5": {
        "w_mm": 176.0,
        "h_mm": 250.0,
        "pad_top_mm": 20.0,
        "pad_bot_mm": 20.0,
        "gutter_mm": 23.0,
        "outer_mm": 17.0,
        "body_h_mm": 188.0,
        "en_pt": 10.15,
        "zh_pt": 10.4,
        "en_lh_base": 1.64,
        "en_lh_max": 1.86,
        "en_pb_mm": 2.85,
    },
}


def find_chrome(explicit: str | None) -> str:
    if explicit and Path(explicit).exists():
        return explicit
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
    ]
    for c in candidates:
        if c and Path(c).exists():
            return str(c)
    raise FileNotFoundError("Google Chrome / Chromium not found. Pass --chrome <path>.")


def build_css(spec: dict) -> str:
    w_mm = spec["w_mm"]
    h_mm = spec["h_mm"]
    pt = spec["pad_top_mm"]
    pb = spec["pad_bot_mm"]
    gut = spec["gutter_mm"]
    out = spec["outer_mm"]
    col_w = w_mm - gut - out
    body_h = spec["body_h_mm"]
    en_pt = spec["en_pt"]
    zh_pt = spec["zh_pt"]

    return f"""
@page {{
  size: {w_mm}mm {h_mm}mm;
  margin: 0;
}}
* {{
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}}
html, body {{
  background: #ffffff;
  color: #1a1a1a;
  -webkit-font-smoothing: antialiased;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}}
.page {{
  width: {w_mm}mm;
  height: {h_mm}mm;
  position: relative;
  overflow: hidden;
  background: #ffffff;
  display: flex;
  flex-direction: column;
  page-break-after: always;
  break-after: page;
}}
.page:last-child {{
  page-break-after: auto;
  break-after: auto;
}}
.page-even {{
  padding: {pt}mm {gut}mm {pb}mm {out}mm;
}}
.page-odd {{
  padding: {pt}mm {out}mm {pb}mm {gut}mm;
}}
.running-header {{
  height: 7mm;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  padding-bottom: 2.2mm;
  margin-bottom: 4.5mm;
  border-bottom: 0.4pt solid #d4dbe3;
  font-family: 'Avenir Next', 'PingFang SC', 'Helvetica Neue', sans-serif;
  font-size: 6.5pt;
  letter-spacing: 0.08em;
  color: #64748b;
  flex-shrink: 0;
}}
.page-even .running-header {{
  flex-direction: row;
  text-transform: uppercase;
}}
.page-odd .running-header {{
  flex-direction: row-reverse;
  letter-spacing: 0.07em;
}}
.hdr-sub {{
  color: #94a3b8;
  font-weight: 400;
  max-width: {col_w * 0.50:.1f}mm;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
.hdr-main {{
  color: #475569;
  font-weight: 500;
  max-width: {col_w * 0.46:.1f}mm;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
.page-body {{
  height: {body_h}mm;
  overflow: hidden;
  flex-shrink: 0;
}}
.running-footer {{
  height: 9.5mm;
  display: flex;
  align-items: flex-end;
  font-family: 'Avenir Next', 'PingFang SC', sans-serif;
  font-size: 7.5pt;
  color: #64748b;
  letter-spacing: 0.06em;
  flex-shrink: 0;
}}
.page-even .running-footer {{ justify-content: flex-start; }}
.page-odd .running-footer {{ justify-content: flex-end; }}

.col-en {{
  --en-lh: {spec['en_lh_base']};
  --en-pb: {spec['en_pb_mm']}mm;
  width: {col_w}mm;
  font-family: 'Charter', 'Iowan Old Style', 'Georgia', serif;
  font-size: {en_pt}pt;
  line-height: var(--en-lh);
  color: #1c1e21;
  text-align: justify;
  hyphens: auto;
  -webkit-hyphens: auto;
}}
.col-zh {{
  width: {col_w}mm;
  font-family: 'Songti SC', 'STSong', 'Noto Serif CJK SC', serif;
  font-size: {zh_pt}pt;
  line-height: 1.78;
  color: #1c1e21;
  text-align: justify;
  line-break: strict;
  word-break: normal;
}}
.blk {{ display: block; }}

.blk-chapter-en, .blk-essay-en {{
  margin-top: 1mm;
  margin-bottom: 5.2mm;
  padding-bottom: 3.3mm;
  border-bottom: 0.75pt solid #1e293b;
}}
.blk-chapter-en .kicker, .blk-essay-en .kicker {{
  font-family: 'Avenir Next', sans-serif;
  font-size: 7pt;
  font-weight: 600;
  letter-spacing: 0.16em;
  color: #64748b;
  margin-bottom: 1.8mm;
}}
.blk-chapter-en h1, .blk-essay-en h1 {{
  font-family: 'Baskerville', 'Charter', Georgia, serif;
  font-size: 17.5pt;
  font-weight: 600;
  line-height: 1.22;
  color: #0f172a;
  text-align: left;
  letter-spacing: -0.01em;
}}
.blk-essay-en .byline {{
  margin-top: 2mm;
  font-family: 'Charter', Georgia, serif;
  font-style: italic;
  font-size: 9.5pt;
  color: #475569;
  text-align: left;
}}
.blk-chapter-zh, .blk-essay-zh {{
  margin-top: 1mm;
  margin-bottom: 5.2mm;
  padding-bottom: 3.3mm;
  border-bottom: 0.75pt solid #1e293b;
}}
.blk-chapter-zh .kicker, .blk-essay-zh .kicker {{
  font-family: 'PingFang SC', 'Avenir Next', sans-serif;
  font-size: 7.2pt;
  font-weight: 500;
  letter-spacing: 0.18em;
  color: #64748b;
  margin-bottom: 1.8mm;
}}
.blk-chapter-zh h1, .blk-essay-zh h1 {{
  font-family: 'Songti SC', 'STSong', 'Noto Serif CJK SC', serif;
  font-size: 17pt;
  font-weight: 700;
  line-height: 1.28;
  color: #0f172a;
  text-align: left;
  letter-spacing: 0.02em;
}}
.blk-essay-zh .byline {{
  margin-top: 2mm;
  font-family: 'Songti SC', 'STSong', 'Noto Serif CJK SC', serif;
  font-size: 9.6pt;
  color: #475569;
  text-align: left;
}}

.blk-section-en {{
  margin-top: 5mm;
  margin-bottom: 2.5mm;
}}
.blk-section-en::before {{
  content: "";
  display: block;
  width: 7mm;
  height: 1pt;
  background: #334155;
  margin-bottom: 1.7mm;
}}
.blk-section-en h2 {{
  font-family: 'Baskerville', 'Charter', Georgia, serif;
  font-size: 11.8pt;
  font-weight: 700;
  line-height: 1.3;
  color: #0f172a;
  text-align: left;
}}
.blk-section-zh {{
  margin-top: 5mm;
  margin-bottom: 2.5mm;
}}
.blk-section-zh::before {{
  content: "";
  display: block;
  width: 7mm;
  height: 1pt;
  background: #334155;
  margin-bottom: 1.7mm;
}}
.blk-section-zh h2 {{
  font-family: 'Songti SC', 'STSong', 'Noto Serif CJK SC', serif;
  font-size: 11.6pt;
  font-weight: 700;
  line-height: 1.35;
  color: #0f172a;
  text-align: left;
  letter-spacing: 0.03em;
}}

.blk-para {{ margin-bottom: 2.6mm; }}
.col-en .blk-para {{ margin-bottom: var(--en-pb); }}
.blk-bullet {{
  position: relative;
  padding-left: 4.5mm;
  margin-bottom: 2.1mm;
}}
.blk-bullet::before {{
  content: "—";
  position: absolute;
  left: 0;
  top: 0;
  color: #64748b;
  font-weight: 500;
}}
.blk-numbered-en, .blk-numbered-zh {{
  display: flex;
  align-items: baseline;
  gap: 2.8mm;
  margin-bottom: 2.3mm;
  text-align: left;
}}
.num-badge {{
  font-family: 'Avenir Next', sans-serif;
  font-size: 7.4pt;
  font-weight: 600;
  color: #64748b;
  min-width: 5.2mm;
  letter-spacing: 0.04em;
  flex-shrink: 0;
}}
.blk-timeline {{
  margin-bottom: 2.4mm;
  padding-left: 3mm;
  border-left: 0.9pt solid #cbd5e1;
  text-align: left;
}}
.tl-head {{ font-weight: 700; color: #0f172a; }}
.blk-book-en {{
  margin-top: 3mm;
  margin-bottom: 1.1mm;
  font-family: 'Charter', Georgia, serif;
  font-weight: 700;
  font-size: {en_pt + 0.1}pt;
  line-height: 1.44;
  color: #0f172a;
  text-align: left;
}}
.blk-book-zh {{
  margin-top: 3mm;
  margin-bottom: 1.1mm;
  font-family: 'Songti SC', 'STSong', 'Noto Serif CJK SC', serif;
  font-weight: 700;
  font-size: {zh_pt}pt;
  line-height: 1.62;
  color: #0f172a;
  text-align: left;
}}
.blk-question-en {{
  margin-top: 3.3mm;
  margin-bottom: 1.5mm;
  font-family: 'Charter', Georgia, serif;
  font-weight: 700;
  font-size: {en_pt + 0.1}pt;
  line-height: 1.48;
  color: #0f172a;
  text-align: left;
}}
.blk-question-zh {{
  margin-top: 3.3mm;
  margin-bottom: 1.5mm;
  font-family: 'Songti SC', 'STSong', 'Noto Serif CJK SC', serif;
  font-weight: 700;
  font-size: {zh_pt}pt;
  line-height: 1.65;
  color: #0f172a;
  text-align: left;
}}
.blk-highlight-en {{
  margin-top: 2.8mm;
  margin-bottom: 3.3mm;
  padding: 1.8mm 0 1.8mm 3.6mm;
  border-left: 1.6pt solid #2c3e50;
  font-family: 'Charter', Georgia, serif;
  font-style: italic;
  font-size: {en_pt + 0.2}pt;
  line-height: calc(var(--en-lh) - 0.06);
  color: #0f172a;
  text-align: left;
}}
.blk-highlight-en .hl-line + .hl-line {{ margin-top: 1.1mm; }}
.blk-highlight-zh {{
  margin-top: 2.8mm;
  margin-bottom: 3.3mm;
  padding: 1.8mm 0 1.8mm 3.6mm;
  border-left: 1.6pt solid #2c3e50;
  font-family: 'Songti SC', 'STSong', 'Noto Serif CJK SC', serif;
  font-weight: 600;
  font-size: {zh_pt + 0.05}pt;
  line-height: 1.72;
  color: #0f172a;
  text-align: left;
}}
.blk-highlight-zh .hl-line + .hl-line {{ margin-top: 1.1mm; }}
.blk-signoff-en {{
  margin-top: 4mm;
  font-family: 'Charter', Georgia, serif;
  font-style: italic;
  font-size: {en_pt + 0.25}pt;
  line-height: 1.6;
  color: #1e293b;
  text-align: left;
}}
.blk-signoff-zh {{
  margin-top: 4mm;
  font-family: 'Songti SC', 'STSong', 'Noto Serif CJK SC', serif;
  font-weight: 600;
  font-size: {zh_pt + 0.05}pt;
  line-height: 1.8;
  color: #1e293b;
  text-align: left;
}}
.page-body > .blk:first-child {{ margin-top: 0; }}
.page-body > .blk:last-child {{ margin-bottom: 0; }}

/* Title Page */
.title-page {{ justify-content: center; align-items: flex-start; }}
.title-box {{ width: 100%; padding-top: 6mm; padding-bottom: 10mm; }}
.title-eyebrow {{
  font-family: 'Avenir Next', 'PingFang SC', sans-serif;
  font-size: 7.5pt;
  letter-spacing: 0.22em;
  color: #64748b;
  text-transform: uppercase;
  margin-bottom: 7mm;
}}
.title-rule-top {{
  width: 16mm;
  height: 1.2pt;
  background: #1e293b;
  margin-bottom: 7mm;
}}
.title-en {{
  font-family: 'Baskerville', 'Charter', Georgia, serif;
  font-size: 24pt;
  font-weight: 600;
  line-height: 1.16;
  color: #0f172a;
  letter-spacing: -0.01em;
  margin-bottom: 3.5mm;
}}
.title-sub-en {{
  font-family: 'Charter', Georgia, serif;
  font-style: italic;
  font-size: 10.8pt;
  line-height: 1.45;
  color: #475569;
  margin-bottom: 11mm;
}}
.title-zh {{
  font-family: 'Songti SC', 'STSong', 'Noto Serif CJK SC', serif;
  font-size: 21pt;
  font-weight: 700;
  line-height: 1.3;
  color: #0f172a;
  letter-spacing: 0.08em;
  margin-bottom: 2.5mm;
}}
.title-sub-zh {{
  font-family: 'Songti SC', 'STSong', 'Noto Serif CJK SC', serif;
  font-size: 10.4pt;
  line-height: 1.5;
  color: #475569;
  letter-spacing: 0.06em;
}}
.title-divider {{
  width: 100%;
  height: 0.5pt;
  background: #cbd5e1;
  margin: 12mm 0 7mm 0;
}}
.title-footer-note {{
  position: absolute;
  bottom: 18mm;
  left: {gut}mm;
  right: {out}mm;
  font-family: 'Avenir Next', 'PingFang SC', sans-serif;
  font-size: 7pt;
  letter-spacing: 0.14em;
  color: #94a3b8;
  text-transform: uppercase;
}}

/* TOC */
.toc-title-en {{
  font-family: 'Baskerville', 'Charter', Georgia, serif;
  font-size: 16pt;
  font-weight: 600;
  color: #0f172a;
  padding-bottom: 2.5mm;
  margin-bottom: 4mm;
  border-bottom: 0.75pt solid #1e293b;
}}
.toc-title-zh {{
  font-family: 'Songti SC', 'STSong', 'Noto Serif CJK SC', serif;
  font-size: 15.5pt;
  font-weight: 700;
  color: #0f172a;
  padding-bottom: 2.5mm;
  margin-bottom: 4mm;
  border-bottom: 0.75pt solid #1e293b;
  letter-spacing: 0.12em;
}}
.toc-cont {{
  opacity: 0.45;
  font-size: 11.8pt;
}}
.toc-group-en {{
  font-family: 'Avenir Next', sans-serif;
  font-size: 7.2pt;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #1e293b;
  margin-top: 3.4mm;
  margin-bottom: 1.2mm;
}}
.toc-group-zh {{
  font-family: 'PingFang SC', 'Songti SC', sans-serif;
  font-size: 7.5pt;
  font-weight: 600;
  letter-spacing: 0.1em;
  color: #1e293b;
  margin-top: 3.4mm;
  margin-bottom: 1.2mm;
}}
.toc-row {{
  display: flex;
  align-items: baseline;
  font-size: 8.6pt;
  line-height: 1.55;
  color: #334155;
}}
.toc-row.toc-part-row {{
  font-weight: 600;
  color: #0f172a;
  margin-top: 3mm;
  margin-bottom: 0.8mm;
}}
.toc-row.toc-child {{ padding-left: 3.5mm; }}
.toc-dots {{
  flex: 1;
  border-bottom: 0.5pt dotted #cbd5e1;
  margin: 0 2mm;
  min-width: 6mm;
}}
.toc-pg {{
  font-family: 'Avenir Next', sans-serif;
  font-size: 7.8pt;
  color: #64748b;
  font-variant-numeric: tabular-nums;
}}

/* Part / Epigraph Openers */
.part-page {{ justify-content: space-between; }}
.part-center {{ margin-top: 30mm; }}
.part-label-en {{
  font-family: 'Avenir Next', sans-serif;
  font-size: 8pt;
  font-weight: 600;
  letter-spacing: 0.24em;
  color: #64748b;
  margin-bottom: 4mm;
}}
.part-title-en {{
  font-family: 'Baskerville', 'Charter', Georgia, serif;
  font-size: 23pt;
  font-weight: 600;
  line-height: 1.2;
  color: #0f172a;
  margin-bottom: 7mm;
}}
.part-rule {{
  width: 14mm;
  height: 1pt;
  background: #1e293b;
  margin-bottom: 9mm;
}}
.part-epigraph-en {{
  font-family: 'Charter', Georgia, serif;
  font-style: italic;
  font-size: 10.3pt;
  line-height: 1.62;
  color: #334155;
  max-width: {col_w * 0.88:.1f}mm;
  white-space: pre-line;
}}
.part-author-en {{
  margin-top: 4mm;
  font-family: 'Avenir Next', sans-serif;
  font-size: 8.2pt;
  letter-spacing: 0.08em;
  color: #64748b;
}}
.part-lead-en {{
  margin-top: 14mm;
  padding-top: 6mm;
  border-top: 0.4pt solid #cbd5e1;
  font-family: 'Charter', Georgia, serif;
  font-style: italic;
  font-size: 10.5pt;
  color: #0f172a;
  max-width: {col_w * 0.88:.1f}mm;
}}
.part-label-zh {{
  font-family: 'PingFang SC', sans-serif;
  font-size: 8.5pt;
  font-weight: 500;
  letter-spacing: 0.28em;
  color: #64748b;
  margin-bottom: 4mm;
}}
.part-title-zh {{
  font-family: 'Songti SC', 'STSong', 'Noto Serif CJK SC', serif;
  font-size: 22pt;
  font-weight: 700;
  line-height: 1.3;
  color: #0f172a;
  letter-spacing: 0.08em;
  margin-bottom: 7mm;
}}
.part-epigraph-zh {{
  font-family: 'Songti SC', 'STSong', 'Noto Serif CJK SC', serif;
  font-size: 10.5pt;
  line-height: 1.82;
  color: #334155;
  max-width: {col_w * 0.88:.1f}mm;
  white-space: pre-line;
}}
.part-author-zh {{
  margin-top: 4mm;
  font-family: 'Songti SC', 'STSong', 'Noto Serif CJK SC', serif;
  font-size: 9pt;
  letter-spacing: 0.08em;
  color: #64748b;
}}
.part-lead-zh {{
  margin-top: 14mm;
  padding-top: 6mm;
  border-top: 0.4pt solid #cbd5e1;
  font-family: 'Songti SC', 'STSong', 'Noto Serif CJK SC', serif;
  font-size: 10.5pt;
  color: #0f172a;
  max-width: {col_w * 0.88:.1f}mm;
}}
"""


def load_book_and_translations(book_path: Path, trans_dir: Path | None) -> tuple[dict, list[dict]]:
    raw = json.loads(book_path.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        meta = raw["meta"]
        sections = raw["sections"]
    else:
        meta = {
            "slug": book_path.stem,
            "eyebrow": "Bilingual Facing-Page Edition",
            "title_en": book_path.stem.replace("_", " "),
            "subtitle_en": "",
            "title_zh": book_path.stem.replace("_", " "),
            "subtitle_zh": "",
            "footer_note": "Left Page: Original English · Right Page: Chinese Translation",
        }
        sections = raw

    trans_map: dict[str, str | list[str]] = {}
    if trans_dir and trans_dir.exists():
        for tf in sorted(trans_dir.glob("*.json")):
            part = json.loads(tf.read_text(encoding="utf-8"))
            if isinstance(part, dict):
                trans_map.update(part)

    missing: list[str] = []
    for sec in sections:
        if sec.get("kind") != "flow":
            continue
        for blk in sec["blocks"]:
            uid = blk["uid"]
            if blk.get("zh") is None:
                if uid in trans_map:
                    blk["zh"] = trans_map[uid]
                else:
                    missing.append(uid)
            if blk.get("en_byline") and not blk.get("zh_byline"):
                b_uid = f"{uid}__byline"
                if b_uid in trans_map:
                    blk["zh_byline"] = trans_map[b_uid]

    if missing:
        raise RuntimeError(f"Missing translations for {len(missing)} blocks: {missing[:10]}")
    return meta, sections


def format_timeline_html(text: str, lang: str) -> str:
    if lang == "en" and "—" in text:
        head, tail = text.split("—", 1)
        return f'<span class="tl-head">{html.escape(head)}—</span>{html.escape(tail)}'
    if lang == "zh" and "——" in text:
        head, tail = text.split("——", 1)
        return f'<span class="tl-head">{html.escape(head)}——</span>{html.escape(tail)}'
    if lang == "zh" and "—" in text:
        head, tail = text.split("—", 1)
        return f'<span class="tl-head">{html.escape(head)}—</span>{html.escape(tail)}'
    return html.escape(text)


def render_block_html(block: dict, lang: str) -> str:
    btype = block["type"]
    uid = block["uid"]
    if btype in ("chapter_title", "essay_title"):
        cls = "chapter" if btype == "chapter_title" else "essay"
        kicker = html.escape(block.get(f"{lang}_kicker", ""))
        title = html.escape(block[lang])
        byline_key = f"{lang}_byline"
        byline_html = (
            f'<div class="byline">{html.escape(block[byline_key])}</div>'
            if block.get(byline_key)
            else ""
        )
        kicker_html = f'<div class="kicker">{kicker}</div>' if kicker else ""
        return (
            f'<div class="blk blk-{cls}-{lang}" data-uid="{uid}">'
            f"{kicker_html}<h1>{title}</h1>{byline_html}</div>"
        )
    if btype == "section_title":
        return f'<div class="blk blk-section-{lang}" data-uid="{uid}"><h2>{html.escape(block[lang])}</h2></div>'
    if btype == "highlight":
        content = block[lang]
        if isinstance(content, list):
            lines = "".join(f'<div class="hl-line">{html.escape(line)}</div>' for line in content)
        else:
            lines = f'<div class="hl-line">{html.escape(content)}</div>'
        return f'<div class="blk blk-highlight-{lang}" data-uid="{uid}">{lines}</div>'
    if btype == "question":
        return f'<div class="blk blk-question-{lang}" data-uid="{uid}">{html.escape(block[lang])}</div>'
    if btype == "book_entry":
        return f'<div class="blk blk-book-{lang}" data-uid="{uid}">{html.escape(block[lang])}</div>'
    if btype == "bullet":
        return f'<p class="blk blk-bullet" data-uid="{uid}">{html.escape(block[lang])}</p>'
    if btype == "numbered":
        return (
            f'<div class="blk blk-numbered-{lang}" data-uid="{uid}">'
            f'<span class="num-badge">{html.escape(block["num"])}</span>'
            f'<span>{html.escape(block[lang])}</span></div>'
        )
    if btype == "timeline":
        return f'<p class="blk blk-timeline" data-uid="{uid}">{format_timeline_html(block[lang], lang)}</p>'
    if btype == "signoff":
        lines = "".join(f"<div>{html.escape(line)}</div>" for line in block[lang])
        return f'<div class="blk blk-signoff-{lang}" data-uid="{uid}">{lines}</div>'
    if btype == "para":
        return f'<p class="blk blk-para" data-uid="{uid}">{html.escape(block[lang])}</p>'
    raise ValueError(f"Unknown block type: {btype}")


def build_measure_html(sections: list[dict], css: str) -> str:
    en_parts: list[str] = []
    zh_parts: list[str] = []
    for sec in sections:
        if sec.get("kind") != "flow":
            continue
        for blk in sec["blocks"]:
            en_parts.append(render_block_html(blk, "en"))
            zh_parts.append(render_block_html(blk, "zh"))
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><style>
{css}
.measure-stage {{ display: flex; gap: 20mm; padding: 10mm; background: #fff; }}
.measure-box {{ height: var(--body-h, 155mm); border: 1px solid red; }}
</style></head>
<body>
  <div class="measure-stage">
    <div id="measure-box" class="measure-box"></div>
    <div id="col-en" class="col-en">{''.join(en_parts)}</div>
    <div id="col-zh" class="col-zh">{''.join(zh_parts)}</div>
  </div>
</body></html>"""


def paginate_section(
    blocks: list[dict],
    en_heights: list[dict],
    zh_heights: list[dict],
    max_h: float,
) -> list[dict]:
    n = len(blocks)
    groups: list[list[int]] = []
    i = 0
    keep_types = ("chapter_title", "essay_title", "section_title", "question", "book_entry")
    while i < n:
        grp = [i]
        while i < n - 1 and blocks[i]["type"] in keep_types:
            i += 1
            grp.append(i)
        groups.append(grp)
        i += 1

    limit = max_h - 14.0

    def sim_h(indices: list[int], heights: list[dict]) -> float:
        if not indices:
            return 0.0
        total = 0.0
        prev_mb = 0.0
        for pos, idx in enumerate(indices):
            item = heights[idx]
            total += item["h"] if pos == 0 else max(prev_mb, item["mt"]) + item["h"]
            prev_mb = item["mb"]
        return total

    spreads: list[dict] = []
    curr: list[int] = []
    for grp in groups:
        cand = curr + grp
        if curr and (sim_h(cand, en_heights) > limit or sim_h(cand, zh_heights) > limit):
            spreads.append({
                "indices": curr,
                "en_h": sim_h(curr, en_heights),
                "zh_h": sim_h(curr, zh_heights),
            })
            curr = list(grp)
        else:
            curr = cand
    if curr:
        spreads.append({
            "indices": curr,
            "en_h": sim_h(curr, en_heights),
            "zh_h": sim_h(curr, zh_heights),
        })
    return spreads


def build_toc_items(sections: list[dict]) -> list[dict]:
    items: list[dict] = []
    last_group = None
    for sec in sections:
        kind = sec.get("kind")
        if kind == "epigraph_spread":
            continue
        if kind == "part_opener":
            en_t = sec.get("toc_en") or f"{sec['en_label'].title()}: {sec['en_title']}"
            zh_t = sec.get("toc_zh") or f"{sec['zh_label']}：{sec['zh_title']}"
            items.append({
                "kind": "entry",
                "sid": sec["id"],
                "is_part": True,
                "en": en_t,
                "zh": zh_t,
                "offset": sec["_offset"],
            })
            continue

        g_en = sec.get("toc_group_en")
        g_zh = sec.get("toc_group_zh")
        if g_en and g_en != last_group:
            items.append({"kind": "group_label", "en": g_en, "zh": g_zh or g_en})
            last_group = g_en

        en_t = sec.get("toc_en") or sec["blocks"][0]["en"]
        zh_t = sec.get("toc_zh") or sec["blocks"][0]["zh"]
        items.append({
            "kind": "entry",
            "sid": sec["id"],
            "is_part": False,
            "en": en_t,
            "zh": zh_t,
            "offset": sec["_offset"],
        })
    return items


def paginate_and_render_toc(
    page, meta: dict, toc_items: list[dict], css: str, max_h: float
) -> tuple[list[str], int]:
    """Dynamically measure and paginate Bilingual TOC into 1+ spreads, then inject exact page numbers."""
    if not toc_items:
        return [], 0

    def render_row(item: dict, lang: str, page_shift: int = 0) -> str:
        if item["kind"] == "group_label":
            return f'<div class="toc-group-{lang}">{html.escape(item[lang])}</div>'
        cls = "toc-part-row" if item["is_part"] else "toc-child"
        pg = item["offset"] + page_shift + (0 if lang == "en" else 1)
        return (
            f'<div class="toc-row {cls}">'
            f'<span>{html.escape(item[lang])}</span>'
            f'<span class="toc-dots"></span>'
            f'<span class="toc-pg">{pg}</span></div>'
        )

    # Measure TOC items in Chrome
    en_rows = "".join(render_row(it, "en") for it in toc_items)
    zh_rows = "".join(render_row(it, "zh") for it in toc_items)
    m_html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{css}
    .ms {{ display: flex; gap: 20mm; padding: 10mm; }}
    </style></head><body><div class="ms">
      <div class="col-en" id="ten">
        <div id="th-en" class="toc-title-en">Contents</div>
        <div id="thc-en" class="toc-title-en toc-cont">Contents (continued)</div>
        {en_rows}
      </div>
      <div class="col-zh" id="tzh">
        <div id="th-zh" class="toc-title-zh">目录</div>
        <div id="thc-zh" class="toc-title-zh toc-cont">目录（续）</div>
        {zh_rows}
      </div>
    </div></body></html>"""
    page.set_content(m_html, wait_until="load")
    page.evaluate("() => document.fonts.ready")
    tm = page.evaluate("""() => {
        const readCol = (id) => {
            const kids = Array.from(document.getElementById(id).children);
            const h0 = kids[0].getBoundingClientRect().height + (parseFloat(getComputedStyle(kids[0]).marginBottom) || 0);
            const hc = kids[1].getBoundingClientRect().height + (parseFloat(getComputedStyle(kids[1]).marginBottom) || 0);
            const rows = kids.slice(2).map(el => {
                const cs = getComputedStyle(el);
                return {
                    h: el.getBoundingClientRect().height,
                    mt: parseFloat(cs.marginTop) || 0,
                    mb: parseFloat(cs.marginBottom) || 0
                };
            });
            return { h0, hc, rows };
        };
        return { en: readCol('ten'), zh: readCol('tzh') };
    }""")

    limit = max_h - 14.0
    spreads: list[list[int]] = []
    curr: list[int] = []
    n = len(toc_items)
    i = 0
    groups: list[list[int]] = []
    while i < n:
        grp = [i]
        while i < n - 1 and toc_items[i]["kind"] == "group_label":
            i += 1
            grp.append(i)
        groups.append(grp)
        i += 1

    def sim_toc(indices: list[int], col_info: dict, is_first: bool) -> float:
        total = col_info["h0"] if is_first else col_info["hc"]
        prev_mb = 0.0
        rows = col_info["rows"]
        for pos, idx in enumerate(indices):
            r = rows[idx]
            total += r["h"] if pos == 0 else max(prev_mb, r["mt"]) + r["h"]
            prev_mb = r["mb"]
        return total

    for grp in groups:
        cand = curr + grp
        is_first = len(spreads) == 0
        if curr and (sim_toc(cand, tm["en"], is_first) > limit or sim_toc(cand, tm["zh"], is_first) > limit):
            spreads.append(curr)
            curr = list(grp)
        else:
            curr = cand
    if curr:
        spreads.append(curr)

    toc_pages_count = 2 * len(spreads)
    page_shift = 2 + toc_pages_count  # Page 1 = Title, Pages 2..(1+toc_pages_count) = TOC

    pages_html: list[str] = []
    pg_num = 2
    for s_idx, sp_idxs in enumerate(spreads):
        t_en = '<div class="toc-title-en">Contents</div>' if s_idx == 0 else '<div class="toc-title-en toc-cont">Contents (continued)</div>'
        t_zh = '<div class="toc-title-zh">目录</div>' if s_idx == 0 else '<div class="toc-title-zh toc-cont">目录（续）</div>'
        r_en = "".join(render_row(toc_items[idx], "en", page_shift) for idx in sp_idxs)
        r_zh = "".join(render_row(toc_items[idx], "zh", page_shift) for idx in sp_idxs)

        pages_html.append(f"""
<section class="page page-even">
  <div class="running-header"><span class="hdr-main">{html.escape(meta['title_en'])}</span><span class="hdr-sub">Contents</span></div>
  <div class="page-body col-en">{t_en}{r_en}</div>
  <div class="running-footer"><span>{pg_num}</span></div>
</section>""")
        pg_num += 1
        pages_html.append(f"""
<section class="page page-odd">
  <div class="running-header"><span class="hdr-main">{html.escape(meta['title_zh'])}</span><span class="hdr-sub">目录</span></div>
  <div class="page-body col-zh">{t_zh}{r_zh}</div>
  <div class="running-footer"><span>{pg_num}</span></div>
</section>""")
        pg_num += 1

    return pages_html, toc_pages_count


def render_section_pages(
    sec: dict,
    spreads: list[dict] | None,
    start_page_num: int,
    spec: dict,
    max_h: float,
    boost_log: list[tuple[int, float, float, float]] | None = None,
) -> list[str]:
    pages_html: list[str] = []
    pg = start_page_num
    kind = sec.get("kind")

    if kind == "epigraph_spread":
        pages_html.append(f"""
<section class="page page-even part-page">
  <div class="part-center">
    <div class="part-rule"></div>
    <div class="part-epigraph-en">{html.escape(sec['en_quote'])}</div>
    <div class="part-author-en">{html.escape(sec.get('en_author', ''))}</div>
    {f'<div class="part-lead-en">{html.escape(sec["en_lead"])}</div>' if sec.get("en_lead") else ''}
  </div>
  <div class="running-footer"><span>{pg}</span></div>
</section>""")
        pages_html.append(f"""
<section class="page page-odd part-page">
  <div class="part-center">
    <div class="part-rule"></div>
    <div class="part-epigraph-zh">{html.escape(sec['zh_quote'])}</div>
    <div class="part-author-zh">{html.escape(sec.get('zh_author', ''))}</div>
    {f'<div class="part-lead-zh">{html.escape(sec["zh_lead"])}</div>' if sec.get("zh_lead") else ''}
  </div>
  <div class="running-footer"><span>{pg + 1}</span></div>
</section>""")
        return pages_html

    if kind == "part_opener":
        pages_html.append(f"""
<section class="page page-even part-page">
  <div class="part-center">
    <div class="part-label-en">{html.escape(sec['en_label'])}</div>
    <div class="part-title-en">{html.escape(sec['en_title'])}</div>
    <div class="part-rule"></div>
    <div class="part-epigraph-en">{html.escape(sec.get('en_epigraph', ''))}</div>
  </div>
  <div class="running-footer"><span>{pg}</span></div>
</section>""")
        pages_html.append(f"""
<section class="page page-odd part-page">
  <div class="part-center">
    <div class="part-label-zh">{html.escape(sec['zh_label'])}</div>
    <div class="part-title-zh">{html.escape(sec['zh_title'])}</div>
    <div class="part-rule"></div>
    <div class="part-epigraph-zh">{html.escape(sec.get('zh_epigraph', ''))}</div>
  </div>
  <div class="running-footer"><span>{pg + 1}</span></div>
</section>""")
        return pages_html

    blocks = sec["blocks"]
    base_lh = spec["en_lh_base"]
    max_lh = spec["en_lh_max"]
    base_pb = spec["en_pb_mm"]

    for sp in spreads:
        sp_idxs = sp["indices"]
        en_h = sp["en_h"]
        zh_h = sp["zh_h"]
        en_style = ""
        if zh_h - en_h > 16.0 and en_h > 120.0:
            max_ratio_by_lh = max_lh / base_lh
            max_ratio_by_box = max(1.0, (max_h - 16.0) / en_h)
            ratio = min(zh_h / en_h, max_ratio_by_lh, max_ratio_by_box)
            if ratio > 1.015:
                adj_lh = round(base_lh * ratio, 3)
                adj_pb = round(base_pb * (1.0 + (ratio - 1.0) * 0.75), 2)
                en_style = f' style="--en-lh: {adj_lh}; --en-pb: {adj_pb}mm;"'
                if boost_log is not None:
                    boost_log.append((pg, en_h, zh_h, adj_lh))

        en_in = "\n".join(render_block_html(blocks[i], "en") for i in sp_idxs)
        zh_in = "\n".join(render_block_html(blocks[i], "zh") for i in sp_idxs)
        pages_html.append(f"""
<section class="page page-even">
  <div class="running-header"><span class="hdr-main">{html.escape(sec['hdr_en_main'])}</span><span class="hdr-sub">{html.escape(sec['hdr_en_sub'])}</span></div>
  <div class="page-body col-en"{en_style}>{en_in}</div>
  <div class="running-footer"><span>{pg}</span></div>
</section>""")
        pg += 1
        pages_html.append(f"""
<section class="page page-odd">
  <div class="running-header"><span class="hdr-main">{html.escape(sec['hdr_zh_main'])}</span><span class="hdr-sub">{html.escape(sec['hdr_zh_sub'])}</span></div>
  <div class="page-body col-zh">{zh_in}</div>
  <div class="running-footer"><span>{pg}</span></div>
</section>""")
        pg += 1
    return pages_html


def main() -> None:
    parser = argparse.ArgumentParser(description="Render bilingual facing-page Print & SpreadPreview PDFs.")
    parser.add_argument("--book", required=True, help="Path to book_structure.json")
    parser.add_argument("--trans-dir", default=None, help="Directory of translated chunk JSONs")
    parser.add_argument("--out-dir", required=True, help="Output directory")
    parser.add_argument("--size", choices=["a5", "b5"], default="a5", help="Trim size (default: a5)")
    parser.add_argument("--no-toc", action="store_true", help="Omit Bilingual Table of Contents")
    parser.add_argument("--chrome", default=None, help="Explicit Chrome/Chromium binary path")
    args = parser.parse_args()

    spec = PAGE_SPECS[args.size]
    css = build_css(spec)
    chrome_bin = find_chrome(args.chrome)

    book_path = Path(args.book)
    trans_dir = Path(args.trans_dir) if args.trans_dir else None
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = out_dir / "_tmp_batches"
    sample_dir = out_dir / "preview_samples"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    sample_dir.mkdir(parents=True, exist_ok=True)
    for d in (tmp_dir, sample_dir):
        for f in d.glob("*"):
            if f.is_file():
                f.unlink()

    meta, sections = load_book_and_translations(book_path, trans_dir)
    slug = meta.get("slug") or "Bilingual_Book"
    print_pdf = out_dir / f"{slug}_Bilingual_Print.pdf"
    spread_pdf = out_dir / f"{slug}_Bilingual_SpreadPreview.pdf"

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=chrome_bin)
        page = browser.new_page()

        # Pass 1: Measure all flow blocks
        measure_html = build_measure_html(sections, css).replace("var(--body-h, 155mm)", f"{spec['body_h_mm']}mm")
        page.set_content(measure_html, wait_until="load")
        page.evaluate("() => document.fonts.ready")
        metrics = page.evaluate("""() => {
            const boxH = document.getElementById('measure-box').getBoundingClientRect().height;
            const readCol = (id) => {
                const byUid = {};
                for (const el of document.getElementById(id).children) {
                    const uid = el.getAttribute('data-uid');
                    const rect = el.getBoundingClientRect();
                    const cs = getComputedStyle(el);
                    byUid[uid] = { h: rect.height, mt: parseFloat(cs.marginTop) || 0, mb: parseFloat(cs.marginBottom) || 0 };
                }
                return byUid;
            };
            return { boxH, en: readCol('col-en'), zh: readCol('col-zh') };
        }""")
        max_h = metrics["boxH"]

        section_spreads: dict[str, list[list[int]]] = {}
        rel_offset = 0
        for sec in sections:
            sec["_offset"] = rel_offset
            if sec.get("kind") == "flow":
                en_h = [metrics["en"][b["uid"]] for b in sec["blocks"]]
                zh_h = [metrics["zh"][b["uid"]] for b in sec["blocks"]]
                sp = paginate_section(sec["blocks"], en_h, zh_h, max_h)
                section_spreads[sec["id"]] = sp
                rel_offset += 2 * len(sp)
            else:
                rel_offset += 2

        # TOC generation
        if args.no_toc:
            toc_pages: list[str] = []
            toc_count = 0
            pdf_bookmarks = [[1, f"{meta['title_en']} / {meta['title_zh']}", 1]]
        else:
            toc_items = build_toc_items(sections)
            toc_pages, toc_count = paginate_and_render_toc(page, meta, toc_items, css, max_h)
            pdf_bookmarks = [
                [1, f"{meta['title_en']} / {meta['title_zh']}", 1],
                [1, "Contents / 目录", 2],
            ]

        first_content_page = 2 + toc_count
        for sec in sections:
            sec["start_page"] = first_content_page + sec["_offset"]
            kind = sec.get("kind")
            if kind == "part_opener":
                en_t = sec.get("toc_en") or f"{sec['en_label'].title()}: {sec['en_title']}"
                zh_t = sec.get("toc_zh") or f"{sec['zh_label']}：{sec['zh_title']}"
                pdf_bookmarks.append([1, f"{en_t} / {zh_t}", sec["start_page"]])
            elif kind == "flow":
                en_t = sec.get("toc_en") or sec["blocks"][0]["en"]
                zh_t = sec.get("toc_zh") or sec["blocks"][0]["zh"]
                lvl = sec.get("toc_level", 1)
                pdf_bookmarks.append([lvl, f"{en_t} / {zh_t}", sec["start_page"]])

        # Build HTML batches (~60 pages max per batch to keep Chrome fast & light)
        sub_en_html = f'<div class="title-sub-en">{html.escape(meta["subtitle_en"])}</div>' if meta.get("subtitle_en") else ""
        sub_zh_html = f'<div class="title-sub-zh">{html.escape(meta["subtitle_zh"])}</div>' if meta.get("subtitle_zh") else ""
        title_html = f"""
<section class="page page-odd title-page">
  <div class="title-box">
    <div class="title-eyebrow">{html.escape(meta.get('eyebrow', 'Bilingual Facing-Page Edition'))}</div>
    <div class="title-rule-top"></div>
    <div class="title-en">{html.escape(meta['title_en'])}</div>
    {sub_en_html}
    <div class="title-divider"></div>
    <div class="title-zh">{html.escape(meta['title_zh'])}</div>
    {sub_zh_html}
  </div>
  <div class="title-footer-note">{html.escape(meta.get('footer_note', 'Left Page: Original English · Right Page: Chinese Translation'))}</div>
</section>"""

        batches: list[tuple[str, list[str]]] = [("00_front", [title_html] + toc_pages)]
        curr_pages: list[str] = []
        b_idx = 1
        boost_log: list[tuple[int, float, float, float]] = []
        for sec in sections:
            sp = section_spreads.get(sec["id"])
            sec_pages = render_section_pages(sec, sp, sec["start_page"], spec, max_h, boost_log)
            if curr_pages and len(curr_pages) + len(sec_pages) > 80:
                batches.append((f"{b_idx:02d}_body", curr_pages))
                b_idx += 1
                curr_pages = []
            curr_pages.extend(sec_pages)
        if curr_pages:
            batches.append((f"{b_idx:02d}_body", curr_pages))
        if boost_log:
            print(f"Adaptive EN leading applied on {len(boost_log)} spreads (e.g., p.{boost_log[0][0]}: EN {boost_log[0][1]:.0f}px vs ZH {boost_log[0][2]:.0f}px -> lh={boost_log[0][3]})")

        batch_pdfs: list[Path] = []
        for bname, bpages in batches:
            doc_html = f"<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'><style>{css}</style></head><body>{''.join(bpages)}</body></html>"
            page.set_content(doc_html, wait_until="load")
            page.evaluate("() => document.fonts.ready")
            overflows = page.evaluate("""() => {
                return Array.from(document.querySelectorAll('.page-body'))
                    .map((el, i) => ({ index: i, overflow: el.scrollHeight - el.clientHeight }))
                    .filter(x => x.overflow > 1);
            }""")
            if overflows:
                raise RuntimeError(f"Overflow detected in batch {bname}: {overflows}")
            bp = tmp_dir / f"{bname}.pdf"
            page.pdf(path=str(bp), prefer_css_page_size=True, print_background=True)
            batch_pdfs.append(bp)
            print(f"Batch {bname}: {len(bpages)} pages (0 overflows)")
        browser.close()

    # Merge PDFs
    final_doc = fitz.open()
    for bp in batch_pdfs:
        sub = fitz.open(str(bp))
        final_doc.insert_pdf(sub)
        sub.close()

    if len(final_doc) % 2 == 1:
        r0 = final_doc[0].rect
        final_doc.new_page(width=r0.width, height=r0.height)
        print(f"Appended 1 blank verso page for duplex printing -> {len(final_doc)} total pages")

    for i, pg in enumerate(final_doc):
        r = pg.rect
        w_mm = r.width * 25.4 / 72.0
        h_mm = r.height * 25.4 / 72.0
        if abs(w_mm - spec["w_mm"]) > 0.5 or abs(h_mm - spec["h_mm"]) > 0.5:
            raise RuntimeError(f"Page {i+1} invalid size: {w_mm:.2f}x{h_mm:.2f}mm")

    final_doc.set_toc(pdf_bookmarks)
    final_doc.save(str(print_pdf), garbage=4, deflate=True)
    print(f"Saved Print PDF: {print_pdf} ({len(final_doc)} pages)")

    # Build 2-up vector SpreadPreview PDF
    spread_doc = fitz.open()
    r0 = final_doc[0].rect
    w_pt, h_pt = r0.width, r0.height

    def add_spread(left_idx: int | None, right_idx: int | None):
        sp = spread_doc.new_page(width=w_pt * 2, height=h_pt)
        if left_idx is not None:
            sp.show_pdf_page(fitz.Rect(0, 0, w_pt, h_pt), final_doc, left_idx)
        else:
            sp.draw_rect(fitz.Rect(0, 0, w_pt, h_pt), color=None, fill=(0.97, 0.97, 0.98))
        if right_idx is not None:
            sp.show_pdf_page(fitz.Rect(w_pt, 0, w_pt * 2, h_pt), final_doc, right_idx)
        else:
            sp.draw_rect(fitz.Rect(w_pt, 0, w_pt * 2, h_pt), color=None, fill=(0.97, 0.97, 0.98))
        sp.draw_line(fitz.Point(w_pt, 0), fitz.Point(w_pt, h_pt), color=(0.82, 0.84, 0.88), width=0.6)

    add_spread(None, 0)
    for p_idx in range(1, len(final_doc), 2):
        add_spread(p_idx, p_idx + 1 if p_idx + 1 < len(final_doc) else None)

    spread_doc.save(str(spread_pdf), garbage=4, deflate=True)
    print(f"Saved SpreadPreview PDF: {spread_pdf} ({len(spread_doc)} spreads)")

    # Save representative PNG samples
    n_sp = len(spread_doc)
    sample_idxs = sorted({
        0,
        min(1, n_sp - 1),
        min(2, n_sp - 1),
        n_sp // 3,
        (2 * n_sp) // 3,
        max(0, n_sp - 2),
    })
    mat = fitz.Matrix(160 / 72.0, 160 / 72.0)
    for si in sample_idxs:
        pix = spread_doc[si].get_pixmap(matrix=mat, alpha=False)
        pix.save(str(sample_dir / f"sample_spread_{si:03d}.png"))

    spread_doc.close()
    final_doc.close()
    shutil.rmtree(tmp_dir, ignore_errors=True)
    print(f"Saved {len(sample_idxs)} sample PNGs in {sample_dir}")


if __name__ == "__main__":
    main()
