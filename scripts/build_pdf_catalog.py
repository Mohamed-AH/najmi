#!/usr/bin/env python3
"""
Build a standalone catalog (CSV) for the newly-downloaded PDFs, from
download_results.csv (the log written by download_missing_files.py).

Only rows with type=pdf and status=ok are included -- this is a record of
what was actually downloaded, not the full manifest.

Usage:
    python3 build_pdf_catalog.py \
        --results download_results.csv \
        --out pdf_catalog.csv
"""
import argparse
import csv
import sys
from urllib.parse import unquote

PAGE_CATEGORY = {
    "book_lib": "الكتب",
    "comments": "التعليقات",
    "messages": "الرسائل",
    "cv_ar": "من السيرة الذاتية",
}


def page_of(local_path):
    # local_path looks like "pdf/<page>/<filename>"
    parts = local_path.replace("\\", "/").split("/")
    return parts[1] if len(parts) >= 3 else ""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results", default="download_results.csv")
    ap.add_argument("--out", default="pdf_catalog.csv")
    args = ap.parse_args()

    print(f"[1/2] Reading {args.results}")
    with open(args.results, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    print(f"      -> {len(rows)} row(s) loaded")

    pdf_rows = [r for r in rows if r["type"] == "pdf" and r["status"] == "ok"]
    print(f"      -> {len(pdf_rows)} successfully-downloaded PDF(s)")

    catalog = []
    for r in pdf_rows:
        page = page_of(r["local_path"])
        catalog.append({
            "file-name": unquote(r["url"].rsplit("/", 1)[-1]),
            "title": r["title"].strip(),
            "category": PAGE_CATEGORY.get(page, page),
            "source-url": r["url"],
        })

    catalog.sort(key=lambda r: (r["category"], r["title"]))

    print(f"[2/2] Writing catalog: {args.out}")
    with open(args.out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["file-name", "title", "category", "source-url"])
        w.writeheader()
        w.writerows(catalog)

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total PDFs catalogued: {len(catalog)}")
    import collections
    for cat, n in collections.Counter(r["category"] for r in catalog).most_common():
        print(f"  {n:3d}  {cat}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
