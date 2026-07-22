#!/usr/bin/env python3
"""
Patch in real Arabic lecture titles recovered from the site's page source
(saved HTML for https://alnajmi.net/portal/m2/ and /m3/), for rows whose
"lecture-title" column was empty or just a broken icon-font glyph.

Those two categories ("لقاءات قرآنية" and "خطب قرآنية") were originally
scraped with only a stray private-use-area icon character where the title
should have been, so the PDF fell back to showing the raw (Latin-script)
file name -- which is what triggered the "titles are in English" feedback.
The real titles live next to each audio player's "استماع" (listen) button
in an <h6> tag; recovered_titles.json maps lower-cased base file name ->
Arabic title, built by parsing the saved page HTML.

Usage:
    python3 apply_recovered_titles.py \
        --csv lectures_metadata_final.csv \
        --titles recovered_titles.json
"""
import argparse
import csv
import json
import sys


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", default="lectures_metadata_final.csv")
    ap.add_argument("--titles", default="recovered_titles.json")
    args = ap.parse_args()

    print(f"[1/3] Loading recovered titles: {args.titles}")
    with open(args.titles, encoding="utf-8") as f:
        titles = json.load(f)
    print(f"      -> {len(titles)} recovered titles loaded")

    print(f"[2/3] Reading CSV: {args.csv}")
    with open(args.csv, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = [list(r) for r in reader]
    print(f"      -> {len(rows)} rows loaded")

    title_idx = header.index("lecture-title")
    name_idx = header.index("file-name")

    print("[3/3] Patching titles ...")
    updated = 0
    for row in rows:
        base = row[name_idx].rsplit(".", 1)[0].lower()
        if base in titles:
            row[title_idx] = titles[base]
            updated += 1

    with open(args.csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Rows updated with recovered titles: {updated}")
    print(f"Output written to                 : {args.csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
