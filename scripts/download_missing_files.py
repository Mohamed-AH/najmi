#!/usr/bin/env python3
"""
Download every file listed in a manifest CSV (default: files_to_download.csv,
produced by build_site_inventory.py + the Phase 2 cross-check) into a local
output folder, skipping files that were already downloaded successfully.

Meant to be run on a machine that actually has network access to the site
(this was built in a sandboxed session where outbound access to alnajmi.net
is blocked by network policy).

Stdlib only -- no pip install needed, just Python 3.

Usage:
    python3 download_missing_files.py \
        --manifest files_to_download.csv \
        --out-dir downloaded \
        --results download_results.csv

Re-running the script is safe: files that already exist locally with a
non-zero size are skipped, and download_results.csv from a previous run is
consulted so only rows that previously failed (or are new) are retried.
"""
import argparse
import csv
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import quote, urlsplit, urlunsplit

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AlNajmiArchiveBot/1.0"


def safe_url(url):
    """Percent-encode a URL's path/query so non-ASCII characters (e.g. raw
    Arabic filenames straight out of an href attribute) don't crash the
    HTTP request line, without double-encoding sequences already escaped."""
    parts = urlsplit(url)
    path = quote(parts.path, safe="/%")
    query = quote(parts.query, safe="=&%")
    return urlunsplit((parts.scheme, parts.netloc, path, query, parts.fragment))


def load_manifest(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_previous_results(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        return {row["url"]: row["status"] for row in csv.DictReader(f)}


def download_one(url, dest_path, timeout, retries, backoff, ssl_context):
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
        return "skipped_exists", None

    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    req = urllib.request.Request(safe_url(url), headers={"User-Agent": USER_AGENT})

    last_err = None
    for attempt in range(1, retries + 1):
        try:
            tmp_path = dest_path + ".part"
            with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as resp:
                with open(tmp_path, "wb") as out:
                    while True:
                        chunk = resp.read(1 << 16)
                        if not chunk:
                            break
                        out.write(chunk)
            if os.path.getsize(tmp_path) == 0:
                os.remove(tmp_path)
                return "failed_empty", "downloaded 0 bytes"
            os.replace(tmp_path, dest_path)
            return "ok", None
        except urllib.error.HTTPError as e:
            last_err = f"HTTP {e.code}"
            if e.code in (404, 403):
                break  # not retryable
        except (urllib.error.URLError, ssl.SSLCertVerificationError) as e:
            reason = getattr(e, "reason", e)
            if isinstance(reason, ssl.SSLCertVerificationError) or "CERTIFICATE_VERIFY_FAILED" in str(reason):
                last_err = f"TLS cert verification failed ({reason}); re-run with --insecure if you trust this site"
                break  # not retryable without the flag
            last_err = str(reason)
        except Exception as e:  # noqa: BLE001 - report and retry
            last_err = str(e)

        if attempt < retries:
            time.sleep(backoff * attempt)

    return "failed", last_err


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", default="files_to_download.csv")
    ap.add_argument("--out-dir", default="downloaded")
    ap.add_argument("--results", default="download_results.csv")
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--retries", type=int, default=4)
    ap.add_argument("--backoff", type=float, default=3.0)
    ap.add_argument("--insecure", action="store_true",
                     help="Skip TLS certificate verification. Only use this if you've "
                          "confirmed the certificate error is a hosting quirk on a site "
                          "you trust, not an actual man-in-the-middle.")
    args = ap.parse_args()

    ssl_context = None
    if args.insecure:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        print("!! --insecure set: TLS certificate verification is DISABLED for this run.")

    print(f"[1/2] Loading manifest: {args.manifest}")
    manifest = load_manifest(args.manifest)
    print(f"      -> {len(manifest)} file(s) listed")

    prev = load_previous_results(args.results)
    already_ok = sum(1 for u, s in prev.items() if s == "ok")
    if prev:
        print(f"      -> found previous results ({already_ok} already ok)")

    print("[2/2] Downloading ...")
    results = []
    ok = skipped = failed = 0
    total = len(manifest)
    for i, row in enumerate(manifest, start=1):
        url = row["url"]
        dest = os.path.join(args.out_dir, row["local_path"])
        label = row.get("title") or row["local_path"]

        if prev.get(url) == "ok" and os.path.exists(dest):
            status, err = "skipped_exists", None
        else:
            status, err = download_one(url, dest, args.timeout, args.retries, args.backoff, ssl_context)

        if status == "ok":
            ok += 1
            tag = "OK"
        elif status.startswith("skipped"):
            skipped += 1
            tag = "SKIP"
        else:
            failed += 1
            tag = "FAIL"

        print(f"      [{i}/{total}] {tag:4s} {row['type']:5s} {label[:50]:50s}"
              + (f"  ({err})" if err else ""))

        results.append({
            "url": url,
            "local_path": row["local_path"],
            "type": row["type"],
            "title": row.get("title", ""),
            "status": status,
            "error": err or "",
        })

    with open(args.results, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["url", "local_path", "type", "title", "status", "error"])
        w.writeheader()
        w.writerows(results)

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Downloaded now : {ok}")
    print(f"Already present: {skipped}")
    print(f"Failed         : {failed}")
    print(f"Results log    : {args.results}")
    if failed:
        print("\nRe-run this script to retry only the failed rows.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
