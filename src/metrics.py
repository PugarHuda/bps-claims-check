"""Score every results/extract_*.jsonl against the human gold sheet -> results/metrics.md

Uses only gold rows marked `checked`. Verdicts are recomputed from the CURRENT bps_reference.csv
(stored verdicts are ignored), so fixing the reference table never needs a model rerun.

Alignment unit: (claim_id, indicator, value). Period is deliberately not in the key, so a wrong
period shows up as a verdict disagreement instead of a missed + a spurious tuple.
Label NONE = "not extracted" on that side.
"""
import csv, glob, json, random, re, sys
from collections import Counter
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline as p  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")  # Windows console is cp1252; reports contain κ, ≥, →

LABELS = ["MATCH", "MISMATCH", "UNVERIFIABLE"]


def key(cid, c):
    return cid, c["indicator"], Decimal(c.get("text") or repr(c["value"])).normalize()


def duplicate_ids():
    """Same sentence scraped twice (syndication / repeated paragraph): count it once."""
    seen, dup = set(), set()
    for c in p.load_claims():
        if c["sentence"] in seen:
            dup.add(c["claim_id"])
        seen.add(c["sentence"])
    return dup


def load_gold(path=None):
    gold, meta, dup = {}, {}, duplicate_ids()
    claims = {c["claim_id"]: c for c in p.load_claims()}  # sentence/url for sheets that only carry labels
    for r in csv.DictReader(Path(path or p.ROOT / "data/gold_sheet.csv").open(encoding="utf-8-sig")):
        r = {**{k: v for k, v in r.items() if v is not None}, **claims.get(r["claim_id"], {})}  # text from source
        if not r["checked"].strip() or r["claim_id"] in dup:
            continue
        gold[r["claim_id"]] = p.clean([{"indicator": r[f"indicator{i}"].strip(), "period": r[f"period{i}"].strip(),
                                        "value": r[f"value{i}"].strip()} for i in (1, 2, 3)])
        meta[r["claim_id"]] = r
    return gold, meta


def load_pred(path):
    dup = duplicate_ids()
    return {d["claim_id"]: d["claims"] for d in map(json.loads, Path(path).open(encoding="utf-8"))
            if d["claim_id"] not in dup}


def kappa(pairs):
    """Cohen's kappa over (label_a, label_b) pairs."""
    n = len(pairs)
    if not n:
        return float("nan")
    po = sum(a == b for a, b in pairs) / n
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    pe = sum(ca[k] * cb[k] for k in ca) / n / n
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def agreement(a, b, ref):
    """Verdict-level kappa between two {claim_id: claims} sets on claims both processed (no gold needed)."""
    ids = [cid for cid in a if cid in b]
    x, y = labelled(a, ref, ids), labelled(b, ref, ids)
    return kappa([(x.get(k, "NONE"), y.get(k, "NONE")) for k in set(x) | set(y)]), len(ids)


def labelled(claims_by_id, ref, ids):
    out = {}
    for cid in ids:
        for c in claims_by_id.get(cid, []):
            # e2e ablation rows carry the LLM's own verdict; everything else is judged deterministically
            out.setdefault(key(cid, c), c.get("llm_verdict") or p.verdict(c, ref)[0])  # dup tuple: keep first
    return out


def score(gold, pred, ref):
    """gold/pred: {claim_id: [claim dicts]}. Scored on gold ids the model actually processed."""
    ids = [cid for cid in gold if cid in pred]
    g, q = labelled(gold, ref, ids), labelled(pred, ref, ids)
    keys = set(g) | set(q)
    pairs = [(g.get(k, "NONE"), q.get(k, "NONE")) for k in keys]
    tp_ext = len(set(g) & set(q))
    prec = tp_ext / len(q) if q else 0.0
    rec = tp_ext / len(g) if g else 0.0
    f1s = []
    for lab in LABELS:
        tp = sum(a == b == lab for a, b in pairs)
        fp = sum(b == lab != a for a, b in pairs)
        fn = sum(a == lab != b for a, b in pairs)
        f1s.append(2 * tp / (2 * tp + fp + fn) if tp else 0.0)
    return {
        "claims_scored": len(ids),
        "extract_p": prec, "extract_r": rec, "extract_f1": 2 * prec * rec / (prec + rec) if prec + rec else 0.0,
        "verdict_acc": sum(a == b for a, b in pairs) / len(pairs) if pairs else 0.0,
        "verdict_macro_f1": sum(f1s) / len(f1s),
        # the costly error for a fact-checker: accusing an official of a wrong number they didn't get wrong
        "false_mismatch": sum(b == "MISMATCH" != a for a, b in pairs),
        "missed_mismatch": sum(a == "MISMATCH" != b for a, b in pairs),
        "confusion": Counter(pairs),
    }


