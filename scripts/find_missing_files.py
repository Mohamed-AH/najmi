#!/usr/bin/env python3
"""
Cross-check lectures_metadata.csv against pathm4a.txt to find:
  1. Lectures listed in the CSV that were never downloaded (no matching .m4a file).
  2. Lectures whose downloaded file name may have changed (best-effort fuzzy hints).

Usage:
    python3 find_missing_files.py \
        --csv lectures_metadata.csv \
        --paths pathm4a.txt \
        --report missing_files_report.csv

Matching strategy:
  - The CSV "file-name" column holds the *original* name (e.g. "cvs1.mp3").
  - pathm4a.txt holds absolute Windows paths to the downloaded/converted files
    (e.g. "D:\\najmi\\downloaded_site_data\\audios\\out\\cvs1.m4a").
  - We compare base names (file name without extension):
      1. Exact match (case-sensitive)      -> downloaded, no rename.
      2. Exact match (case-insensitive)    -> downloaded, casing changed.
      3. No match                           -> missing (not downloaded), and we
         report the closest look-alike names among the downloaded set purely as
         a hint for manual review (NOT assumed to be the same lecture).
"""
import argparse
import csv
import difflib
import sys
from pathlib import PureWindowsPath


def load_csv_rows(csv_path):
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)
    return header, rows


def load_downloaded_basenames(paths_path):
    bases = {}  # lower(base) -> list of (original_base, raw_line)
    with open(paths_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip().strip('"')
            if not line:
                continue
            name = PureWindowsPath(line).name  # e.g. "cvs1.m4a"
            base = name.rsplit(".", 1)[0] if "." in name else name
            bases.setdefault(base.lower(), []).append((base, name))
    return bases


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", default="lectures_metadata.csv")
    ap.add_argument("--paths", default="pathm4a.txt")
    ap.add_argument("--report", default="missing_files_report.csv")
    ap.add_argument("--fuzzy-cutoff", type=float, default=0.75,
                     help="difflib similarity cutoff for the informational rename hint")
    args = ap.parse_args()

    print(f"[1/4] Reading CSV: {args.csv}")
    header, rows = load_csv_rows(args.csv)
    total = len(rows)
    print(f"      -> {total} rows loaded")

    print(f"[2/4] Reading downloaded file paths: {args.paths}")
    downloaded = load_downloaded_basenames(args.paths)
    n_downloaded = sum(len(v) for v in downloaded.values())
    print(f"      -> {n_downloaded} downloaded file paths loaded "
          f"({len(downloaded)} unique base names)")

    all_downloaded_bases_lower = list(downloaded.keys())

    print("[3/4] Cross-checking CSV entries against downloaded files ...")
    missing = []
    renamed_case = []
    downloaded_count = 0
    progress_step = max(1, total // 10)

    for i, row in enumerate(rows, start=1):
        if not row:
            continue
        file_name = row[0]
        base = file_name.rsplit(".", 1)[0] if "." in file_name else file_name

        if base.lower() in downloaded:
            candidates = downloaded[base.lower()]
            exact = [c for c in candidates if c[0] == base]
            if exact:
                downloaded_count += 1
            else:
                downloaded_count += 1
                renamed_case.append((row, base, candidates[0][0]))
        else:
            hint = difflib.get_close_matches(
                base, all_downloaded_bases_lower, n=1, cutoff=args.fuzzy_cutoff
            )
            missing.append((row, base, hint[0] if hint else ""))

        if i % progress_step == 0 or i == total:
            print(f"      ... {i}/{total} rows checked")

    print("[4/4] Writing report:", args.report)
    with open(args.report, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(list(header) + ["status", "possible_match_hint"])
        for row, base, hint in missing:
            writer.writerow(list(row) + ["missing", hint])
        for row, base, actual in renamed_case:
            writer.writerow(list(row) + ["downloaded_case_mismatch", actual])

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total lectures in CSV      : {total}")
    print(f"Downloaded (exact match)   : {downloaded_count - len(renamed_case)}")
    print(f"Downloaded (casing differs): {len(renamed_case)}")
    print(f"Missing (not downloaded)   : {len(missing)}")
    print(f"Report written to          : {args.report}")
    if missing:
        print()
        print("Note: 'possible_match_hint' is only a fuzzy look-alike suggestion")
        print("for manual review -- it is NOT assumed to be the same lecture.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
