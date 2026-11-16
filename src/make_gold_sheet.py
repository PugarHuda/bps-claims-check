"""Build the human-labelling sheet data/gold_sheet.csv (open in Excel / Google Sheets).

One row per candidate sentence; up to 3 in-scope (indicator, period, value) slots.
Put "x" in `checked` once a row is verified (even if it has no claims): metrics only use checked rows.
Pre-fill (--prefill):
  regex   (default) the naive baseline, so gold is not anchored on any capable model.
  silver  the blind Claude Opus annotation (data/silver_sheet.csv) incl. speaker_type and notes: the human only
          verifies/corrects ("LLM-assisted, human-verified"). Faster, but anchors the human on the silver labels,
          which inflates human-silver agreement and favours Claude-family systems; the report must say so.
`disagree` = how many different answers the systems gave for the sentence (a number only, no outputs shown):
label high-disagreement rows first if time is short.
"""
import argparse
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


def safe(v):
    """CSV/formula injection: Excel/Sheets run cells starting with = + - @ (or tab/CR) as formulas.
    Prefix them with ' (OWASP). Metrics take sentence text from claims_raw.csv, never from this sheet."""
    return "'" + v if v[:1] in ("=", "+", "-", "@", "\t", "\r") else v


ap = argparse.ArgumentParser()
ap.add_argument("--prefill", choices=["regex", "silver"], default="regex")
ap.add_argument("--adjudicated", action="store_true",
                help="write the evaluation sheet: silver labels, with every row in data/human_adjudication.csv "
                     "replaced by the human decision; label_source records which is which")
a = ap.parse_args()

if a.adjudicated:
    adj = {r["claim_id"]: r for r in csv.DictReader((ROOT / "data/human_adjudication.csv").open(encoding="utf-8"))}
    silver_rows = {r["claim_id"]: r for r in csv.DictReader((ROOT / "data/silver_sheet.csv").open(encoding="utf-8-sig"))}
    out = ROOT / "data/gold_sheet.csv"
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["checked", "claim_id"] + slots + ["speaker_type", "note", "label_source"])
        w.writeheader()
        for c in claims:
            s = silver_rows[c["claim_id"]]
            row = {"checked": "x", "claim_id": c["claim_id"], **{k: s.get(k, "") for k in slots},
                   "speaker_type": s.get("speaker_type", ""), "note": s.get("note", ""), "label_source": "silver"}
            if h := adj.get(c["claim_id"]):
                row |= {k: "" for k in slots} | {k: h.get(k, "") for k in slots if k in h}
                row |= {"note": h["note"], "label_source": f"human_adjudicated: {h['human_answer']}"}
            w.writerow(row)
    print(f"{len(claims)} rows -> {out} ({len(adj)} human-adjudicated, rest silver)")
    sys.exit()
silver = {r["claim_id"]: r for r in csv.DictReader((ROOT / "data/silver_sheet.csv").open(encoding="utf-8-sig"))} \
    if a.prefill == "silver" else {}

dst = ROOT / "data/gold_sheet.csv"
if dst.exists() and any(r.get("checked") for r in csv.DictReader(dst.open(encoding="utf-8-sig"))):
    sys.exit("gold_sheet.csv already has checked rows; refusing to overwrite human labels")
with dst.open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=["checked", "disagree"] + cols + slots + ["speaker_type", "note", "prefill"])
    w.writeheader()
    for c in claims:
        row = {k: safe(c[k]) for k in cols} | {"disagree": disagree(c["claim_id"]), "prefill": a.prefill}
        if a.prefill == "silver":  # labels only; `checked` stays empty until a person saves the row
            s = silver.get(c["claim_id"], {})
            row |= {k: s.get(k, "") for k in slots + ["speaker_type", "note"]}
        else:
            for i, x in enumerate(regex.get(c["claim_id"], [])[:3], 1):
                row |= {f"indicator{i}": x["indicator"], f"period{i}": x["period"] or "",
                        f"value{i}": x.get("text") or x["value"]}
        w.writerow(row)
print(f"{len(claims)} rows -> data/gold_sheet.csv (prefill: {a.prefill})")
