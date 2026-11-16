"""Claim -> (indicator, period, value) extraction -> deterministic BPS lookup -> verdict.

Usage:
  uv run python src/pipeline.py --model regex      # naive keyword baseline
  uv run python src/pipeline.py --model rules      # stronger rule baseline (scope cues, clause-level)
  uv run python src/pipeline.py --model anthropic/claude-sonnet-5.5 --limit 10
Writes results/extract_<model>.jsonl (resumable: already-done claim_ids are skipped).
"""
import argparse, csv, json, os, re, sys, time
from decimal import ROUND_HALF_UP, Decimal
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
INDICATORS = ["inflation_yoy", "unemployment_rate", "poverty_rate", "gdp_growth_yoy"]
MONTHS = {m: i + 1 for i, m in enumerate(
    "januari februari maret april mei juni juli agustus september oktober november desember".split())}

PROMPT = """You extract checkable statistical claims from Indonesian text for fact-checking against official BPS (Statistics Indonesia) data.

In scope are ONLY national-level (Indonesia-wide) values of these 4 indicators:
- inflation_yoy: headline CPI inflation, year-on-year (NOT month-to-month, NOT year-to-date unless it is December, NOT core/component/regional inflation)
- unemployment_rate: Tingkat Pengangguran Terbuka (TPT), percent (NOT number of unemployed people)
- poverty_rate: persentase penduduk miskin, national total (NOT urban/rural split, NOT extreme poverty, NOT number of people)
- gdp_growth_yoy: economic growth, year-on-year or annual (NOT q-to-q, NOT c-to-c cumulative semesters, NOT sectoral or consumption growth)

Return JSON: {"claims": [ {"indicator": ..., "period": ..., "value": ...}, ... ]}
- One entry per in-scope (indicator, value) asserted as an actual/realised figure. A sentence may contain 0, 1 or several.
- Skip targets, forecasts, projections, assumptions, ranges like "2,5 plus minus 1 persen", and figures for other countries.
- period format: "YYYY-MM" for a monthly figure (inflation; TPT/poverty use the survey month, e.g. TPT Agustus 2025 -> "2025-08"), "YYYY-Qn" for a quarter, "YYYY" for a full year. Use the article date and preceding sentence to resolve relative references ("bulan lalu", "tahun ini"). If the period genuinely cannot be determined, use null.
- value: the number as stated (decimal comma -> dot), as a float, in percent.

Article date: {date}
Preceding sentence: {prev}
Sentence: {sentence}"""

# ponytail: free tier = 50 req/day, so N claims share one request; same rules, different wrapper.
_head, _rules = PROMPT.split("Return JSON:")
BATCH_PROMPT = _head + "Rules for each item:\n" + _rules.split("Article date:")[0].split("\n", 1)[1] + """
You get several items, each tagged [claim_id]. Judge each independently.
Return JSON: {"results": [ {"claim_id": "...", "claims": [ {"indicator": ..., "period": ..., "value": ...} ]}, ... ]} with one entry per item, in order, even when its claims list is empty.

"""

# Ablation: the LLM also judges the verdict itself, given the whole evidence table in the prompt.
E2E_PROMPT = BATCH_PROMPT.replace(
    '{"indicator": ..., "period": ..., "value": ...}',
    '{"indicator": ..., "period": ..., "value": ..., "verdict": "MATCH" | "MISMATCH" | "UNVERIFIABLE"}') + """Verdict rules: look up (indicator, period) in the official BPS table below. MATCH if the official value,
rounded half-up to the number of decimals the claim states, equals the claim; MISMATCH otherwise;
UNVERIFIABLE if the period is unknown or the (indicator, period) row is not in the table.

Official BPS table (indicator,period,value):
{table}

"""


def load_claims(path=None):
    return list(csv.DictReader(Path(path or ROOT / "data/claims_raw.csv").open(encoding="utf-8-sig")))


def load_ref():
    return {(r["indicator"], r["period"]): float(r["value"])
            for r in csv.DictReader((ROOT / "data/bps_reference.csv").open(encoding="utf-8-sig"))}


# ---------- extractors ----------

def secret(name):
    """Environment first, then a local .env (git-ignored) with NAME=value lines."""
    if name in os.environ:
        return os.environ[name]
    env = ROOT / ".env"
    for line in env.read_text(encoding="utf-8").splitlines() if env.exists() else []:
        k, _, v = line.partition("=")
        if k.strip() == name:
            return v.strip().strip('"')
    raise KeyError(f"{name} not set (environment or .env)")