def headline(gold, ref):
    lab = labelled(gold, ref, gold)
    c = Counter(lab.values())
    return c, c["MATCH"] + c["MISMATCH"], lab


def rates(gold, ref):
    c, bind, _ = headline(gold, ref)
    n = sum(c.values())
    return {"bindable": bind / n if n else float("nan"), "mismatch": c["MISMATCH"] / bind if bind else float("nan")}


def resample(d, draw):
    """Same sentence drawn twice must count twice: suffix ids so dict keys stay distinct."""
    return {f"{cid}#{i}": d[cid] for i, cid in enumerate(draw) if cid in d}


def bootstrap(ids, stat, B=2000, seed=16):
    """95% percentile CI, resampling SENTENCES (the unit we sampled). stat(draw) gets a list of ids."""
    rng = random.Random(seed)
    ids, vals = list(ids), []
    for _ in range(B):
        v = stat([rng.choice(ids) for _ in ids])
        if v == v:  # drop NaN draws (e.g. nothing bindable in that resample)
            vals.append(v)
    vals.sort()
    return (vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals)) - 1]) if vals else (float("nan"),) * 2


def ci(ids, stat, pct=True):
    lo, hi = bootstrap(ids, stat)
    return f"[{lo:.1%}, {hi:.1%}]" if pct else f"[{lo:.2f}, {hi:.2f}]"


# ---------- variants: "right number, wrong frame" ----------
FAMILY = {"inflation_yoy": ("inflation_mtm", "inflation_ytd"), "gdp_growth_yoy": ("gdp_growth_qoq", "gdp_growth_ctc")}


def load_variants():
    f = p.ROOT / "data/bps_variants.csv"
    if not f.exists():
        return {}
    return {(r["indicator"], r["period"]): float(r["value"]) for r in csv.DictReader(f.open(encoding="utf-8-sig"))}


def frame_of(c, variants):
    """For a MISMATCH tuple: the variant (mtm/ytd/q-to-q/c-to-c) whose official value the claim matches, if any."""
    for v in FAMILY.get(c["indicator"], ()):
        if (v, c["period"]) in variants and p.verdict({**c, "indicator": v}, {(v, c["period"]): variants[(v, c["period"])]})[0] == "MATCH":
            return v
    return None


# ---------- error taxonomy ----------
CUES = [("mtm read as y-on-y", r"m-to-m|\bmtm\b|month[- ]to[- ]month|secara bulanan|bulan sebelumnya"),
        ("ytd read as y-on-y", r"y-to-d|\bytd\b|year[- ]to[- ]date|tahun kalender"),
        ("q-to-q / c-to-c read as y-on-y", r"q-to-q|\bqtq\b|triwulan sebelumnya|c-to-c|kumulatif"),
        ("core / component inflation", r"\binti\b|harga diatur|bergejolak|volatile|komponen|pangan"),
        # (?-i:...) keeps the place-name cue case-sensitive although the search runs with re.I
        ("regional figure", r"provinsi|kabupaten|\bkota\b|perkotaan|perdesaan|tertinggi|terendah"
                            r"|(?-i:\bdi (?!Indonesia\b|RI\b)[A-Z][a-z]+)"),
        ("target / projection", r"target|menargetkan|dipatok|mematok|sasaran|proyeksi|memproyeksikan|diperkirakan"
                                r"|memperkirakan|prakiraan|asumsi|outlook|kisaran|\bakan\b")]


