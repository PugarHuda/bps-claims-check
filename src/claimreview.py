"""Export bindable verdicts as schema.org ClaimReview JSON-LD (the markup Google Fact Check Explorer
and Indonesian fact-checkers such as cekfakta.com publish), so results drop into a newsroom CMS.

  uv run python src/claimreview.py --source gold --review-url https://<user>.github.io/<repo>/claimreview.html
  uv run python src/claimreview.py --source results/extract_regex.jsonl --review-url ...

Writes results/claimreview.jsonld (array) + docs/claimreview.html (the page each ClaimReview `url` anchors
into, JSON-LD embedded; Google requires the review to live on a real page).
Four ratings: MATCH 5 "Sesuai data BPS"; MISFRAMED 3 "Angka benar, konteks keliru" (the stated number is a
different published variant of the same release, e.g. m-to-m inflation stated as inflation); STALE 3 "Angka lama"
(the number was right for an earlier release, but a newer one was already out on the article date); MISMATCH 1.
UNVERIFIABLE tuples are not exported: no evidence, no review.
"""
import argparse, csv, html, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline as p  # noqa: E402

NAMES = {"inflation_yoy": "inflasi (y-on-y)", "unemployment_rate": "tingkat pengangguran terbuka",
         "poverty_rate": "persentase penduduk miskin", "gdp_growth_yoy": "pertumbuhan ekonomi (y-on-y)"}
RATING = {"MATCH": (5, "Sesuai data BPS"), "MISFRAMED": (3, "Angka benar, konteks keliru"),
          "STALE": (3, "Angka lama: sudah ada rilis BPS yang lebih baru"), "MISMATCH": (1, "Tidak sesuai data BPS")}
FRAME_NAMES = {"inflation_mtm": "inflasi bulanan (m-to-m)", "inflation_ytd": "inflasi tahun kalender (y-to-d)",
               "gdp_growth_qoq": "pertumbuhan q-to-q", "gdp_growth_ctc": "pertumbuhan kumulatif (c-to-c)"}
ORG = {"@type": "Organization", "name": "BPS claim-check (Apart AI x Epistemics hackathon)"}


def anchor(r):
    return f"{r['claim_id']}-{r['indicator']}-{r['period']}"


def build(rows, review_url):
    out = []
    for r in rows:
        value, label = RATING[r["verdict"]]
        out.append({
            "@context": "https://schema.org", "@type": "ClaimReview",
            "url": f"{review_url}#{anchor(r)}",
            "claimReviewed": r["sentence"],
            "author": ORG,
            "reviewRating": {"@type": "Rating", "ratingValue": value, "bestRating": 5, "worstRating": 1,
                             "alternateName": label},
            "reviewBody": f"Klaim: {NAMES[r['indicator']]} periode {r['period']} = {r['text']} persen. "
                          f"Data resmi BPS (rilis pertama): {r['official']} persen. Sumber: {r['source_url']}"
                          + (f" Angka {r['text']} persen adalah {FRAME_NAMES[r['frame']]} pada rilis yang sama."
                             if r.get("frame") else "")
                          + (f" Angka {r['text']} persen adalah data periode {r['stale'][0]}; data {r['stale'][1]} "
                             f"sudah dirilis BPS pada {r['stale'][2]}, sebelum artikel terbit." if r.get("stale") else ""),
            "itemReviewed": {"@type": "Claim", "datePublished": r["article_date"] or None,
                             "appearance": [{"@type": "CreativeWork", "url": r["url"]}]},
        })
    return out


