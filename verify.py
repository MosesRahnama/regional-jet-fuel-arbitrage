"""Offline reproducibility verifier (stdlib only).

  python verify.py    # check saved public outputs; no execution

Default verification reads saved public results, notebook JSON,
dashboard pages, key counts, the raw backtest schema, and the two
portfolio rows. No notebook replay. No acquisition, no network, no
publishing.
"""
import ast
import csv
import json
import math
import os
import sys
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "docs"))
from render_contract import validate_render  # production helper, side-effect free

FAIL = []
STEP_COLS = ["order", "id", "stage", "question", "why", "inputs", "method",
             "assumptions", "result", "interpretation", "conclusion", "source"]
STEP_PARTS = ["method", "why", "result", "interpretation"]
BT_COLS = ["spread", "model", "period", "weeks", "total_cents",
           "cents_per_year", "sharpe", "weeks_won", "worst_drawdown"]
WEST_ROW = {
    "spread": "WEST_COAST_3", "model": "f_fair_value",
    "period": "2017 to Feb 2020", "weeks": "163", "total_cents": "135.9",
    "cents_per_year": "43.4", "sharpe": "2.29", "weeks_won": "0.65",
    "worst_drawdown": "-12.5",
}
SHORT_ROW = {
    "spread": "SHORTLIST_4", "model": "f_fair_value",
    "period": "2017 to Feb 2020", "weeks": "163", "total_cents": "105.3",
    "cents_per_year": "33.6", "sharpe": "1.30", "weeks_won": "0.60",
    "worst_drawdown": "-33.5",
}
FDR_Q = 0.10
BH03_CUT = 0.0003762367445156
BH04_CUT = 0.0014440277566266


def check(name, cond, detail=""):
    print(("PASS " + name if cond else "FAIL " + name) + (f"  [{detail}]" if detail else ""))
    if not cond:
        FAIL.append(name)


