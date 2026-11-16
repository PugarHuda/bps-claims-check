"""Synthetic perturbation benchmark: claims with KNOWN answers, built from the BPS table itself.

  uv run python src/perturb.py make            # -> data/perturbed_claims.csv (+ expected answers)
  uv run python src/pipeline.py --claims data/perturbed_claims.csv --out-dir results/perturb --model <m> --batch 20 [--e2e]
  uv run python src/perturb.py score           # -> results/perturb_metrics.md

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


def score():
    exp = {r["claim_id"]: r for r in csv.DictReader(EXPECTED.open(encoding="utf-8"))}
    ref = p.load_ref()
    systems = {"oracle (gold tuple → deterministic verdict)": {
        cid: p.verdict(p.clean([{"indicator": r["indicator"], "period": r["period"], "value": r["value"]}])[0], ref)[0]
        for cid, r in exp.items()}}
    for f in sorted(glob.glob(str(ROOT / "results/perturb/extract_*.jsonl"))):
        got = {}
        for d in map(json.loads, open(f, encoding="utf-8")):
            cl = d["claims"]
            # each synthetic sentence states exactly one figure; no extraction = the system missed it
            got[d["claim_id"]] = (cl[0].get("llm_verdict") or p.verdict(cl[0], ref)[0]) if cl else "NONE"
        systems[Path(f).stem.removeprefix("extract_")] = got
    kinds = sorted({r["kind"] for r in exp.values()})
    L = ["# Synthetic perturbation benchmark\n",
         f"{len(exp)} claims built from official figures; every claim has a known verdict. "
         "Cells = share of claims where the system's verdict equals the expected one (n in brackets). "
         "`last_digit_plus1`, `truncated_1dp`, `off_by_0.5`, `wrong_period` must be MISMATCH; "
         "`exact`, `rounded_1dp` must be MATCH; `absent_period` must be UNVERIFIABLE.\n",
         "| system | covered | " + " | ".join(kinds) + " | overall | false accusations | missed errors |",
         "|---" * (len(kinds) + 5) + "|"]
    for name, got in systems.items():
        ids = [c for c in exp if c in got]
        if not ids:
            continue
        cells = []
        for k in kinds:
            kid = [c for c in ids if exp[c]["kind"] == k]
            cells.append(f"{sum(got[c] == exp[c]['expected'] for c in kid) / len(kid):.0%} ({len(kid)})" if kid else "–")
        acc = sum(got[c] == exp[c]["expected"] for c in ids) / len(ids)
        fa = sum(got[c] == "MISMATCH" and exp[c]["expected"] == "MATCH" for c in ids)
        missed = sum(got[c] == "MATCH" and exp[c]["expected"] == "MISMATCH" for c in ids)
        L.append(f"| {name} | {len(ids)}/{len(exp)} | " + " | ".join(cells) + f" | **{acc:.0%}** | {fa} | {missed} |")
    out = ROOT / "results/perturb_metrics.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(out.read_text(encoding="utf-8"))
    return systems, exp


if __name__ == "__main__":
    {"make": make, "score": score}[sys.argv[1] if len(sys.argv) > 1 else "score"]()