def rows_from(source):
    claims = {c["claim_id"]: c for c in p.load_claims()}
    ref = p.load_ref()
    urls = {(r["indicator"], r["period"]): r["source_url"]
            for r in csv.DictReader((p.ROOT / "data/bps_reference.csv").open(encoding="utf-8-sig"))}
    import metrics
    variants, releases = metrics.load_variants(), metrics.load_releases()
    if source == "gold":
        by_id = metrics.load_gold()[0]
    else:
        by_id = {d["claim_id"]: d["claims"] for d in map(json.loads, Path(source).open(encoding="utf-8"))}
    for cid, cl in by_id.items():
        for c in cl:
            v, official = p.verdict(c, ref)  # recompute against the current table
            if v == "UNVERIFIABLE":
                continue
            frame = metrics.frame_of(c, variants) if v == "MISMATCH" else None
            stale = metrics.stale_of(c, claims[cid]["article_date"], ref, releases) if v == "MISMATCH" and not frame else None
            yield {**claims[cid], **c, "text": c.get("text") or repr(c["value"]),
                   "verdict": "MISFRAMED" if frame else "STALE" if stale else v,
                   "official": official, "source_url": urls[(c["indicator"], c["period"])], "frame": frame,
                   "frame_value": variants.get((frame, c["period"])) if frame else None, "stale": stale}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="gold", help="'gold' or a results/extract_*.jsonl path")
    ap.add_argument("--review-url", required=True, help="public URL where docs/claimreview.html is served")
    a = ap.parse_args()
    rows = list(rows_from(a.source))
    doc = build(rows, a.review_url)
    (p.ROOT / "results/claimreview.jsonld").write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    (p.ROOT / "docs").mkdir(exist_ok=True)
    (p.ROOT / "docs/claimreview.html").write_text(page(rows, doc, a.source), encoding="utf-8")
    print(f"{len(doc)} ClaimReview items -> results/claimreview.jsonld, docs/claimreview.html")


def page(rows, doc, source):
    """The review page each ClaimReview `url` anchors into, with the JSON-LD embedded (what Google reads).
    docs/ so GitHub Pages can serve it as-is."""
    esc = lambda s: html.escape(str(s or ""))
    items = []
    for r, d in zip(rows, doc):
        items.append(f'''<article id="{esc(anchor(r))}" class="{r["verdict"].lower()}">
<p class="rating">{esc(RATING[r["verdict"]][1])} · {esc(NAMES[r["indicator"]])} {esc(r["period"])}</p>
<blockquote>{esc(r["sentence"])}</blockquote>
<p>Klaim: <b>{esc(r["text"])}%</b> · Data BPS: <b>{esc(r["official"])}%</b> (<a href="{esc(r["source_url"])}">BRS</a>)
{f'· sama dengan angka <b>{esc(FRAME_NAMES[r["frame"]])}</b> BPS ({esc(r["frame_value"])}%)' if r.get("frame") else ""}</p>
<p class="src"><a href="{esc(r["url"])}">{esc(r["url"])}</a> · {esc(r["article_date"])}</p>
<script type="application/ld+json">{json.dumps(d, ensure_ascii=False).replace("</", "<\\/")}</script>
</article>''')
    return f'''<!doctype html>
<html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cek Klaim BPS</title>
<style>
:root{{--bg:#fcfcfb;--fg:#0b0b0b;--muted:#52514e;--line:#e1e0d9;--ok:#2a78d6;--bad:#eb6834;--frame:#eda100}}
@media (prefers-color-scheme:dark){{:root{{--bg:#1a1a19;--fg:#f0efec;--muted:#c3c2b7;--line:#2c2c2a;--ok:#3987e5;--bad:#d95926;--frame:#c98500}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 system-ui,sans-serif}}
main{{max-width:760px;margin:0 auto;padding:16px}} a{{color:inherit;word-break:break-all}}
article{{border-left:4px solid var(--line);padding:4px 0 4px 14px;margin:22px 0}}
article.match{{border-color:var(--ok)}} article.mismatch{{border-color:var(--bad)}} article.misframed,article.stale{{border-color:var(--frame)}}
.rating{{font-weight:700;margin:0}} blockquote{{margin:8px 0;font-style:italic}} .src,.note{{color:var(--muted);font-size:14px}}
</style></head><body><main>
<h1>Cek klaim statistik vs data BPS</h1>
<p class="note">{len(rows)} klaim. Sumber verdict: <code>{esc(source)}</code>. Angka resmi BPS (rilis pertama) dibulatkan
setengah-ke-atas ke jumlah desimal yang disebut klaim. “Angka benar, konteks keliru” = angkanya sama dengan varian lain
dari rilis yang sama (mis. inflasi bulanan disajikan sebagai inflasi tahunan).</p>
{chr(10).join(items)}
</main></body></html>
'''


if __name__ == "__main__":
    main()
