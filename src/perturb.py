"""Synthetic perturbation benchmark: claims with KNOWN answers, built from the BPS table itself.

  uv run python src/perturb.py make            # -> data/perturbed_claims.csv (+ expected answers)
  uv run python src/pipeline.py --claims data/perturbed_claims.csv --out-dir results/perturb --model <m> --batch 20 [--e2e]
  uv run python src/perturb.py score           # -> results/perturb_metrics.md
  uv run python src/perturb.py make-hard       # harder set -> data/perturbed_hard_*.csv
  uv run python src/perturb.py score-hard      # -> results/perturb_hard_metrics.md (outputs: results/perturb_hard/)

Each official figure is restated as a fluent Indonesian sentence, either faithfully or with one controlled
change. This isolates the verdict step from the messiness of real text: a verifier that is sensitive should
flag every near-miss, and a specific one should accept every faithful rounding.
"""
import csv, glob, json, random, sys
from collections import Counter, defaultdict
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline as p  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")  # Windows console is cp1252; reports contain κ, ≥, →

ROOT = p.ROOT
CLAIMS, EXPECTED = ROOT / "data/perturbed_claims.csv", ROOT / "data/perturbed_expected.csv"
BULAN = {v: k.capitalize() for k, v in p.MONTHS.items()}
ROMAN = {1: "I", 2: "II", 3: "III", 4: "IV"}

TEMPLATES = {  # two phrasings each so the benchmark is not one string pattern
    "inflation_yoy": ["Inflasi tahunan (year-on-year) Indonesia pada {when} tercatat sebesar {v} persen.",
                      "Menurut BPS, inflasi y-on-y {when} berada di level {v} persen."],
    "unemployment_rate": ["Tingkat pengangguran terbuka (TPT) pada {when} sebesar {v} persen.",
                          "BPS mencatat TPT nasional {when} mencapai {v} persen."],
    "poverty_rate": ["Persentase penduduk miskin pada {when} sebesar {v} persen.",
                     "Tingkat kemiskinan nasional {when} tercatat {v} persen."],
    "gdp_growth_yoy": ["Ekonomi Indonesia {when} tumbuh {v} persen (y-on-y).",
                       "Pertumbuhan ekonomi nasional {when} mencapai {v} persen secara tahunan."],
}


def when(ind, period):
    if "-Q" in period:
        y, q = period.split("-Q")
        return f"triwulan {ROMAN[int(q)]} {y}"
    if "-" in period:
        y, m = period.split("-")
        return f"{BULAN[int(m)]} {y}"
    return f"tahun {period}"


def idn(d):
    return str(d).replace(".", ",")


def variants(ind, period, official, ref, rng):
    """-> [(kind, stated Decimal, claimed period, expected verdict)]"""
    o = Decimal(repr(official))
    out = [("exact", o, period, "MATCH")]
    one = o.quantize(Decimal("0.1"), ROUND_HALF_UP)
    if one != o:
        out.append(("rounded_1dp", one, period, "MATCH"))
        trunc = o.quantize(Decimal("0.1"), ROUND_DOWN)
        if trunc != one:  # truncating instead of rounding is a (small) misstatement
            out.append(("truncated_1dp", trunc, period, "MISMATCH"))
    step = Decimal(1).scaleb(o.as_tuple().exponent)
    out.append(("last_digit_plus1", o + step, period, "MISMATCH"))
    out.append(("off_by_0.5", o - Decimal("0.5"), period, "MISMATCH"))
    # same figure attributed to another period that the table has, with a different value
    others = [per for (i, per), v in ref.items() if i == ind and per != period and len(per) == len(period)
              and Decimal(repr(v)).quantize(step) != o]
    if others:
        out.append(("wrong_period", o, rng.choice(others), "MISMATCH"))
    year = int(period[:4])
    out.append(("absent_period", o, f"{year - 6}{period[4:]}", "UNVERIFIABLE"))  # before table coverage
    return out