def endpoint(model):
    """'gemini/<id>' -> Google AI Studio's OpenAI-compatible API (free tier, GEMINI_API_KEY); else OpenRouter."""
    if model.startswith("gemini/"):
        return ("https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                secret("GEMINI_API_KEY"), model.split("/", 1)[1])
    return "https://openrouter.ai/api/v1/chat/completions", secret("OPENROUTER_API_KEY"), model


def extract_batch(model, rows, effort=None, e2e=False):
    """-> ({claim_id: claims}, err). Ids missing from the reply aren't written, so a rerun retries them."""
    table = "\n".join(f"{i},{per},{v}" for (i, per), v in sorted(load_ref().items()))
    msg = (E2E_PROMPT.replace("{table}", table) if e2e else BATCH_PROMPT) +"\n\n".join(
        f"[{r['claim_id']}]\nArticle date: {r['article_date'] or 'unknown'}\n"
        f"Preceding sentence: {r['context_prev'][:500]}\nSentence: {r['sentence']}" for r in rows)
    for attempt in range(5):  # free providers 429 a lot; back off and retry
        got, err = _batch_once(model, msg, effort)
        if not err or "429" not in err:
            return got, err
        time.sleep(30 * (attempt + 1))
    return got, err


def _batch_once(model, msg, effort=None):
    try:
        url, key, model_id = endpoint(model)
        r = requests.post(url, timeout=600, headers={"Authorization": f"Bearer {key}"},
                          json={"model": model_id, "temperature": 0, "max_tokens": 16000,
                                "messages": [{"role": "user", "content": msg}],
                                # small reasoning models burn the budget thinking (finish_reason=length)
                                **({"reasoning": {"effort": effort}} if effort else {})})
        r.raise_for_status()
        ch = r.json()["choices"][0]
        text = ch["message"]["content"]
        if not text:  # reasoning models can spend the whole budget thinking
            raise ValueError(f"empty content, finish_reason={ch.get('finish_reason')}")
        res = json.loads(re.search(r"\{.*\}", text, re.S).group(0), parse_float=str)["results"]
        return {x["claim_id"]: clean(x.get("claims")) for x in res if isinstance(x, dict) and x.get("claim_id")}, None
    except Exception as e:
        return {}, f"{type(e).__name__}: {str(e)[:300]}"

def extract_llm(model, row):
    msg = PROMPT.replace("{date}", row["article_date"] or "unknown") \
        .replace("{prev}", row["context_prev"][:500]).replace("{sentence}", row["sentence"])
    err = "429 after retries"
    for attempt in range(5):  # same 429 backoff as batched mode; no response_format (not all free models take it)
        try:
            url, key, model_id = endpoint(model)
            r = requests.post(url, timeout=300, headers={"Authorization": f"Bearer {key}"},
                              json={"model": model_id, "temperature": 0, "max_tokens": 4000,
                                    "messages": [{"role": "user", "content": msg}]})
            if r.status_code == 429:
                time.sleep(30 * (attempt + 1))
                continue
            r.raise_for_status()
            text = r.json()["choices"][0]["message"]["content"] or ""
            m = re.search(r"\{.*\}", text, re.S)
            return clean(json.loads(m.group(0), parse_float=str)["claims"]), None
        except Exception as e:
            return [], f"{type(e).__name__}: {str(e)[:200]}"
    return [], err


def extract_regex(row):
    """Baseline: keyword -> indicator, first 'N persen' -> value, explicit month/quarter/year -> period."""
    s = row["sentence"]
    low = s.lower()
    ind = ("unemployment_rate" if re.search(r"pengangguran|\btpt\b", low) else
           "poverty_rate" if "miskin" in low else
           "inflation_yoy" if "inflasi" in low else
           "gdp_growth_yoy" if re.search(r"tumbuh|pertumbuhan", low) else None)
    num = re.search(r"(\d+(?:,\d+)?)\s*(?:persen|%)", s, re.I)
    if not ind or not num:
        return [], None
    period = None
    if m := re.search(r"(" + "|".join(MONTHS) + r")\s+(20\d\d)", low):
        period = f"{m.group(2)}-{MONTHS[m.group(1)]:02d}"
    elif m := re.search(r"(?:triwulan|kuartal)\s*(i{1,3}v?|iv|[1-4])\s*[-/ ]?\s*(?:tahun\s*)?(20\d\d)", low):
        q = {"i": 1, "ii": 2, "iii": 3, "iv": 4}.get(m.group(1), m.group(1))
        period = f"{m.group(2)}-Q{q}"
    elif m := re.search(r"(?:tahun|sepanjang)\s+(20\d\d)", low):
        period = m.group(1)
    return clean([{"indicator": ind, "period": period, "value": num.group(1).replace(",", ".")}]), None


# ---------- strong rule baseline ----------
# ponytail: hand-written cues from the scope definition only (no peeking at model outputs or gold).
MONTH_RE = "|".join(MONTHS)
IND_CUES = [("unemployment_rate", r"pengangguran|\btpt\b"), ("poverty_rate", r"miskin|kemiskinan"),
            ("inflation_yoy", r"inflasi"), ("gdp_growth_yoy", r"ekonomi\b.{0,40}tumbuh|pertumbuhan ekonomi|\bpdb\b")]
OUT_OF_SCOPE = re.compile(
    r"m-to-m|\bmtm\b|month[- ]to[- ]month|secara bulanan|dibanding(?:kan)? bulan sebelumnya|bulan ke bulan"
    r"|y-to-d|\bytd\b|year[- ]to[- ]date|tahun kalender|q-to-q|\bqtq\b|dibanding(?:kan)? triwulan sebelumnya"
    r"|kuartal ke kuartal|c-to-c|\bctc\b|kumulatif|\binti\b|harga diatur|bergejolak|volatile|komponen"
    r"|provinsi|kabupaten|\bkota\b|perkotaan|perdesaan|ekstrem"
    r"|target|sasaran|proyeksi|diproyeksikan|diperkirakan|prakiraan|asumsi|outlook|kisaran|diharapkan"
    r"|ditargetkan|menargetkan|dipatok|mematok|memproyeksikan|memperkirakan|\bakan\b", re.I)  # me-+t elides the t
REGIONAL = re.compile(r"\bdi (?!Indonesia\b|RI\b|Tanah Air\b)[A-Z][a-z]+|tertinggi|terendah")  # case-sensitive
ROMAN = {"i": 1, "ii": 2, "iii": 3, "iv": 4}


def _period(text, ind, article_date, sent_year=None):
    low = text.lower()
    if m := re.search(rf"({MONTH_RE})\s+(20\d\d)", low):
        return f"{m.group(2)}-{MONTHS[m.group(1)]:02d}"
    if m := re.search(r"(?:triwulan|kuartal)\s*(iv|i{1,3}|[1-4])\b\s*[-/ ]?\s*(?:tahun\s*)?(20\d\d)", low):
        return f"{m.group(2)}-Q{ROMAN.get(m.group(1), m.group(1))}"
    y = article_date[:4] if article_date else None
    if m := re.search(rf"\b({MONTH_RE})\b", low):
        mm = MONTHS[m.group(1)]
        if sent_year:  # "Desember 2025 ... setelah November ..." -> the year the sentence states
            return f"{sent_year}-{mm:02d}"
        if y:  # else the most recent such month up to the article date
            return f"{int(y) - (mm > int(article_date[5:7]))}-{mm:02d}"
    if m := re.search(r"(?:tahun|sepanjang|selama)\s+(20\d\d)", low):
        return m.group(1)
    if y and ind == "inflation_yoy" and re.search(r"bulan lalu", low):
        yy, mm = int(y), int(article_date[5:7]) - 1
        return f"{yy - (mm == 0)}-{(mm or 12):02d}"
    return None


def extract_rules(row):
    """Stronger non-LLM baseline. Every 'N persen' takes the nearest preceding indicator cue in its clause,
    is dropped when that clause carries an out-of-scope cue (mtm/ytd/q-to-q/core/regional/target...), and
    gets a period from the clause, else the sentence, else relative to the article date."""
    s, out = row["sentence"], []
    for num in re.finditer(r"(-?\d+(?:,\d+)?)\s*(?:persen|%)", s, re.I):
        clause = re.split(r"[;:,]| dan | serta ", s[:num.start()])[-1][-160:]
        hits = [(m.end(), ind) for ind, cue in IND_CUES for m in re.finditer(cue, clause, re.I)]
        if not hits:  # list like "inflasi ... masing-masing 1,2 persen dan 1,5 persen": look further back
            hits = [(m.end(), ind) for ind, cue in IND_CUES for m in re.finditer(cue, s[:num.start()], re.I)]
        if not hits or OUT_OF_SCOPE.search(clause) or REGIONAL.search(clause):
            continue
        ind = max(hits)[1]
        date = row.get("article_date", "")
        sy = m.group(0) if (m := re.search(r"20\d\d", s)) else None
        period = _period(clause, ind, date, sy) or _period(s, ind, date, sy)
        out.append({"indicator": ind, "period": period, "value": num.group(1).replace(",", ".")})
    return clean(out), None


def clean(claims):
    out = []
    for c in claims or []:
        try:
            if c.get("indicator") not in INDICATORS or c.get("value") in (None, ""):
                continue
            text = str(c["value"]).strip().replace(",", ".")  # keep stated precision: "5.0" != "5"
            out.append({"indicator": c["indicator"], "period": c.get("period") or None,
                        "value": float(text), "text": text}
                       | ({"llm_verdict": c["verdict"]} if c.get("verdict") in ("MATCH", "MISMATCH", "UNVERIFIABLE") else {}))
        except (ValueError, TypeError, AttributeError):
            continue
    return out


# ---------- deterministic verdict ----------

def verdict(claim, ref):
    """MATCH if the official value, rounded to the claim's stated precision, equals the claim."""
    if not claim["period"]:
        return "UNVERIFIABLE", None
    key = (claim["indicator"], claim["period"])
    if key not in ref:
        return "UNVERIFIABLE", None
    official = ref[key]
    # Decimal + ROUND_HALF_UP: float round() gives round(5.05, 1) == 5.0, which would flag a correctly
    # rounded "5,1 persen" as MISMATCH. Precision = decimals the claim states.
    stated = Decimal(claim.get("text") or repr(float(claim["value"])))
    exp = Decimal(1).scaleb(min(stated.as_tuple().exponent, 0))
    ok = Decimal(repr(official)).quantize(exp, ROUND_HALF_UP) == stated
    return ("MATCH" if ok else "MISMATCH"), official


def run_batched(model, todo, ref, out, size, effort=None, e2e=False):
    with out.open("a", encoding="utf-8") as f:
        for i in range(0, len(todo), size):
            chunk = todo[i:i + size]
            got, err = extract_batch(model, chunk, effort, e2e)
            if err:
                print(f"batch {i}: {err}", file=sys.stderr)
            ids = {r["claim_id"] for r in chunk}
            for cid, cl in got.items():
                if cid not in ids:
                    continue
                for c in cl:
                    c["verdict"], c["official"] = verdict(c, ref)
                f.write(json.dumps({"claim_id": cid, "claims": cl, "error": None}, ensure_ascii=False) + "\n")
            f.flush()
            print(f"{model}: batch {i // size + 1}, {len(got)}/{len(chunk)} returned", file=sys.stderr)


def run(model, limit, workers, batch=0, effort=None, e2e=False, claims_path=None, out_dir="results", tag=""):
    claims = load_claims(claims_path)
    claims = claims[:limit] if limit else claims
    name = model.replace("/", "__").replace(":", "_") + ("__e2e" if e2e else "") + (f"__{tag}" if tag else "")
    out = ROOT / out_dir / f"extract_{name}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    done = {json.loads(l)["claim_id"] for l in out.open(encoding="utf-8")} if out.exists() else set()
    todo = [c for c in claims if c["claim_id"] not in done]
    ref = load_ref()
    if batch:
        return run_batched(model, todo, ref, out, batch, effort, e2e)
    fn = {"regex": extract_regex, "rules": extract_rules}.get(model) or (lambda row: extract_llm(model, row))
    errors = 0
    with out.open("a", encoding="utf-8") as f, ThreadPoolExecutor(1 if model in ("regex", "rules") else workers) as ex:
        for row, (cl, err) in zip(todo, ex.map(fn, todo)):
            if err:  # not written, so a rerun retries it
                errors += 1
                print(f"{row['claim_id']}: {err}", file=sys.stderr)
                continue
            for c in cl:
                c["verdict"], c["official"] = verdict(c, ref)
            f.write(json.dumps({"claim_id": row["claim_id"], "claims": cl, "error": err}, ensure_ascii=False) + "\n")
            f.flush()
    print(f"{model}: {len(todo)} new, {errors} errors -> {out}", file=sys.stderr)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--batch", type=int, default=0, help="claims per request (free-tier quota)")
    ap.add_argument("--reasoning-effort", choices=["low", "medium", "high"], help="batched mode only")
    ap.add_argument("--e2e", action="store_true", help="ablation: LLM gives the verdict itself (needs --batch)")
    ap.add_argument("--claims", help="claims CSV (default data/claims_raw.csv)")
    ap.add_argument("--out-dir", default="results")
    ap.add_argument("--tag", default="", help="output file suffix, e.g. 'persentence'")
    a = ap.parse_args()
    if a.e2e and not a.batch:
        ap.error("--e2e needs --batch")
    run(a.model, a.limit, a.workers, a.batch, a.reasoning_effort, a.e2e, a.claims, a.out_dir, a.tag)