VARIANT_CAUSE = {"inflation_mtm": "mtm read as y-on-y", "inflation_ytd": "ytd read as y-on-y",
                 "gdp_growth_qoq": "q-to-q / c-to-c read as y-on-y", "gdp_growth_ctc": "q-to-q / c-to-c read as y-on-y"}


def taxonomy(gold, pred, ref, sentences, variants=None):
    """One cause per disagreement between gold and a system (same alignment as score()).
    A spurious tuple whose value equals a published variant (m-to-m, y-to-d, ...) is attributed to that frame
    even when the sentence carries no textual cue: the data says which statistic the number is."""
    variants = load_variants() if variants is None else variants
    ids = [cid for cid in gold if cid in pred]
    out = Counter()
    for cid in ids:
        g = {key(cid, c): c for c in gold[cid]}
        q = {key(cid, c): c for c in pred[cid]}
        s = sentences.get(cid, "")
        for k in set(g) | set(q):
            if k in g and k in q:
                if g[k]["period"] != q[k]["period"]:
                    out["wrong period"] += 1
                continue
            if k in g:  # gold has it, the system doesn't
                if not any(c["indicator"] == g[k]["indicator"] and key(cid, c) not in g for c in pred[cid]):
                    out["missed claim"] += 1
                continue  # else: the system read a different number for this indicator, counted once below
            # spurious tuple: system extracted a figure gold says is out of scope. Find the cue near it.
            pos = s.replace(",", ".").find(q[k].get("text", ""))
            window = s[max(0, pos - 120):pos] if pos >= 0 else s
            frame = frame_of(q[k], variants) if q[k]["period"] else None
            cause = VARIANT_CAUSE[frame] if frame else next((name for name, cue in CUES if re.search(cue, window, re.I)), None)
            if cause is None and any(c["indicator"] == q[k]["indicator"] for c in gold[cid]):
                cause = "wrong value"  # counted on the spurious side only, so it isn't double-counted above
            out[cause or "other out-of-scope figure"] += 1
    return out


def strata(meta):
    """Sentence-level grouping variables. speaker_type comes from the annotator; the rest is deterministic."""
    return {"speaker_type": lambda cid: meta[cid].get("speaker_type") or "(unlabelled)",
            "source": lambda cid: "government (.go.id)" if ".go.id" in meta[cid]["url"] else "news media",
            "attributes BPS in sentence": lambda cid: "yes" if "BPS" in meta[cid]["sentence"] else "no"}


def ungrounded(pred, only=None):
    """Tuples whose number does not occur in the sentence or the preceding one: hallucinated, or (batched
    prompts) answered for another item. Computed the same way for every system, old runs included."""
    rows = {c["claim_id"]: c for c in p.load_claims()}
    return sum(not p.grounded(c, rows[cid]) for cid, cl in pred.items() if only is None or cid in only for c in cl)


def pregold(ref):
    """What can be said without human labels: verdict mix per system, how many of each system's MISMATCHes are
    exactly another published variant (right number, wrong frame), and system-system agreement."""
    variants = load_variants()
    preds = {Path(f).stem.removeprefix("extract_"): load_pred(f)
             for f in sorted(glob.glob(str(p.ROOT / "results/extract_*.jsonl")))}
    L = ["# No-gold report (system outputs only — NOT accuracy)\n",
         f"Reference table {len(ref)} rows; variant table {len(variants)} rows. Duplicates dropped: {len(duplicate_ids())}.\n",
         "| system | sentences | tuples | MATCH | MISMATCH | of which = another published variant | UNVERIFIABLE | values not in sentence |",
         "|---|---|---|---|---|---|---|---|"]
    for name, pred in preds.items():
        c, framed = Counter(), Counter()
        for cid, cl in pred.items():
            for x in cl:
                v = x.get("llm_verdict") or p.verdict(x, ref)[0]
                c[v] += 1
                if v == "MISMATCH" and (f := frame_of(x, variants)):
                    framed[f] += 1
        L.append(f"| {name} | {len(pred)} | {sum(c.values())} | {c['MATCH']} | {c['MISMATCH']} | "
                 f"{sum(framed.values())} ({', '.join(f'{k} {v}' for k, v in framed.items()) or '–'}) | {c['UNVERIFIABLE']} | {ungrounded(pred)} |")
    names = list(preds)
    L += ["\n## Verdict agreement (Cohen's κ; n = sentences both systems processed)\n",
          "| | " + " | ".join(names) + " |", "|---" * (len(names) + 1) + "|"]
    for x in names:
        L.append(f"| {x} | " + " | ".join("{:.2f} (n={})".format(*agreement(preds[x], preds[y], ref)) for y in names) + " |")
    out = p.ROOT / "results/pregold_metrics.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(out.read_text(encoding="utf-8"))


