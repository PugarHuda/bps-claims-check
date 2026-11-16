"""Keep the evidence table current: read the newest BPS press-release titles and append new headline figures.

  uv run python src/update_bps.py            # append new rows to data/bps_reference.csv
  uv run python src/update_bps.py --dry-run  # only report

The BPS listing is rendered client-side (Next.js server actions), so a real browser is used. BRS titles state
the headline value ("Inflasi Year-on-Year (y-on-y) Oktober 2026 sebesar 3,23 persen"), which is what we parse.
Existing rows are NEVER overwritten (the table holds first-release values); a different value for an existing
period is reported as a possible revision for a human to look at. Runs monthly via .github/workflows/update-bps.yml,
which opens a pull request instead of committing, so a person reviews every new number.
"""
import argparse, csv, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline as p  # noqa: E402

LISTING = "https://www.bps.go.id/id/pressrelease"
REF = p.ROOT / "data/bps_reference.csv"
NUM = r"(-?\d+(?:,\d+)?)"
ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4}


def num(s, deflation=False):
    v = float(s.replace(",", "."))
    return -abs(v) if deflation else v


def parse(title, url):
    """One BRS title -> (indicator, period, value) or None. Release date comes from the URL path."""
    t = " ".join(title.split())
    low = t.lower()
    rel = re.search(r"/pressrelease/(\d{4})/(\d{2})/\d{2}/", url)
    months = "|".join(p.MONTHS)
    if "y-on-y" in low and ("inflasi" in low or "deflasi" in low) and "provinsi" not in low.split("sebesar")[0]:
        m = re.search(rf"({months})\s+(\d{{4}}).*?sebesar\s+{NUM}\s*persen", low) or \
            re.search(rf"sebesar\s+{NUM}\s*persen.*?({months})\s+(\d{{4}})", low)
        if m:
            g = m.groups()
            mon, yr, val = (g[0], g[1], g[2]) if g[0] in p.MONTHS else (g[1], g[2], g[0])
            defl = "deflasi" in low.split("sebesar")[0] and "inflasi" not in low.split("sebesar")[0]
            return "inflation_yoy", f"{yr}-{p.MONTHS[mon]:02d}", num(val, defl)
    if m := re.search(rf"ekonomi indonesia triwulan (iv|i{{1,3}})[- ](\d{{4}}) (tumbuh|terkontraksi) {NUM} persen \(y-on-y\)", low):
        return "gdp_growth_yoy", f"{m.group(2)}-Q{ROMAN[m.group(1).upper()]}", num(m.group(4), m.group(3) == "terkontraksi")
    if m := re.search(rf"ekonomi indonesia tahun (\d{{4}}) (tumbuh|terkontraksi) {NUM} persen", low):
        return "gdp_growth_yoy", m.group(1), num(m.group(3), m.group(2) == "terkontraksi")
    if (m := re.search(rf"tingkat pengangguran terbuka \(tpt\) sebesar {NUM} persen", low)) and rel:
        # titles omit the survey month; Sakernas results are released 3 months after the survey month
        y, mo = int(rel.group(1)), int(rel.group(2)) - 3
        return "unemployment_rate", f"{y - (mo <= 0)}-{(mo - 1) % 12 + 1:02d}", num(m.group(1))
    if m := re.search(rf"persentase penduduk miskin (?:pada )?({months}) (\d{{4}}) (?:sebesar|turun menjadi|naik menjadi|menjadi) {NUM} persen", low):
        return "poverty_rate", f"{m.group(2)}-{p.MONTHS[m.group(1)]:02d}", num(m.group(3))
    return None


def fetch_titles(pages=1):
    from playwright.sync_api import sync_playwright
    out = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(LISTING, wait_until="networkidle", timeout=90000)
        for i in range(pages):
            out += page.evaluate("""() => [...document.querySelectorAll('a[href*="/pressrelease/20"]')]
                                    .map(a => [a.href, (a.innerText || '').split('\\n').filter(Boolean)])""")
            nxt = page.locator("button[aria-label*='next' i], a[aria-label*='next' i]")
            if i + 1 < pages and nxt.count():
                nxt.first.click()
                page.wait_for_load_state("networkidle")
        browser.close()
    # anchor text = [date, title, abstract...]; the title is the line that states a value
    return [(href, next((l for l in lines if "persen" in l.lower()), lines[1] if len(lines) > 1 else ""))
            for href, lines in out]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--pages", type=int, default=2)
    a = ap.parse_args()
    rows = list(csv.DictReader(REF.open(encoding="utf-8-sig")))
    have = {(r["indicator"], r["period"]): float(r["value"]) for r in rows}
    new, revised, seen = [], [], set()
    for href, title in fetch_titles(a.pages):
        hit = parse(title, href)
        if not hit or hit[:2] in seen:
            continue
        seen.add(hit[:2])
        ind, per, val = hit
        if (ind, per) not in have:
            new.append({"indicator": ind, "period": per, "value": f"{val:.2f}", "unit": "pct",
                        "source_url": href.split("?")[0], "provenance": "bps_listing_auto"})
        elif abs(have[(ind, per)] - val) > 1e-9:
            revised.append((ind, per, have[(ind, per)], val, href))
        else:
            print(f"  OK   {ind} {per} {val} already in table")
    print(f"parsed {len(seen)} headline releases; new: {len(new)}; differs from stored: {len(revised)}")
    for r in new:
        print("  NEW", r["indicator"], r["period"], r["value"], r["source_url"])
    for ind, per, old, val, href in revised:
        print(f"  CHECK {ind} {per}: stored {old}, listing {val} ({href}) -- not changed (first-release policy)")
    if new and not a.dry_run:
        rows += new
        rows.sort(key=lambda r: (r["indicator"], r["period"]))
        with REF.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"appended {len(new)} rows -> {REF}")


if __name__ == "__main__":
    main()