def make(n_figures=12, seed=16):
    rng = random.Random(seed)
    ref = p.load_ref()
    by_ind = defaultdict(list)
    for (ind, per), v in sorted(ref.items()):
        by_ind[ind].append((per, v))
    picks = []
    for ind, rows in by_ind.items():  # stratified: same number of source figures per indicator
        picks += [(ind, per, v) for per, v in rng.sample(rows, min(n_figures // 4 + 1, len(rows)))]
    claims, expected, k = [], [], 0
    for ind, per, v in picks:
        for kind, stated, cper, exp in variants(ind, per, v, ref, rng):
            k += 1
            cid = f"p{k:04d}"
            tmpl = rng.choice(TEMPLATES[ind])
            claims.append({"claim_id": cid, "url": "synthetic", "article_date": f"{int(cper[:4]) + 1}-03-01",
                           "sentence": tmpl.format(when=when(ind, cper), v=idn(stated)), "context_prev": ""})
            expected.append({"claim_id": cid, "kind": kind, "indicator": ind, "period": cper,
                             "value": str(stated), "expected": exp, "source_period": per, "official": v})
    for path, rows in ((CLAIMS, claims), (EXPECTED, expected)):
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=rows[0].keys())
            w.writeheader()
            w.writerows(rows)
    print(f"{len(claims)} synthetic claims from {len(picks)} official figures -> {CLAIMS.name}, {EXPECTED.name}")


HARD_CLAIMS, HARD_EXPECTED = ROOT / "data/perturbed_hard_claims.csv", ROOT / "data/perturbed_hard_expected.csv"


def make_hard(n_each=10, seed=16):
    """Harder cases modelled on what real sentences got wrong. Each row: the tuple a careful reader would extract
    (period resolved) and the expected verdict(s) ('A|B' = either is acceptable)."""
    import metrics
    rng = random.Random(seed)
    ref, variants, releases = p.load_ref(), metrics.load_variants(), metrics.load_releases()
    infl = sorted(per for (i, per) in ref if i == "inflation_yoy" and "-" in per and (i, per) in releases)
    claims, expected = [], []

    def add(kind, sentence, date, ind, per, val, exp):
        cid = f"h{len(claims) + 1:04d}"
        claims.append({"claim_id": cid, "url": "synthetic", "article_date": date, "sentence": sentence,
                       "context_prev": ""})
        expected.append({"claim_id": cid, "kind": kind, "indicator": ind, "period": per, "value": str(val),
                         "expected": exp})

    def shift(per, k=1):
        y, m = map(int, per.split("-"))
        m += k
        return f"{y + (m - 1) // 12}-{(m - 1) % 12 + 1:02d}"

    for per in rng.sample(infl[1:], n_each):  # "bulan lalu" must be resolved from the article date
        v = Decimal(repr(ref[("inflation_yoy", per)]))
        date = f"{shift(per)}-20"
        add("relative_last_month", f"Inflasi tahunan (y-on-y) bulan lalu tercatat sebesar {idn(v)} persen.",
            date, "inflation_yoy", per, v, "MATCH")
        before = ("inflation_yoy", shift(per, -1))
        if before in ref and Decimal(repr(ref[before])) != v:  # the month before's figure must be rejected
            prev = Decimal(repr(ref[before]))
            add("relative_wrong_month", f"Inflasi tahunan (y-on-y) bulan lalu tercatat sebesar {idn(prev)} persen.",
                date, "inflation_yoy", per, prev, "MISMATCH")
    for ind, word in (("unemployment_rate", "tingkat pengangguran terbuka (TPT)"),
                      ("inflation_yoy", "inflasi tahunan (y-on-y)")):
        rows = sorted((d, per) for (i, per), d in releases.items() if i == ind and "-" in per and "-Q" not in per)
        pairs = [(a, b) for a, b in zip(rows, rows[1:]) if ref[(ind, a[1])] != ref[(ind, b[1])]]
        for (d_old, p_old), (d_new, p_new) in rng.sample(pairs, min(n_each // 2, len(pairs))):
            y, m, dd = map(int, d_new.split("-"))
            date = f"{y}-{m:02d}-{min(dd + 3, 28):02d}"  # three days after the newer release
            old = Decimal(repr(ref[(ind, p_old)]))
            add("stale_latest", f"Data terbaru BPS mencatat {word} nasional sebesar {idn(old)} persen.",
                date, ind, p_new, old, "MISMATCH")
    mtm = sorted(per for (i, per) in variants if i == "inflation_mtm" and ("inflation_yoy", per) in ref)
    for per in rng.sample(mtm, min(n_each, len(mtm))):  # an m-to-m figure written as plain "inflasi"
        v = Decimal(repr(variants[("inflation_mtm", per)]))
        y, m = per.split("-")
        add("mtm_unlabelled", f"Inflasi {BULAN[int(m)]} {y} tercatat {idn(v)} persen.", f"{shift(per)}-05",
            "inflation_yoy", per, v, "NONE|MISMATCH|UNVERIFIABLE")  # anything but MATCH-as-y-on-y is defensible
    for path, rows in ((HARD_CLAIMS, claims), (HARD_EXPECTED, expected)):
        with path.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=rows[0].keys())
            w.writeheader()
            w.writerows(rows)
    print(f"{len(claims)} hard synthetic claims -> {HARD_CLAIMS.name}, {HARD_EXPECTED.name}")


def ok(got, exp):
    return got in exp.split("|")


def score(expected_path=EXPECTED, results_dir="results/perturb", out_name="perturb_metrics.md",
          title="Synthetic perturbation benchmark"):
    exp = {r["claim_id"]: r for r in csv.DictReader(Path(expected_path).open(encoding="utf-8"))}
    ref = p.load_ref()
    systems = {"oracle (gold tuple → deterministic verdict)": {
        cid: p.verdict(p.clean([{"indicator": r["indicator"], "period": r["period"], "value": r["value"]}])[0], ref)[0]
        for cid, r in exp.items()}}
    for f in sorted(glob.glob(str(ROOT / results_dir / "extract_*.jsonl"))):
        got = {}
        for d in map(json.loads, open(f, encoding="utf-8")):
            cl = d["claims"]
            # each synthetic sentence states exactly one figure; no extraction = the system missed it
            got[d["claim_id"]] = (cl[0].get("llm_verdict") or p.verdict(cl[0], ref)[0]) if cl else "NONE"
        systems[Path(f).stem.removeprefix("extract_")] = got
    kinds = sorted({r["kind"] for r in exp.values()})
    L = [f"# {title}\n",
         f"{len(exp)} claims built from official figures; every claim has a known verdict (`A|B` = either "
         "accepted). Cells = share of claims judged as expected (n in brackets).\n",
         "| system | covered | " + " | ".join(kinds) + " | overall | false accusations | missed errors |",
         "|---" * (len(kinds) + 5) + "|"]
    for name, got in systems.items():
        ids = [c for c in exp if c in got]
        if not ids:
            continue
        cells = []
        for k in kinds:
            kid = [c for c in ids if exp[c]["kind"] == k]
            cells.append(f"{sum(ok(got[c], exp[c]['expected']) for c in kid) / len(kid):.0%} ({len(kid)})" if kid else "–")
        acc = sum(ok(got[c], exp[c]["expected"]) for c in ids) / len(ids)
        fa = sum(got[c] == "MISMATCH" and exp[c]["expected"] == "MATCH" for c in ids)
        missed = sum(got[c] == "MATCH" and "MATCH" not in exp[c]["expected"].split("|") for c in ids)
        L.append(f"| {name} | {len(ids)}/{len(exp)} | " + " | ".join(cells) + f" | **{acc:.0%}** | {fa} | {missed} |")
    out = ROOT / "results" / out_name
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(out.read_text(encoding="utf-8"))
    return systems, exp


if __name__ == "__main__":
    {"make": make, "score": score, "make-hard": make_hard,
     "score-hard": lambda: score(HARD_EXPECTED, "results/perturb_hard", "perturb_hard_metrics.md",
                                 "Hard synthetic benchmark (relative periods, stale figures, unlabelled m-to-m)"),
     }[sys.argv[1] if len(sys.argv) > 1 else "score"]()
