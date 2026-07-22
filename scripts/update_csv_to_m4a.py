#!/usr/bin/env python3
"""
Update lectures_metadata.csv so the "file-name" column reflects the actual
downloaded/converted .m4a file name.

Steps:
  1. De-duplicate: if two or more CSV rows are byte-for-byte identical
     (same file-name, title, sequence, dates, category, source-url), only
     the first occurrence is kept. The dropped copies are written to a
     separate report (--dupes-report) so nothing is silently lost.
  2. For every remaining row:
       - If a downloaded file with the same base name exists (in
         pathm4a.txt), the "file-name" column is rewritten to
         "<actual-base-name>.m4a", using the exact casing/name found on
         disk (the "correct" file name).
       - If no downloaded file matches, the row is left with its original
         "file-name" (still .mp3) untouched, and flagged via a new
         "download-status" column so it's easy to filter later.

A "download-status" column (downloaded / missing) is appended to the output
so no information is silently lost.

Usage:
    python3 update_csv_to_m4a.py \
        --csv lectures_metadata.csv \
        --paths pathm4a.txt \
        --output lectures_metadata_m4a.csv \
        --dupes-report removed_duplicates_report.csv
"""
import argparse
import csv
import sys
from pathlib import PureWindowsPath


def load_csv_rows(csv_path):
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)
    return header, rows


def load_downloaded_basenames(paths_path):
    bases = {}  # lower(base) -> actual base name on disk (e.g. "cvs1")
    with open(paths_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip().strip('"')
            if not line:
                continue
            name = PureWindowsPath(line).name
            base = name.rsplit(".", 1)[0] if "." in name else name
            bases.setdefault(base.lower(), base)
    return bases


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", default="lectures_metadata.csv")
    ap.add_argument("--paths", default="pathm4a.txt")
    ap.add_argument("--output", default="lectures_metadata_m4a.csv")
    ap.add_argument("--dupes-report", default="removed_duplicates_report.csv")
    args = ap.parse_args()

    print(f"[1/4] Reading CSV: {args.csv}")
    header, rows = load_csv_rows(args.csv)
    total = len(rows)
    print(f"      -> {total} rows loaded")

    print("[2/4] Removing exact-duplicate rows ...")
    seen = set()
    deduped_rows = []
    removed_rows = []
    for row in rows:
        key = tuple(row)
        if key in seen:
            removed_rows.append(row)
        else:
            seen.add(key)
            deduped_rows.append(row)
    print(f"      -> {len(removed_rows)} duplicate rows removed, "
          f"{len(deduped_rows)} unique rows remain")

    if removed_rows:
        with open(args.dupes_report, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(removed_rows)
        print(f"      -> removed rows written to {args.dupes_report}")

    rows = deduped_rows
    total = len(rows)

    print(f"[3/4] Reading downloaded file paths: {args.paths}")
    downloaded = load_downloaded_basenames(args.paths)
    print(f"      -> {len(downloaded)} unique downloaded base names loaded")

    print("[4/4] Rewriting file-name column to .m4a where a match exists ...")
    updated_rows = []
    updated_count = 0
    unchanged_count = 0
    progress_step = max(1, total // 10)

    for i, row in enumerate(rows, start=1):
        row = list(row)
        file_name = row[0]
        base = file_name.rsplit(".", 1)[0] if "." in file_name else file_name

        actual_base = downloaded.get(base.lower())
        if actual_base is not None:
            row[0] = f"{actual_base}.m4a"
            row.append("downloaded")
            updated_count += 1
        else:
            row.append("missing")
            unchanged_count += 1

        updated_rows.append(row)

        if i % progress_step == 0 or i == total:
            print(f"      ... {i}/{total} rows processed "
                  f"(updated={updated_count}, unchanged={unchanged_count})")

    print("Writing output:", args.output)
    with open(args.output, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(list(header) + ["download-status"])
        writer.writerows(updated_rows)

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Original rows in CSV       : {total + len(removed_rows)}")
    print(f"Duplicate rows removed     : {len(removed_rows)}")
    print(f"Unique rows kept           : {total}")
    print(f"Updated to .m4a            : {updated_count}")
    print(f"Left as .mp3 (missing)     : {unchanged_count}")
    print(f"Output written to          : {args.output}")
    if removed_rows:
        print(f"Removed duplicates written : {args.dupes_report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
