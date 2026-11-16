"""Fetch articles from data/urls.txt and keep sentences that state an indicator value.

Output: data/claims_raw.csv (one row per candidate claim sentence).
"""
import csv, json, re, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests, trafilatura

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0 (research crawler; claims-vs-BPS study)"}

# ponytail: keyword regex is a recall-oriented pre-filter; the LLM extraction step decides what's a real claim.
INDICATOR = re.compile(r"inflasi|pengangguran|\bTPT\b|kemiskinan|penduduk miskin|pertumbuhan ekonomi|ekonomi (?:Indonesia|RI|nasional)? ?(?:tumbuh|triwulan|kuartal)|PDB", re.I)
NUMBER = re.compile(r"\d+(?:[.,]\d+)?\s*(?:persen|%)", re.I)


CACHE = ROOT / "data/text_cache"
# pages that need a real browser (JS-rendered or TLS-chain issues) are saved by hand via Playwright
CACHED = {r["url"]: CACHE / r["file"] for r in csv.DictReader((CACHE / "index.csv").open(encoding="utf-8"))}


def fetch(url):
    if url in CACHED:
        return url, json.loads(CACHED[url].read_text(encoding="utf-8")), "", "cache"
    try:
        html = requests.get(url, headers=UA, timeout=20).text
        doc = trafilatura.bare_extraction(html, url=url, with_metadata=True)
        if not doc:
            return url, None, None, "no_text"
        d = doc if isinstance(doc, dict) else doc.as_dict()
        return url, d.get("text"), d.get("date"), "ok"
    except Exception as e:
        return url, None, None, f"err:{type(e).__name__}"


# Pages whose date trafilatura can't find (ekon.go.id puts it only in the dateline); read by hand via Playwright.
DATES = {r["url_id"]: r["article_date"] for r in csv.DictReader((ROOT / "data/article_dates.csv").open(encoding="utf-8"))}


def url_id(url):
    m = re.search(r"(ekon\.go\.id)/(?:unduh/)?publikasi/(?:detail/)?(\d+)", url)
    return f"{m.group(1)}/{m.group(2)}" if m else url


def sentences(text):
    # split on sentence end; keep decimals like 3,23 intact
    return [s.strip() for s in re.split(r"(?<=[.!?\"”])\s+(?=[A-Z\"“])", text.replace("\n", " ")) if s.strip()]


def main():
    urls = [u.strip() for u in (ROOT / "data/urls.txt").read_text().splitlines() if u.strip()]
    with ThreadPoolExecutor(8) as ex:
        results = list(ex.map(fetch, urls))
    rows, n = [], 0
    for url, text, date, status in results:
        print(f"{status:12} {url[:90]}", file=sys.stderr)
        if not text:
            continue
        sents = sentences(text)
        for i, s in enumerate(sents):
            if INDICATOR.search(s) and NUMBER.search(s) and len(s) < 600:
                n += 1
                rows.append({"claim_id": f"c{n:04d}", "url": url, "article_date": date or DATES.get(url_id(url), ""),
                             "sentence": s, "context_prev": sents[i - 1] if i else ""})
    out = ROOT / "data/claims_raw.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader(); w.writerows(rows)
    ok = sum(1 for r in results if r[1])
    print(f"{ok}/{len(urls)} articles fetched, {len(rows)} candidate claims -> {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