def load_csv(path):
    try:
        with open(ROOT / path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except FileNotFoundError:
        check(f"file.{Path(path).stem}", False, f"missing {path}")
        return None


def fnum(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def fbool(x):
    return str(x).strip().lower() in ("true", "1", "yes")


def bh_cutoff(pvals, q):
    """Benjamini-Hochberg step-up: largest rank k with ranked[k-1] <= k*q/m."""
    ranked = sorted(pvals)
    m = len(ranked)
    k = 0
    for i, p in enumerate(ranked, 1):
        if p <= i * q / m:
            k = i
    return k, (ranked[k - 1] if k else -1.0)


def row_match(got, exp, keys):
    for k in keys:
        a, b = got.get(k), exp[k]
        if k in ("weeks", "spread", "model", "period"):
            if str(a).strip() != str(b):
                return False
        else:
            fa, fb = fnum(a), fnum(b)
            if fa is None or fb is None or abs(fa - fb) > 1e-9:
                return False
    return True


# ---------- A. required saved public files ----------
NEED = ["requirements.txt",
        "results/price_eda_scorecard.csv", "results/signal_search.csv",
        "results/fair_value_scores.csv", "results/backtest.csv",
        "results/nowcast_scores.csv", "results/miles_search.csv",
        "results/covid_first_signals.csv", "results/analysis_steps.csv",
        "docs/build_dashboard.py", "docs/render_contract.py",
        "docs/index.html", "docs/detail.html",
        "notebooks/01_price_eda.ipynb", "notebooks/02_fundamentals_panel.ipynb",
        "notebooks/03_signal_search.ipynb", "notebooks/04_air_traffic.ipynb"]
missing = [p for p in NEED if not (ROOT / p).exists()]
check("A.required-files", not missing, f"missing={missing}")

SS = load_csv("results/signal_search.csv")
BT = load_csv("results/backtest.csv")
FVS = load_csv("results/fair_value_scores.csv")
NOW = load_csv("results/nowcast_scores.csv")
MS = load_csv("results/miles_search.csv")
CF = load_csv("results/covid_first_signals.csv")
SC = load_csv("results/price_eda_scorecard.csv")
STEPS = load_csv("results/analysis_steps.csv")

# ---------- E. helper edge vector ----------
k, _ = bh_cutoff([0.025, 0.03, 0.2], 0.05)
pw = sum(1 for i, p in enumerate([0.025, 0.03, 0.2], 1) if p <= i * 0.05 / 3)
check("E.bh-stepup-rejects-two", k == 2 and pw == 1, f"pointwise={pw} stepup={k}")

# ---------- F. raw backtest schema and two portfolio rows ----------
if BT:
    check("F.backtest-schema-raw-only", list(BT[0].keys()) == BT_COLS,
          f"got={list(BT[0].keys())}")
    west = next((r for r in BT if r.get("spread") == "WEST_COAST_3"
                 and r.get("model") == "f_fair_value"
                 and r.get("period") == "2017 to Feb 2020"), None)
    short = next((r for r in BT if r.get("spread") == "SHORTLIST_4"
                  and r.get("model") == "f_fair_value"
                  and r.get("period") == "2017 to Feb 2020"), None)
    check("F.portfolio-west-coast-row",
          west is not None and row_match(west, WEST_ROW, BT_COLS),
          f"got={west}")
    check("F.portfolio-shortlist-row",
          short is not None and row_match(short, SHORT_ROW, BT_COLS),
          f"got={short}")

# ---------- G. scores, BH flags, nowcast, miles ----------
if SS:
    pv = [fnum(r["p_train"]) for r in SS]
    if any(p is None or not 0 <= p <= 1 for p in pv):
        check("G.bh-flags-match-saved-pvalues", False, "p_train outside [0,1] or missing")
    else:
        k, cut = bh_cutoff(pv, FDR_Q)

        def sgnv(x):
            return 1 if x > 0 else -1 if x < 0 else 0

        mism = []
        n_hold = 0
        for r in SS:
            fdr = fnum(r["p_train"]) <= cut
            holds = sgnv(fnum(r["b_test"])) == sgnv(fnum(r["b_train"])) and fnum(r["test_error_gain"]) > 0
            flag = r.get("fdr_pass") or r.get("bh_pass")
            cand = r.get("holdout_candidate")
            if (fdr != fbool(flag) or holds != fbool(r["holds_in_test"])
                    or (fdr and holds) != fbool(cand)):
                mism.append(f"{r['spread']}/{r['physical_number']}/h{r['h']}")
            if fdr and holds:
                n_hold += 1
        check("G.bh-flags-match-saved-pvalues", not mism,
              f"cut={cut:.16g} k={k} mism={mism[:3]}" if mism else f"cut={cut:.16g} k={k} n={len(SS)}")
        check("G.bh-15-at-saved-cutoff", k == 15 and abs(cut - BH03_CUT) < 1e-15,
              f"k={k} cut={cut:.16g}")
        check("G.bh-3-holdout-candidates", n_hold == 3, f"n={n_hold}")
    tg = {r["spread"] for r in SS}
    dg = {r["physical_number"] for r in SS}
    hg = {r["h"] for r in SS}
    check("G.search-design-grid", len(SS) == 3240 and len(SS) == len(tg) * len(dg) * len(hg),
          f"n={len(SS)} spreads={len(tg)} drivers={len(dg)} h={sorted(hg)}")
    check("G.nominal-264", sum(1 for r in SS if fnum(r["p_train"]) < 0.05) == 264)

if FVS:
    h1 = next((r for r in FVS if r["spread"] == "LA_GC_1" and r["h"] == "1"), None)
    la4 = next((r for r in FVS if r["spread"] == "LA_GC_1" and r["h"] == "4"), None)
    check("G.la_gc_1-r2-17.9-vs-12.6", h1 is not None and la4 is not None
          and abs(float(la4["r2_fair_value"]) - 0.179) < 0.002
          and abs(float(la4["r2_own"]) - 0.126) < 0.002)
    check("G.h4-weeks-three-fewer", h1 is not None and la4 is not None
          and int(h1["weeks"]) - int(la4["weeks"]) == 3)

if NOW:
    check("G.nowcast-8-rows", len(NOW) == 8, f"n={len(NOW)}")
    pre_w = [r for r in NOW if r["period"].startswith("before") and not r["target"].endswith("_4W")]
    check("G.nowcast-pre-covid-weekly-3-to-4pct",
          len(pre_w) == 2 and sorted(fnum(r["pct_better_than_best_simple"]) for r in pre_w) == [3.0, 4.0],
          f"pct={[r.get('pct_better_than_best_simple') for r in pre_w]}")
if SC:
    key0 = "series" if "series" in SC[0] else list(SC[0].keys())[0]
    sl = [r for r in SC if r["shortlist"].strip().lower() == "true"]
    la = next((r for r in SC if r[key0] == "LA_GC_1"), None)
    lj = next((r for r in SC if r[key0] == "LA_JET"), None)
    check("G.shortlist-four", len(sl) == 4, f"{[r[key0] for r in sl]}")
    check("G.halflife-6-vs-207", la is not None and lj is not None
          and abs(float(la["half_life_weeks"]) - 6) < 0.6
          and abs(float(lj["half_life_weeks"]) - 207) < 5)

if MS:
    pv = [fnum(r["p"]) for r in MS]
    k, cut = bh_cutoff(pv, FDR_Q)
    check("G.miles-720-70-bh-11", len(MS) == 720 and sum(1 for p in pv if p < 0.05) == 70
          and k == 11 and abs(cut - BH04_CUT) < 1e-15,
          f"n={len(MS)} nom={sum(1 for p in pv if p < 0.05)} k={k} cut={cut:.16g}")
    mism = [f"{r['spread']}/{r['miles_feature']}/h{r['h']}"
            for r in MS if fbool(r["fdr_pass"]) != (fnum(r["p"]) <= cut)]
    check("G.miles-bh-flags", not mism, f"mism={mism[:3]}")

# ---------- H. production renderer + two dashboard pages ----------
cases = [
    ("valid-2page", {"a": "x {{X}}", "b": "y {{Y}}"},
     {"a": {"{{X}}": 1}, "b": {"{{Y}}": 2}}, None),
    ("missing-key", {"a": "x {{X}} {{Z}}"}, {"a": {"{{X}}": 1}}, ValueError),
    ("unused-key", {"a": "x {{X}}"}, {"a": {"{{X}}": 1, "{{Y}}": 2}}, ValueError),
    ("missing-page", {"a": "x", "b": "y"}, {"a": {}}, ValueError),
    ("unknown-page", {"a": "x"}, {"a": {}, "zz": {}}, ValueError),
    ("wrong-page", {"a": "x {{X}}", "b": "y"}, {"a": {}, "b": {"{{X}}": 1}}, ValueError),
    ("malformed-key", {"a": "x"}, {"a": {"X": 1}}, ValueError),
]
bad = []
for name, t, v, exc in cases:
    try:
        out = validate_render(t, v)
        if exc is not None or (exc is None and out != {"a": "x 1", "b": "y 2"}):
            bad.append(name)
    except ValueError:
        if exc is None:
            bad.append(name)
    except Exception:
        bad.append(name + ":wrong-exc")
check("H.production-renderer-7-cases", not bad, f"bad={bad}")
try:
    txt = (ROOT / "docs/build_dashboard.py").read_text(encoding="utf-8")
    check("H.build_dashboard-delegates", "validate_render" in txt or "render_contract" in txt)
except FileNotFoundError:
    check("H.build_dashboard-delegates", False, "missing docs/build_dashboard.py")
intended = ["docs/index.html", "docs/detail.html"]
present = [p for p in intended if (ROOT / p).exists()]
check("H.two-dashboard-pages", len(present) == 2, f"present={present}")
left = [p for p in present if "{{" in (ROOT / p).read_text(encoding="utf-8")]
check("H.no-unfilled-placeholders", not left, f"left={left}")
if (ROOT / "docs/index.html").exists():
    idx = (ROOT / "docs/index.html").read_text(encoding="utf-8")
    check("H.index-project-title",
          "Regional Jet-Fuel Spreads Arbitrage During COVID Shutdowns" in idx)
    # These three guard the substance, not one wording: the overview must say the
    # figures are before costs, must not claim a net result, and must say that the
    # cost inputs are absent from the data.
    check("H.index-before-costs-stated",
          "before trading costs" in idx and "is gross" in idx)
    check("H.index-no-net-claim",
          "made money" not in idx.lower())
    check("H.index-cost-inputs-absent",
          all(s in idx for s in ("bid-offer", "absent from the dataset", "break-even")))

# ---------- J. analysis steps, notebooks, grids ----------
if MS:
    ts = {r["spread"] for r in MS}
    df = {r["miles_feature"] for r in MS}
    hf = {r["h"] for r in MS}
    check("J.miles-design-grid", len(MS) == len(ts) * len(df) * len(hf), f"n={len(MS)}")
if CF:
    check("J.covid-signals-nonempty", len(CF) > 0, f"n={len(CF)}")

if STEPS:
    check("J.analysis-steps-ten-rows", len(STEPS) == 10, f"n={len(STEPS)}")
    check("J.analysis-steps-columns", list(STEPS[0].keys()) == STEP_COLS,
          f"got={list(STEPS[0].keys())}")
    blank = []
    temp = []
    for r in STEPS:
        for c in ["source", "conclusion"] + STEP_PARTS:
            if not str(r.get(c, "")).strip():
                blank.append(f"{r.get('id')}.{c}")
        blob = " ".join(str(r.get(c, "")) for c in STEP_COLS)
        if "Temp/" in blob or "temp\\" in blob.lower() or "task 13" in blob.lower():
            temp.append(r.get("id"))
    check("J.analysis-steps-nonblank-parts", not blank, f"blank={blank[:8]}")
    check("J.analysis-steps-no-internal-paths", not temp, f"temp={temp}")

for nb in ["notebooks/01_price_eda.ipynb", "notebooks/02_fundamentals_panel.ipynb",
           "notebooks/03_signal_search.ipynb", "notebooks/04_air_traffic.ipynb"]:
    tag = Path(nb).stem
    try:
        node = json.loads((ROOT / nb).read_text(encoding="utf-8"))
    except Exception as e:
        check(f"J.notebook-json.{tag}", False, str(e)[:120])
        continue
    ks = ((node.get("metadata") or {}).get("kernelspec") or {})
    check(f"J.notebook-kernel.{tag}", ks.get("name") == "python3", f"name={ks.get('name')}")
    md_in_code = []
    code_in_md = []
    parse_fail = []
    for i, c in enumerate(node.get("cells") or []):
        src = "".join(c.get("source") or [])
        stripped = src.lstrip()
        if c.get("cell_type") == "code":
            if stripped.startswith("**") and "import " not in src[:400] and not any(
                    line.lstrip().startswith(("#", "import", "from", "def ", "for ", "if ", "PRICE", "PANEL",
                                              "ROLL", "STAT", "SEARCH", "A =", "F =", "os.", "ANALYSIS"))
                    for line in src.splitlines()[:12]):
                md_in_code.append(i)
            body = "\n".join(ln for ln in src.splitlines()
                             if not ln.lstrip().startswith("%") and not ln.lstrip().startswith("!"))
            if body.strip():
                try:
                    ast.parse(body)
                except SyntaxError:
                    parse_fail.append(i)
        elif c.get("cell_type") == "markdown":
            if "PRICE_FILE =" in src or "EA_FILE =" in src or stripped.startswith("import pandas"):
                code_in_md.append(i)
    check(f"J.notebook-no-markdown-as-code.{tag}", not md_in_code, f"cells={md_in_code}")
    check(f"J.notebook-no-code-as-markdown.{tag}", not code_in_md, f"cells={code_in_md}")
    check(f"J.notebook-code-parses.{tag}", not parse_fail, f"cells={parse_fail[:8]}")

print(f"\n{len(FAIL)} FAILURES: {FAIL}" if FAIL else "\nALL CHECKS PASSED")
sys.exit(1 if FAIL else 0)
