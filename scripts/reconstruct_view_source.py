#!/usr/bin/env python3
"""
Reconstruct real HTML source from a browser "view-source:" page saved as
HTML (Chrome/Edge wrap each source line in a <tr><td class="line-content">
...escaped html...</td></tr> row). Feeding that wrapper file straight to an
HTML parser only sees the wrapper table, not the actual page -- this pulls
the original markup back out.

Usage:
    python3 reconstruct_view_source.py --in-dir site_source/fullsite --out-dir site_source/reconstructed
"""
import argparse
import sys
from pathlib import Path

from bs4 import BeautifulSoup


def reconstruct(path):
    with open(path, encoding="utf-8") as f:
        soup = BeautifulSoup(f, "lxml")
    tds = soup.select("td.line-content")
    if not tds:
        # not a view-source wrapper; assume it's already raw HTML
        with open(path, encoding="utf-8") as f:
            return f.read()
    return "\n".join(td.get_text() for td in tds)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    in_dir = Path(args.in_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(in_dir.glob("*.html"))
    print(f"[1/1] Reconstructing {len(files)} page(s) from {in_dir}")
    for i, path in enumerate(files, start=1):
        src = reconstruct(path)
        out_name = path.stem.replace("view-source_https___alnajmi.net_portal_", "").rstrip("_") + ".html"
        out_path = out_dir / out_name
        out_path.write_text(src, encoding="utf-8")
        print(f"      ({i}/{len(files)}) {path.name} -> {out_path.name} [{len(src)} chars]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
