"""Build the human-labelling sheet data/gold_sheet.csv (open in Excel / Google Sheets).

One row per candidate sentence; up to 3 in-scope (indicator, period, value) slots.
Put "x" in `checked` once a row is verified (even if it has no claims): metrics only use checked rows.
Pre-filled from the REGEX baseline only (not an LLM), so the gold labels are not anchored on any evaluated model.
`disagree` = how many different answers the systems gave for the sentence (a number only, no outputs shown):
label high-disagreement rows first if time is short.
"""
import csv, glob, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import pipeline as p  # noqa: E402

claims = p.load_claims()
ref = p.load_ref()
regex = {r["claim_id"]: r["claims"] for r in map(json.loads, (ROOT / "results/extract_regex.jsonl").open(encoding="utf-8"))}

cols = ["claim_id", "sentence", "context_prev", "article_date", "url"]
slots = [f"{k}{i}" for i in (1, 2, 3) for k in ("indicator", "period", "value")]
systems = [{d["claim_id"]: d["claims"] for d in map(json.loads, open(f, encoding="utf-8"))}
           for f in glob.glob(str(ROOT / "results/extract_*.jsonl")) if "e2e" not in f]


def disagree(cid):
    answers = {frozenset((c["indicator"], c["value"], p.verdict(c, ref)[0]) for c in s[cid]) for s in systems if cid in s}
    return len(answers)


dst = ROOT / "data/gold_sheet.csv"
if dst.exists() and any(r.get("checked") for r in csv.DictReader(dst.open(encoding="utf-8-sig"))):
    sys.exit("gold_sheet.csv already has checked rows; refusing to overwrite human labels")
with dst.open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=["checked", "disagree"] + cols + slots + ["speaker_type", "note"])
    w.writeheader()
    for c in claims:
        row = {k: c[k] for k in cols} | {"disagree": disagree(c["claim_id"])}
        for i, x in enumerate(regex.get(c["claim_id"], [])[:3], 1):
            row |= {f"indicator{i}": x["indicator"], f"period{i}": x["period"] or "", f"value{i}": x.get("text") or x["value"]}
        w.writerow(row)
print(f"{len(claims)} rows -> data/gold_sheet.csv")