SILVER = p.ROOT / "data/silver_sheet.csv"  # blind Claude Opus annotation (an LLM, NOT a human)


def main(gold_path=None, out_name="metrics.md", label="human gold"):
    ref = p.load_ref()
    gold, meta = load_gold(gold_path)
    if not gold:
        print("no `checked` rows in the gold sheet yet -> writing the no-gold report only")
        return pregold(ref)
    variants = load_variants()
    c, bind, lab = headline(gold, ref)
    n = sum(c.values())
    with_claims = sum(1 for cid in gold if gold[cid])
    L = [f"# Metrics — reference labels: {label}\n",
         *(["> **Provisional.** These labels come from a blind LLM annotator (Claude Opus), not a person. "
            "Use them for coverage only; the human-gold report is `results/metrics.md`.\n"] if label != "human gold" else []),
         f"Labels: {len(gold)} checked sentences ({len(duplicate_ids())} duplicate sentences dropped), {with_claims} with "
         f"≥1 in-scope claim, {n} claim tuples. Reference table: {len(ref)} rows; variant table: {len(variants)} rows. "
         "CIs: 95% bootstrap over sentences (2,000 resamples).\n",
         f"## Headline ({label})\n"]
    if n:
        L.append(f"- Bindable rate (claim resolves to a BPS figure): **{bind}/{n} = {bind / n:.1%}** "
                 f"{ci(gold, lambda d: rates(resample(gold, d), ref)['bindable'])}")
    if bind:
        L.append(f"- Mismatch rate among bindable: **{c['MISMATCH']}/{bind} = {c['MISMATCH'] / bind:.1%}** "
                 f"{ci(gold, lambda d: rates(resample(gold, d), ref)['mismatch'])}")
    L.append(f"- Unverifiable: {c['UNVERIFIABLE']}")
    mism = [(k, next(x for x in gold[k[0]] if key(k[0], x) == k)) for k, v in lab.items() if v == "MISMATCH"]
    framed = Counter(frame_of(x, variants) for _, x in mism)
    if mism:
        L.append(f"- Of {len(mism)} MISMATCHes, **right number, wrong frame** (claim equals another published "
                 f"variant of the same release): " + (", ".join(f"{v}: {k}" for v, k in framed.items() if v) or "none")
                 + f"; wrong number: {framed[None]}" + ("" if variants else " (variant table not available)"))
    by_ind = Counter((k[1], v) for k, v in lab.items())
    L += ["\n| indicator | MATCH | MISMATCH | UNVERIFIABLE |", "|---|---|---|---|"]
    for ind in p.INDICATORS:
        L.append(f"| {ind} | " + " | ".join(str(by_ind[(ind, x)]) for x in LABELS) + " |")
    for name, fn in strata(meta).items():
        L += [f"\n### By {name}\n", "| group | sentences | tuples | bindable | mismatch among bindable |", "|---|---|---|---|---|"]
        for grp in sorted({fn(cid) for cid in gold}):
            sub = {cid: v for cid, v in gold.items() if fn(cid) == grp}
            cc, bb, _ = headline(sub, ref)
            nn = sum(cc.values())
            L.append(f"| {grp} | {len(sub)} | {nn} | {bb}/{nn} = {bb / nn:.0%} | " if nn else f"| {grp} | {len(sub)} | 0 | – | ")
            if nn:
                L[-1] += f"{cc['MISMATCH']}/{bb} = {cc['MISMATCH'] / bb:.0%} |" if bb else "– |"
            else:
                L[-1] += "– |"

    L += ["\n## Systems vs gold\n",
          "`__e2e` = the LLM gave the verdict itself with the BPS table in its prompt (ablation); every other row: "
          "LLM/rules extract, deterministic lookup decides. Systems that did not process every gold sentence are "
          "scored on the ones they did (see 'scored').\n",
          "| system | scored | extract P | extract R | extract F1 | verdict acc | verdict macro-F1 [95% CI] | false MISMATCH | missed MISMATCH | values not in sentence |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    conf, tax = [], []
    sentences = {cid: meta[cid]["sentence"] for cid in meta}
    preds = {Path(f).stem.removeprefix("extract_"): load_pred(f)
             for f in sorted(glob.glob(str(p.ROOT / "results/extract_*.jsonl")))}
    for name, pred in preds.items():
        s = score(gold, pred, ref)
        sub = [cid for cid in gold if cid in pred]
        f1ci = ci(sub, lambda d: score(resample(gold, d), resample(pred, d), ref)["verdict_macro_f1"], pct=False) if sub else ""
        L.append(f"| {name} | {s['claims_scored']}/{len(gold)} | {s['extract_p']:.2f} | {s['extract_r']:.2f} | "
                 f"{s['extract_f1']:.2f} | {s['verdict_acc']:.2f} | {s['verdict_macro_f1']:.2f} {f1ci} | "
                 f"{s['false_mismatch']} | {s['missed_mismatch']} | {ungrounded(pred, gold)} |")
        conf.append(f"\n### {name} (rows = gold, cols = system)\n\n| | " + " | ".join(LABELS + ["NONE"]) + " |\n"
                    + "|---" * 5 + "|")
        for a in LABELS + ["NONE"]:
            conf.append(f"| **{a}** | " + " | ".join(str(s["confusion"][(a, b)]) for b in LABELS + ["NONE"]) + " |")
        t = taxonomy(gold, pred, ref, sentences)
        tax.append((name, t))
    causes = sorted({k for _, t in tax for k in t}, key=lambda k: -sum(t[k] for _, t in tax))
    L += ["\n## Error taxonomy (one cause per disagreement with gold)\n",
          "| system | " + " | ".join(causes) + " |", "|---" * (len(causes) + 1) + "|"]
    L += [f"| {name} | " + " | ".join(str(t[k]) for k in causes) + " |" for name, t in tax]
    names = list(preds)
    L += ["\n## Model–model agreement (verdict-level Cohen's κ on claims both processed; no gold needed)\n",
          "| | " + " | ".join(names) + " |", "|---" * (len(names) + 1) + "|"]
    for x in names:
        L.append(f"| {x} | " + " | ".join(f"{agreement(preds[x], preds[y], ref)[0]:.2f}" for y in names) + " |")
    second = p.ROOT / "data/gold_sheet_2.csv"  # a second HUMAN annotator, if one ever labels
    if second.exists():
        k, n2 = agreement(gold, load_gold(second)[0], ref)
        L.append(f"\n**Inter-annotator κ (human vs human)**, {n2} sentences labelled by both: **{k:.2f}**")
    if label == "human gold" and SILVER.exists():
        k, n2 = agreement(gold, load_gold(SILVER)[0], ref)
        L.append(f"\n**Human vs LLM-annotator κ** (gold vs blind Claude Opus labels, {n2} sentences): **{k:.2f}** — "
                 "how far LLM silver labels can stand in for human ones on this task")
    L += ["\n## Confusion matrices"] + conf
    out = p.ROOT / "results" / out_name
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", help="gold sheet (default data/gold_sheet.csv)")
    ap.add_argument("--out", default="metrics.md", help="file name under results/")
    ap.add_argument("--silver", action="store_true", help="score against data/silver_sheet.csv -> silver_metrics.md")
    a = ap.parse_args()
    if a.silver:
        main(SILVER, "silver_metrics.md", "silver (blind Claude Opus annotator, not human-verified)")
    else:
        main(a.gold, a.out)
