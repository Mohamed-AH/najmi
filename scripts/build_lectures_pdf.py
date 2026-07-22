#!/usr/bin/env python3
"""
Build a mobile-friendly, large-font, portrait Arabic PDF listing all the
downloaded lectures, grouped by category, from lectures_metadata_final.csv.

Titles are cleaned up before display:
  - embedded URLs (a scraping artifact) are stripped
  - a leading sequence-number digit glued to the start of the title
    (another scraping artifact, e.g. "2أعلام السنة المنشورة ...") is removed
  - titles that are empty or only contain a stray icon-font character are
    replaced with a readable title derived from the file name

Usage:
    python3 build_lectures_pdf.py \
        --csv lectures_metadata_final.csv \
        --html lectures.html \
        --pdf lectures.pdf
"""
import argparse
import csv
import html
import re
import sys


def clean_title(seq, title, file_name):
    t = (title or "").strip()
    t = re.sub(r"https?://\S+", "", t).strip()

    seq = (seq or "").strip()
    if seq and t.startswith(seq) and not t[len(seq):len(seq) + 1].isdigit():
        t = t[len(seq):].strip()
    m = re.match(r"^(\d+)(\D)", t)
    if m:
        t = t[len(m.group(1)):].strip()

    t = re.sub(r"\s+", " ", t).strip(" -–—")

    # drop stray private-use-area icon-font glyphs left over from scraping
    t = "".join(ch for ch in t if not (0xE000 <= ord(ch) <= 0xF8FF)).strip()

    if not t:
        base = file_name.rsplit(".", 1)[0]
        t = base.replace("-", " ").replace("_", " ").strip()
    return t


def seq_key(seq):
    seq = (seq or "").strip()
    return int(seq) if seq.isdigit() else 10 ** 9


def build_html(rows, generated_on):
    by_category = {}
    order = []
    for row in rows:
        cat = row["category"].strip() or "بدون تصنيف"
        if cat not in by_category:
            by_category[cat] = []
            order.append(cat)
        by_category[cat].append(row)

    order.sort(key=lambda c: -len(by_category[c]))

    total = len(rows)

    summary_lis = "".join(
        f'<li>{html.escape(cat)} <span class="count">({len(by_category[cat])})</span></li>'
        for cat in order
    )

    sections = []
    for cat in order:
        items = by_category[cat]
        items.sort(key=lambda r: seq_key(r["sequence-inseries"]))
        lis = []
        for i, row in enumerate(items, start=1):
            title = clean_title(row["sequence-inseries"], row["lecture-title"], row["file-name"])
            lis.append(f"<li><span class=\"num\">{i}.</span> {html.escape(title)}</li>")
        sections.append(
            f'<section class="cat">'
            f'<h2>{html.escape(cat)} <span class="count">({len(items)})</span></h2>'
            f'<ol>{"".join(lis)}</ol>'
            f"</section>"
        )

    return f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
<meta charset="utf-8">
<title>فهرس المحاضرات الصوتية</title>
<style>
  @page {{ size: A4 portrait; margin: 16mm 14mm; }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: 'FreeSans', 'Liberation Sans', 'Noto Sans', sans-serif;
    font-size: 19px;
    line-height: 1.9;
    color: #111;
    direction: rtl;
  }}
  .cover {{
    text-align: center;
    padding-top: 30vh;
    page-break-after: always;
  }}
  .cover h1 {{
    font-size: 34px;
    margin: 0 0 18px 0;
  }}
  .cover .meta {{
    font-size: 20px;
    color: #444;
    margin-top: 10px;
  }}
  .summary {{
    page-break-after: always;
  }}
  .summary h1 {{
    font-size: 26px;
    text-align: center;
    margin: 0 0 20px 0;
  }}
  .summary ol {{
    list-style: decimal;
    padding-right: 26px;
    margin: 0;
  }}
  .summary li {{
    border-bottom: none;
    padding-bottom: 8px;
    margin-bottom: 8px;
    font-size: 20px;
  }}
  h2 {{
    font-size: 24px;
    background: #f0f0f0;
    border-right: 6px solid #444;
    padding: 8px 14px;
    margin: 26px 0 10px 0;
    page-break-after: avoid;
  }}
  .count {{
    font-size: 17px;
    color: #555;
    font-weight: normal;
  }}
  ol {{
    margin: 0;
    padding-right: 0;
    list-style: none;
  }}
  li {{
    margin: 0 0 10px 0;
    padding-bottom: 10px;
    border-bottom: 1px solid #ddd;
    page-break-inside: avoid;
  }}
  .num {{
    color: #666;
    font-weight: bold;
    margin-left: 6px;
  }}
  section.cat {{
    page-break-inside: auto;
  }}
</style>
</head>
<body>
  <div class="cover">
    <h1>فهرس المحاضرات الصوتية</h1>
    <div class="meta">إجمالي عدد المحاضرات: {total}</div>
    <div class="meta">عدد الأبواب: {len(order)}</div>
    <div class="meta">تاريخ الإعداد: {generated_on}</div>
  </div>
  <div class="summary">
    <h1>الأبواب</h1>
    <ol>{summary_lis}</ol>
  </div>
  {"".join(sections)}
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", default="lectures_metadata_final.csv")
    ap.add_argument("--html", default="lectures.html")
    ap.add_argument("--pdf", default="lectures.pdf")
    ap.add_argument("--date", default="")
    args = ap.parse_args()

    import datetime
    generated_on = args.date or datetime.date.today().isoformat()

    print(f"[1/3] Reading {args.csv}")
    with open(args.csv, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    print(f"      -> {len(rows)} rows loaded")

    print("[2/3] Building HTML")
    doc = build_html(rows, generated_on)
    with open(args.html, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"      -> written to {args.html}")

    print("[3/3] Rendering PDF with headless Chromium")
    from playwright.sync_api import sync_playwright
    import os
    html_path = os.path.abspath(args.html)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        page = browser.new_page()
        page.goto("file://" + html_path)
        page.pdf(path=args.pdf, format="A4", print_background=True,
                 margin={"top": "16mm", "bottom": "16mm", "left": "14mm", "right": "14mm"})
        browser.close()
    print(f"      -> written to {args.pdf}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
