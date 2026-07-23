#!/usr/bin/env python3
"""
Build a single report of every audio file we were NOT able to download,
combining:
  - the one file that failed a real download attempt (download_results.csv,
    status != ok), which has a confirmed direct file link and a confirmed
    HTTP error.
  - the files that were never downloaded in the very first place
    (missing_files_report.csv), which usually only have a category page
    link (no direct file URL was ever known for them).

Usage:
    python3 build_failed_downloads_report.py \
        --missing missing_files_report.csv \
        --download-results download_results.csv \
        --out failed_downloads.csv
"""
import argparse
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_lectures_pdf import clean_title  # noqa: E402

DIRECT_NOTE = "رابط مباشر للملف - تم تأكيد أنه غير موجود على الخادم (خطأ {code}) عند محاولة التحميل الفعلية"
PAGE_NOTE_CONFIRMED = "رابط الصفحة العامة فقط (مؤكد أن الملف غير متاح - ظهر خطأ 404 أثناء جمع البيانات الأصلي)"
PAGE_NOTE_UNKNOWN = "رابط الصفحة العامة فقط (لم يتم العثور على رابط مباشر للملف ولا تأكيد لسبب غيابه)"


def strip_scrape_error(t):
    return re.split(r"Requested file could not be found", t, flags=re.IGNORECASE)[0].strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--missing", default="missing_files_report.csv")
    ap.add_argument("--download-results", default="download_results.csv")
    ap.add_argument("--out", default="failed_downloads.csv")
    args = ap.parse_args()

    print(f"[1/3] Reading {args.download_results}")
    confirmed_failed = []
    handled_filenames = set()
    if Path(args.download_results).exists():
        with open(args.download_results, encoding="utf-8-sig", newline="") as f:
            dl = list(csv.DictReader(f))
        for r in dl:
            if r["status"] == "ok" or r["status"].startswith("skipped"):
                continue
            fname = r["url"].rsplit("/", 1)[-1]
            confirmed_failed.append({
                "file-name": fname,
                "title": r["title"].strip(),
                "category": "",
                "link": r["url"],
                "note": DIRECT_NOTE.format(code=r["error"].replace("HTTP ", "") or "?"),
            })
            handled_filenames.add(fname.lower())
    print(f"      -> {len(confirmed_failed)} confirmed failed download(s)")

    print(f"[2/3] Reading {args.missing}")
    with open(args.missing, encoding="utf-8-sig", newline="") as f:
        missing = list(csv.DictReader(f))
    print(f"      -> {len(missing)} originally-missing row(s)")

    rows = list(confirmed_failed)
    for r in missing:
        if r["file-name"].lower() in handled_filenames:
            continue  # already covered above with better/confirmed info
        raw_title = strip_scrape_error(r["lecture-title"])
        title = clean_title(r["sequence-inseries"], raw_title, r["file-name"])
        had_404_marker = "404" in r["lecture-title"]
        rows.append({
            "file-name": r["file-name"],
            "title": title,
            "category": r["category"],
            "link": r["source-url"],
            "note": PAGE_NOTE_CONFIRMED if had_404_marker else PAGE_NOTE_UNKNOWN,
        })

    # fill in category for the confirmed-failed rows if missing lets us
    for r in rows:
        if not r["category"]:
            match = next((m for m in missing if m["file-name"].lower() == r["file-name"].lower()), None)
            r["category"] = match["category"] if match else ""

    print(f"[3/3] Writing {args.out}")
    with open(args.out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["file-name", "title", "category", "link", "note"])
        w.writeheader()
        w.writerows(rows)

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total files never downloaded: {len(rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
