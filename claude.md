# Task: full-site audio/PDF completeness check + download script

## Original request (superseded, kept for history)
The CSV contains the titles and details of the lectures from the site, while
the TXT file contains the paths of the files that were actually downloaded.
Cross-check CSV vs TXT, update CSV extensions to .m4a. -- DONE (see git log:
dedup, .m4a rename, PDF index for the sheikh, recovered 98 real Arabic
titles for 4 categories from saved page HTML).

## Current request
User attached `fullsite.zip` containing browser "view-source" saves of all
10 top-level portal pages (cv_ar, book_lib, comments, droos, fatawas, m1,
m2, m3, m4, messages). Two asks:
  1. Confirm lectures_metadata_final.csv has every audio file that exists
     on the site.
  2. Build a script to download whatever audio + PDF files are still
     missing (skip the ones already confirmed as 404/dead).

Network access to alnajmi.net is NOT available from this sandboxed
session (org proxy policy blocks it) -- the download script is meant to be
run by the user on their own machine, not executed here.

Working in phases so this can be resumed cleanly if interrupted.

## Site map (established in Phase 1)
- cv_ar    -- "عن الشيخ / السيرة الذاتية" bio page: 7 audio (matches our
              existing مواقف تربوية category, one dup URL reused for 2
              titles on the site itself) + 6 PDF books (NEW, not in CSV).
- m1       -- "المحاضرات" grid: 34 links / 33 unique filenames (one file,
              altaifh-almansoura.MP3, is linked twice under two different
              titles -- a mistake on the source site, not a gap on our
              side). Matches our 33-row المحاضرات القرآنية category.
- m2       -- "اللقاءات" grid: 38 unique filenames. Our لقاءات قرآنية
              category only has 37 downloaded -- the missing one is
              khraaj2.MP3, which IS present on the site (title: "جلسة مع
              طلبة العلم بالخرج 1416 هـ 2") but was never downloaded and
              had NO 404 marker in the original scrape -- genuinely
              recoverable.
  - m3       -- "الخطب" grid: 14 unique, matches خطب قرآنية exactly.
  - m4       -- "فوائد منتقاه" grid: 14 unique, matches فوائد قرآنية exactly.
  - droos    -- "الدروس" hub page only: links out to ~25 per-topic pages
              (شرح صحيح مسلم, شرح عمدة الأحكام, etc.) whose URLs already
              match our CSV's source-url column. No direct file links on
              the hub page itself; not in this zip.
  - fatawas  -- "الفتاوى" hub page only: links out to fat1..fat6 sub-pages
              (not included in this zip). Likely where most of our
              "فتاوى ..." categories (271+172+102+... rows) live.
  - book_lib -- "الكتب" table page: 63 PDF books (NEW content type,
              nothing in our CSV covers PDFs at all).
  - comments -- "التعليقات" table page: 38 PDF scholarly annotations (NEW).
  - messages -- "الرسائل" table page: 14 PDF treatises/letters (NEW).

## Artifacts produced so far
- `site_source/fullsite/*.html` -- raw upload, unzipped (browser
  view-source wrapper format: each source line is a `<td class="line-content">`
  in a table, not real markup).
- `scripts/reconstruct_view_source.py` -- pulls the real HTML back out of
  that view-source wrapper (also used previously for the m1/m4 title
  recovery in this same session).
- `site_source/reconstructed/*.html` -- the real HTML for all 10 pages.
- `scripts/build_site_inventory.py` -- parses all 10 pages (3 different
  page layouts: grid/mhc_column, bio/elementor-widgets, table/tr-td) into
  one unified inventory.
- `site_inventory.csv` -- 224 file links found (106 audio, 118 PDF; 221
  unique filenames after de-duping the one site-side mistake).

## Phase status
- [x] Phase 1: reconstruct pages, build full site inventory (audio + PDF,
      every page, all layouts). -- DONE, see site_inventory.csv (225 links,
      107 audio / 118 pdf, 222 unique filenames after fixing the cv_ar bio
      audio-widget selector to catch all 7 of its files, not just 6).
- [x] Phase 2: cross-check DONE. Results:
      - Audio completeness (Q1 answer): of the 5 pages covered by this zip
        (m1 المحاضرات, m2 اللقاءات, m3 الخطب, m4 فوائد, cv_ar bio) -- **zero**
        audio files exist on the site that aren't already known to our
        CSV. Only one is recoverable-but-not-yet-downloaded: `khraaj2.MP3`
        (م2, "جلسة مع طلبة العلم بالخرج 1416 هـ 2") -- it's on the site, not
        a 404, just never got downloaded originally.
      - IMPORTANT CAVEAT: the other 32 of the 33 originally-known-missing
        lectures (see missing_files_report.csv) live under categories that
        come from the `fatawas` (فتاوى) and `droos` (الدروس) hub pages'
        sub-pages (fat1..fat6, and ~25 per-topic شرح/كتاب pages) -- those
        sub-pages were NOT included in this zip (droos.html/fatawas.html
        are just menus linking out, no content of their own). So audio
        completeness is only CONFIRMED for the 5 pages actually provided;
        if the user wants full-site certainty they'd need to also save
        those sub-pages the same way.
      - Two harmless site-side data-entry duplicates found (same file
        linked under two different titles): `altaifh-almansoura.mp3`
        (audio, م1) and two PDF cases (`واعبدوا-الله...pdf`,
        `مراسلات-من-الشيخ-أحمد-4.pdf`). Not gaps -- just noted.
      - PDFs are an entirely new content type (our CSV never tracked
        PDFs): 116 unique PDF files across book_lib (62), comments (38),
        messages (13), cv_ar (3).
      - `files_to_download.csv` manifest written: 117 rows (1 audio + 116
        PDF), each with type/page/title/url/local_path.
- [x] Phase 3: download script built: `scripts/download_missing_files.py`.
      Stdlib-only (urllib, no pip installs needed), resumable (skips files
      that already exist locally with a nonzero size), retries with
      backoff, per-file progress printout, writes a
      `download_results.csv` log of success/failure per row so re-runs
      only retry what failed. Meant to be run BY THE USER on their own
      machine -- this sandboxed session cannot reach alnajmi.net (org
      network policy blocks it, confirmed earlier this session). Tested
      the script's mechanics (resume/skip logic, retry/backoff, manifest
      parsing, progress/log output) against a local mock HTTP server here
      since real network access isn't available in this environment.
- [ ] Phase 4: hand off to user -- they run
      `python3 download_missing_files.py` locally with
      `files_to_download.csv` next to it, review `download_results.csv`,
      and report back what came down. Once they confirm, add khraaj2 (and
      any PDFs they want catalogued) into lectures_metadata_final.csv /
      regenerate the PDF index if wanted.

## Resume instructions
If picking this up fresh: read this file, then `site_inventory.csv` and
`missing_files_report.csv`, then continue at Phase 2 above.
