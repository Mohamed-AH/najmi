#!/usr/bin/env python3
"""
Build a complete inventory of every audio (mp3/m4a) and PDF file referenced
anywhere across the reconstructed site pages (site_source/reconstructed/).

Three different page layouts are handled:
  - "grid" pages (m1 المحاضرات, m2 اللقاءات, m3 الخطب, m4 فوائد منتقاه):
    a sequence of <h1 class="mhc_fullwidth_header_title"> section headers
    followed by <div class="mhc_column"> cards, each with a <h6> title and
    an <a class="mhc_promo_button" href="...mp3"> listen link.
  - "bio" page (cv_ar عن الشيخ): a mix of Elementor audio-player widgets
    (div.elementor-widget-wp-widget-media_audio, title in <h5>, file in
    <audio><source src>) and icon-box PDF links (a[href$=.pdf] with the
    title as its text or aria-label).
  - "table" pages (book_lib الكتب, comments التعليقات, messages الرسائل):
    plain <tr><td>title</td><td><a href="...pdf"></a></td></tr> rows.

Usage:
    python3 build_site_inventory.py --in-dir site_source/reconstructed --out site_inventory.csv
"""
import argparse
import csv
import sys
from pathlib import Path
from urllib.parse import unquote

from bs4 import BeautifulSoup

GRID_PAGES = {"m1", "m2", "m3", "m4"}
TABLE_PAGES = {"book_lib", "comments", "messages"}
BIO_PAGES = {"cv_ar"}

MEDIA_EXTS = (".mp3", ".m4a", ".pdf")


def clean(text):
    return " ".join((text or "").split())


def extract_grid(page, soup, rows):
    els = soup.select("h1.mhc_fullwidth_header_title, div.mhc_column")
    section = None
    for el in els:
        if el.name == "h1":
            section = clean(el.get_text())
            continue
        h6 = el.find("h6")
        a = el.find("a", href=True)
        if not a:
            continue
        href = a["href"]
        if not href.lower().endswith((".mp3", ".m4a")):
            continue
        title = clean(h6.get_text()) if h6 else ""
        rows.append({
            "page": page,
            "section": section or "",
            "title": title,
            "url": href,
            "filename": href.rsplit("/", 1)[-1],
            "type": "audio",
        })


def extract_bio(page, soup, rows):
    for audio in soup.find_all("audio"):
        container = audio.find_parent("div", class_="elementor-widget-container") or audio.parent
        h5 = container.find("h5") if container else audio.find_previous("h5")
        source = audio.find("source", src=True) or audio.find("a", href=True)
        if not source:
            continue
        href = (source.get("src") or source.get("href")).split("?")[0]
        if not href.lower().endswith((".mp3", ".m4a")):
            continue
        title = clean(h5.get_text()) if h5 else ""
        rows.append({
            "page": page,
            "section": "",
            "title": title,
            "url": href,
            "filename": href.rsplit("/", 1)[-1],
            "type": "audio",
        })

    for box in soup.select("div.elementor-icon-box-wrapper"):
        a = box.find("a", href=lambda h: h and h.lower().endswith(".pdf"))
        if not a:
            continue
        title_el = box.select_one(".elementor-icon-box-title")
        title = clean(title_el.get_text()) if title_el else clean(a.get("aria-label", ""))
        href = a["href"]
        rows.append({
            "page": page,
            "section": "",
            "title": title,
            "url": href,
            "filename": href.rsplit("/", 1)[-1],
            "type": "pdf",
        })


def extract_table(page, soup, rows):
    for a in soup.find_all("a", href=lambda h: h and h.lower().endswith(".pdf")):
        tr = a.find_parent("tr")
        title = ""
        if tr:
            first_td = tr.find("td")
            if first_td:
                span = first_td.find("span", class_="title")
                title = clean(span.get_text()) if span else clean(first_td.get_text())
        if not title:
            title = unquote(a["href"].rsplit("/", 1)[-1].rsplit(".", 1)[0]).replace("-", " ")
        rows.append({
            "page": page,
            "section": "",
            "title": title,
            "url": a["href"],
            "filename": a["href"].rsplit("/", 1)[-1],
            "type": "pdf",
        })


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in-dir", default="site_source/reconstructed")
    ap.add_argument("--out", default="site_inventory.csv")
    args = ap.parse_args()

    in_dir = Path(args.in_dir)
    files = sorted(in_dir.glob("*.html"))
    print(f"[1/2] Parsing {len(files)} reconstructed page(s) from {in_dir}")

    rows = []
    for path in files:
        page = path.stem
        with open(path, encoding="utf-8") as f:
            soup = BeautifulSoup(f, "lxml")
        before = len(rows)
        if page in GRID_PAGES:
            extract_grid(page, soup, rows)
        elif page in BIO_PAGES:
            extract_bio(page, soup, rows)
        elif page in TABLE_PAGES:
            extract_table(page, soup, rows)
        else:
            print(f"      ! unknown page type for {path.name}, skipping")
            continue
        print(f"      {page:12s} -> {len(rows) - before:4d} file link(s)")

    print(f"[2/2] Writing inventory: {args.out}")
    with open(args.out, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["page", "section", "title", "url", "filename", "type"])
        writer.writeheader()
        writer.writerows(rows)

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total file links found : {len(rows)}")
    print(f"  audio (mp3/m4a)      : {sum(1 for r in rows if r['type'] == 'audio')}")
    print(f"  pdf                  : {sum(1 for r in rows if r['type'] == 'pdf')}")
    print(f"Unique filenames       : {len(set(r['filename'].lower() for r in rows))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
