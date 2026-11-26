#!/usr/bin/env python3
"""Validate 100% translation coverage, types, CJK presence, and glossary spot-checks."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def load_translations(trans_dir: Path | None) -> dict[str, str | list[str]]:
    trans: dict[str, str | list[str]] = {}
    if not trans_dir or not trans_dir.exists():
        return trans
    for tf in sorted(trans_dir.glob("*.json")):
        data = json.loads(tf.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            trans.update(data)
    return trans


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate bilingual book translations.")
    parser.add_argument("--book", required=True, help="Path to book_structure.json")
    parser.add_argument("--trans-dir", default=None, help="Directory of translated chunk JSONs")
    parser.add_argument(
        "--glossary-terms",
        default="",
        help="Comma-separated Chinese terms to report occurrence counts for",
    )
    args = parser.parse_args()

    book_path = Path(args.book)
    book = json.loads(book_path.read_text(encoding="utf-8"))
    sections = book["sections"] if isinstance(book, dict) else book
    trans_map = load_translations(Path(args.trans_dir) if args.trans_dir else None)

    total = 0
    missing: list[str] = []
    bad_type: list[tuple] = []
    no_cjk: list[tuple] = []
    bad_q: list[tuple] = []
    all_zh_texts: list[str] = []

    for sec in sections:
        if sec.get("kind") != "flow":
            continue
        for blk in sec["blocks"]:
            total += 1
            uid = blk["uid"]
            zh = blk.get("zh") if blk.get("zh") is not None else trans_map.get(uid)
            if zh is None or (isinstance(zh, str) and not zh.strip()) or (isinstance(zh, list) and not zh):
                missing.append(uid)
                continue

            if isinstance(blk["en"], list):
                if not isinstance(zh, list) or len(zh) != len(blk["en"]) or any(not str(x).strip() for x in zh):
                    bad_type.append((uid, type(zh).__name__, len(blk["en"]), len(zh) if isinstance(zh, list) else -1))
                    continue
                zh_str = " ".join(str(x) for x in zh)
            else:
                if not isinstance(zh, str):
                    bad_type.append((uid, type(zh).__name__, "str", "non-str"))
                    continue
                zh_str = zh

            all_zh_texts.append(zh_str)
            if not re.search(r"[\u4e00-\u9fff]", zh_str):
                no_cjk.append((uid, blk["type"], zh_str[:60]))
            if blk["type"] == "question" and not zh_str.startswith("问："):
                bad_q.append((uid, zh_str[:50]))

    print(f"Total flow blocks: {total}")
    print(f"Missing: {len(missing)} -> {missing[:10]}")
    print(f"Bad type / list length: {len(bad_type)} -> {bad_type[:10]}")
    print(f"No CJK characters: {len(no_cjk)} -> {no_cjk[:10]}")
    print(f"Questions missing '问：': {len(bad_q)} -> {bad_q[:10]}")

    if args.glossary_terms:
        terms = [t.strip() for t in args.glossary_terms.split(",") if t.strip()]
        for term in terms:
            cnt = sum(1 for t in all_zh_texts if term in t)
            print(f"Term {term!r} occurrences: {cnt}")

    if missing or bad_type or no_cjk or bad_q:
        return 1
    print("VALIDATION PASSED: 100% translation coverage and structural integrity.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
