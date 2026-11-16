"""Report figures -> figs/*.png (static, light theme, for the PDF).

  uv run python src/figures.py

Figures that need human gold are skipped (with a message) until data/gold_sheet.csv has `checked` rows.
Palette: reference dataviz palette; verdict pair blue/orange validated (CVD ΔE 24.7, normal 33.6),
UNVERIFIABLE in neutral ink so only the two real verdicts carry hue. Sequential = one blue ramp.
"""
import glob, sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import metrics as m  # noqa: E402
import perturb  # noqa: E402

p = m.p
OUT = p.ROOT / "figs"
SURFACE, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
VERDICT = {"MATCH": "#2a78d6", "MISMATCH": "#eb6834", "UNVERIFIABLE": "#c3c2b7"}
SEQ = LinearSegmentedColormap.from_list("seq", ["#f4f8fd", "#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])
SHORT = {"baidu__ernie-5.5-flash-preview_free": "ERNIE 5.5 Flash",
         "nvidia__nemotron-3-ultra-550b-a55b_free": "Nemotron-3 Ultra",
         "liquid__lfm-3-1.7b_free": "LFM-3 1.7B", "regex": "regex (naive)", "rules": "rules"}

plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
                     "text.color": INK, "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": INK2,
                     "axes.edgecolor": AXIS, "font.size": 9, "axes.titlesize": 10, "axes.titleweight": "bold",
                     "axes.spines.top": False, "axes.spines.right": False})


def short(name):
    base, _, rest = name.partition("__e2e")
    return SHORT.get(base, base) + (" · e2e judge" if _ else "") + rest.replace("__", " · ")


def heat(ax, rows, cols, M, fmt, title, vmax=None):
    im = ax.imshow(M, cmap=SEQ, vmin=0, vmax=vmax or max(max(r) for r in M) or 1, aspect="auto")
    ax.set_xticks(range(len(cols)), cols, rotation=30, ha="right")
    ax.set_yticks(range(len(rows)), rows)
    top = vmax or max(max(r) for r in M) or 1
    for i, r in enumerate(M):
        for j, v in enumerate(r):
            ax.text(j, i, fmt(v), ha="center", va="center", fontsize=8, color="#ffffff" if v > 0.55 * top else INK)
    ax.set_title(title, loc="left")
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    return im


def save(fig, name):
    OUT.mkdir(exist_ok=True)
    fig.savefig(OUT / name, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("wrote", OUT / name)


def fig_agreement():
    ref = p.load_ref()
    preds = {Path(f).stem.removeprefix("extract_"): m.load_pred(f)
             for f in sorted(glob.glob(str(p.ROOT / "results/extract_*.jsonl")))
             if "persentence" not in f}
    names = [n for n in preds if "lfm" not in n]  # LFM covers 38/166 only; its kappa would compare different sets
    M = [[m.agreement(preds[a], preds[b], ref)[0] for b in names] for a in names]
    fig, ax = plt.subplots(figsize=(5.2, 4.2))
    heat(ax, [short(n) for n in names], [short(n) for n in names], M, lambda v: f"{v:.2f}",
         "Verdict agreement between systems (Cohen's κ, no gold)", vmax=1)
    save(fig, "agreement_kappa.png")


def fig_perturbation():
    systems, exp = perturb.score()
    kinds = ["exact", "rounded_1dp", "truncated_1dp", "last_digit_plus1", "off_by_0.5", "wrong_period", "absent_period"]
    rows, M = [], []
    for name, got in systems.items():
        ids = [c for c in exp if c in got]
        if not ids:
            continue
        rows.append("oracle (true tuple)" if name.startswith("oracle") else short(name))
        M.append([sum(got[c] == exp[c]["expected"] for c in ids if exp[c]["kind"] == k)
                  / max(1, sum(exp[c]["kind"] == k for c in ids)) for k in kinds])
    if all(v == 1 for r in M for v in r):  # a wall of 100% says nothing a sentence can't
        print(f"skip perturbation figure: all {len(rows)} systems scored 100% on every kind (state it in text)")
        (OUT / "perturbation.png").unlink(missing_ok=True)
        return
    fig, ax = plt.subplots(figsize=(7.2, 0.5 * len(rows) + 1.6))
    heat(ax, rows, kinds, M, lambda v: f"{v:.0%}", "Synthetic perturbations: share judged correctly", vmax=1)
    save(fig, "perturbation.png")


def fig_gold():
    ref = p.load_ref()
    gold, meta = m.load_gold()
    if not gold:
        print("skip gold figures: no checked rows in data/gold_sheet.csv yet")
        return
    _, _, lab = m.headline(gold, ref)
    from collections import Counter
    by = Counter((k[1], v) for k, v in lab.items())
    inds = [i for i in p.INDICATORS if any(by[(i, v)] for v in VERDICT)]
    fig, ax = plt.subplots(figsize=(6.4, 0.55 * len(inds) + 1.2))
    left = [0] * len(inds)
    for v, col in VERDICT.items():
        vals = [by[(i, v)] for i in inds]
        bars = ax.barh(range(len(inds)), vals, left=left, color=col, height=0.55, edgecolor=SURFACE, linewidth=2, label=v)
        for b, val in zip(bars, vals):
            if val:
                ax.text(b.get_x() + b.get_width() / 2, b.get_y() + b.get_height() / 2, str(val), ha="center",
                        va="center", fontsize=8, color="#ffffff" if v != "UNVERIFIABLE" else INK)
        left = [a + b for a, b in zip(left, vals)]
    ax.set_yticks(range(len(inds)), inds)
    ax.invert_yaxis()
    ax.set_xlabel("claim tuples (human gold)")
    ax.grid(axis="x", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, ncols=3, loc="lower left", bbox_to_anchor=(0, 1.0))
    ax.set_title("Verdict per indicator", loc="left", pad=22)
    save(fig, "verdict_by_indicator.png")

    files = [f for f in sorted(glob.glob(str(p.ROOT / "results/extract_*.jsonl"))) if "persentence" not in f]
    labs = m.LABELS + ["NONE"]
    cols = 3
    rows_n = -(-len(files) // cols)
    fig, axes = plt.subplots(rows_n, cols, figsize=(3.3 * cols, 2.9 * rows_n), squeeze=False)
    for ax, f in zip(axes.flat, files):
        s = m.score(gold, m.load_pred(f), ref)
        M = [[s["confusion"][(a, b)] for b in labs] for a in labs]
        heat(ax, [f"gold {x[:5]}" for x in labs], [x[:5] for x in labs], M, str, short(Path(f).stem.removeprefix("extract_")))
    for ax in list(axes.flat)[len(files):]:
        ax.axis("off")
    fig.tight_layout()
    save(fig, "confusion.png")


if __name__ == "__main__":
    fig_agreement()
    fig_perturbation()
    fig_gold()
