"""Build and check the two public dashboard pages.

Run from the repository root:

    python docs/build_dashboard.py         # validate, then write both pages
    python docs/build_dashboard.py --check # validate only; write nothing

Fails on unfilled placeholders, a missing required result, an unused
computed result, a broken local link, an absolute local path, external
analytics, more charts than the cap, a visible-word cap breach (overview
1,400, methods 2,600), or a mismatch with the two saved portfolio rows.
"""
from __future__ import annotations

import csv
import html
import math
import re
import sys
from pathlib import Path
from typing import NoReturn

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_contract import validate_render

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs"
CHART_CAP = 7
WORD_CAPS = {"index.html": 1400, "detail.html": 2600}
PORT_EXPECT = {
    "WEST_COAST_3": {
        "weeks": 163, "total_cents": 135.9, "cents_per_year": 43.4,
        "sharpe": 2.29, "weeks_won": 0.65, "worst_drawdown": -12.5,
    },
    "SHORTLIST_4": {
        "weeks": 163, "total_cents": 105.3, "cents_per_year": 33.6,
        "sharpe": 1.30, "weeks_won": 0.60, "worst_drawdown": -33.5,
    },
}
NEED = [
    "results/price_eda_scorecard.csv",
    "results/signal_search.csv",
    "results/fair_value_scores.csv",
    "results/backtest.csv",
    "results/nowcast_scores.csv",
    "results/miles_search.csv",
    "results/covid_first_signals.csv",
    "results/analysis_steps.csv",
]
ANALYTICS_RE = re.compile(
    r"goatcounter|gc\.zgo\.at|google-analytics|googletagmanager|"
    r"gtag\s*\(|plausible\.io|mixpanel|hotjar|segment\.com|analytics\.js",
    re.I,
)
ABS_PATH_RE = re.compile(
    r"(?:[A-Za-z]:\\)|(?:file:)|(?:/Users/)|(?:/home/)",
    re.I,
)
HREF_RE = re.compile(r"""href\s*=\s*['"]([^'"]+)['"]""", re.I)
PLACEHOLDER_RE = re.compile(r"\{\{[A-Za-z0-9_]+\}\}")

CSS = """
:root { --ink:#173344; --muted:#576e7b; --accent:#087e83; --bg:#f1f5f6; --line:#d3e0e4; --soft:#edf5f5; }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); font:17px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif; color:var(--ink); }
header { background:var(--ink); color:#fff; padding:40px max(22px, calc((100vw - 880px) / 2)) 32px; }
.kicker { letter-spacing:.12em; font-size:12px; font-weight:700; color:#9ad4d5; margin:0; }
h1 { font-size:clamp(26px,3.4vw,36px); line-height:1.15; margin:10px 0 0; }
main { max-width:880px; margin:auto; padding:22px; }
nav { display:flex; gap:8px; flex-wrap:wrap; margin:22px 0 4px; }
nav a { color:var(--accent); background:#fff; text-decoration:none; border:1px solid var(--line); padding:8px 14px; border-radius:20px; font-weight:600; font-size:14px; }
nav a:hover { border-color:var(--accent); }
a:focus-visible { outline:3px solid #bfe6e8; outline-offset:2px; }
section { background:#fff; border:1px solid var(--line); border-radius:12px; padding:24px 28px; margin:18px 0; }
h2 { font-size:22px; line-height:1.25; margin:0 0 10px; }
p { margin:10px 0; }
ul { margin:8px 0 0; padding-left:1.15em; }
li { margin:8px 0; }
.lab { font-weight:700; }
.cap { color:var(--muted); font-size:14px; margin:6px 0 0; }
svg { display:block; width:100%; height:auto; margin:16px 0 0; }
.tk { font:11px system-ui,sans-serif; fill:var(--muted); }
.ax { font:12px system-ui,sans-serif; fill:var(--muted); }
.pl { font:11px system-ui,sans-serif; fill:var(--ink); }
footer { max-width:880px; margin:auto; padding:8px 22px 48px; color:var(--muted); font-size:14px; }
footer a { color:var(--accent); }
@media (max-width:600px) { section { padding:18px 16px; } body { font-size:16px; } }
"""

INDEX_TPL = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Regional Jet-Fuel Spreads Arbitrage During COVID Shutdowns</title>
<link rel="icon" href="data:,">
<style>""" + CSS + """</style>
</head>
<body>
<header>
<p class="kicker">OVERVIEW &middot; 2011 TO 2020</p>
<h1>Regional Jet-Fuel Spreads Arbitrage During COVID Shutdowns</h1>
</header>
<main>
<nav>
<a href="index.html">Overview</a>
<a href="detail.html">Methods</a>
</nav>
<section>
<p>Jet fuel sells at different prices in different regions. A <b>spread</b> is one regional jet
price minus another, quoted in cents per gallon. An <b>outright price</b>, also called the
front-month price, is the price of the nearest delivery month on its own.</p>
<p>The thesis rests on one measured difference. On weekly means from
2011 to 2020, regional jet spreads return toward their own average within weeks. Outright prices
follow crude oil, and a shock to them persists. The rule trades spreads because spreads return
to an average.</p>
</section>
<section>
<h2>Screened spreads</h2>
<ul>
<li><span class="lab">Method.</span> Four screens, applied to {{N_CAND}} candidate
spreads on weeks through 20 February 2020: an Augmented Dickey-Fuller test with p below 0.05, a
half-life of at most 8 weeks, a typical weekly move of at least 1 c/gal, and one name per group of
spreads that move together.</li>
<li><span class="lab">Reason.</span> Each screen tests one requirement the rule has.
The Dickey-Fuller test asks whether a series returns to a fixed average or keeps drifting,
and the rule needs the first kind. The half-life is the number of weeks in which half
a move fades, so it sets the holding period. The 1 c/gal floor keeps the move larger than the noise
a trader pays to cross. The group screen drops spreads that share a leg and so carry the same
information twice.</li>
<li><span class="lab">Result.</span> {{N_CAND}} candidates fell to {{N_ADF}} after the
Dickey-Fuller screen, {{N_HL}} after the half-life screen, {{N_MOVE}} after the move-size screen,
and {{N_SHORT}} after the group screen: {{SHORTLIST}}. NY_GC_1 failed the move-size screen at
{{NY_SD}} c/gal, just under the 1 c/gal floor. Outright front-month prices failed the first screen,
with Dickey-Fuller p reaching 1.00: they hold no fixed average to trade against.</li>
<li><span class="lab">What it means.</span> The four survivors are the only names the price
statistics support, and the screens say why each other candidate left. The result also describes
the data: regional and calendar spreads hold a stable average because freight and storage costs
bound them, while outright prices inherit the path of crude oil. The screens ran on the
same weeks the later simulation uses, so the shortlist is a retrospective choice.</li>
</ul>
{{FUNNEL}}
<p class="cap">Spreads surviving each screen, with the number lost at each step on the right.</p>
</section>
<section>
<h2>Physical driver tests</h2>
<ul>
<li><span class="lab">Method.</span> {{NTEST}} regressions of spread changes on one physical
driver at a time, then a Benjamini-Hochberg correction, then a test on 2019 to 2020 asking for the
same sign and lower error. A walk-forward fair value was fitted separately, on a fixed set of regional balances.</li>
<li><span class="lab">Reason.</span> A search this wide produces apparent findings from
chance alone, so the survivor count means nothing until the chance count is subtracted.
Benjamini-Hochberg ranks every result together and keeps only those too extreme for the expected
chance passes to explain. The later window checks the survivors: a relationship that reverses sign
outside the fitting period stays out of the rule.</li>
<li><span class="lab">Result.</span> {{NPASS}} of the {{NTEST}} tests reached p below 0.05.
A 5 percent threshold admits one test in twenty by chance, so about {{NCHANCE}} would pass with no
relationship present at all. Benjamini-Hochberg kept {{NFDR}} at a cutoff of {{BH03}}, and
{{NCONF}} of those also held sign and cut error in the later window. Against that, the
regional-balance fair value accounted for {{R2FV}} percent of the four-week move in LA_GC_1 where
the spread's own 26-week average accounted for {{R2OWN}} percent.</li>
<li><span class="lab">What it means.</span> {{NCONF}} survivors from {{NTEST}} attempts sits close to
the chance count, so the open search stays out of the rule.
The fair value rests on separate ground: its inputs were fixed in advance on physical reasoning
rather than chosen by the search. Its {{R2GAP}}-point advantage says that {{R2FV}} percent
of the next four weeks is anticipated by today's inventory position, leaving {{R2REST}} percent
unexplained: enough to trade across many weeks, and too little to act on in any single week.</li>
</ul>
{{PVCHART}}
<p class="cap">Where the {{NTEST}} training p-values fell. The dashed line is the count each bar
would hold if no driver carried information.</p>
</section>
<section>
<h2>Simulated results before trading costs</h2>
<ul>
<li><span class="lab">Method.</span> Held +1 or &minus;1 by the sign of the four-week fair-value
forecast, scored against the following week's average-to-average spread change, held one week,
and repeated for {{WEEKS}} weeks
from January 2017 to February 2020, on revised EIA history. Gross spread changes, before execution
costs. Two books: the three West Coast names, and the four screen
survivors.</li>
<li><span class="lab">Reason.</span> A one-week hold scores the forecast alone, with no
position-sizing rule. The annualized Sharpe ratio divides the
average weekly result by its standard deviation and scales by the square root of 52: return
against the size of its own variation.</li>
<li><span class="lab">Result.</span> West Coast three: {{TOTAL}} c/gal in total, {{PY}} c/gal
a year, Sharpe {{SHARPE}}, {{WIN}} of weeks profitable, worst peak-to-trough fall {{DD}} c/gal.
Shortlist four: {{STOTAL}} total, {{SPY}} a year, Sharpe {{SSHARPE}}, {{SWIN}} of weeks profitable,
worst fall {{SDD}} c/gal. A Sharpe of {{SHARPE}} means the annual result is about {{SHARPE}} times
the size of its own year-to-year variation.</li>
<li><span class="lab">What it means.</span> The forecast carried a positive result on these weeks,
and the narrower West Coast book beat the wider one: the return concentrated in the
Los Angeles names. Both
books were selected with these weeks already visible, and every figure above is gross: the
bid-offer spread, fees and market depth for these swaps are absent from the dataset, so the cost
per unit traded and the break-even cost that would erase the result are the first numbers to
establish before any of this is tradable.</li>
</ul>
{{COMP_CHART}}
<p class="cap">Totals to February 2020, cents per gallon, before trading costs.</p>
</section>
<section>
<h2>Flight miles as an early demand reading</h2>
<ul>
<li><span class="lab">Method.</span> Built weekly flight miles from OpenSky aircraft position
records, estimated the same week's jet fuel demand from them four days before the Energy
Information Administration published it, and scored that against last week's demand and the
four-week average.</li>
<li><span class="lab">Reason.</span> Saturday miles are observable before the Wednesday
report. The two simple alternatives are the
benchmark because a forecast has to beat what a person could write down unaided.</li>
<li><span class="lab">Result.</span> Across 53 normal weeks the root mean squared error was
{{NOW_P5}} percent lower for the West Coast and {{NOW_US}} percent lower for the United States than
the better simple alternative. Four-week demand targets were worse. Miles tested against spreads gave {{MILESP}} results below 0.05 from {{MILESN}} tests, with
{{MILESFDR}} surviving the Benjamini-Hochberg correction and no later window to confirm them.</li>
<li><span class="lab">What it means.</span> A 3 to 4 percent error reduction is small because in a
steady week the four-week average is already close to right. The 2020 collapse shows where the
head start counts: during a fast demand move. Miles give an early reading of a demand shock.
They leave routine weekly forecasting and the spread rule unchanged.</li>
</ul>
</section>
<section>
<h2>Conclusion</h2>
<p>Spreads return to an average and outright prices follow crude oil, so the work trades spreads. A
fair value built from inventory and refinery data anticipated more of the four-week move in the
main West Coast spread than that spread's own history, and a signed one-week hold on it produced a
positive simulated result. The open search stays out of the rule; flight
miles give an early demand reading during a shock. Both books were chosen with these weeks visible, and no trading cost has been measured.</p>
</section>
</main>
<footer>
<a href="detail.html">Methods and sources</a>
</footer>
</body>
</html>
"""

DETAIL_TPL = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Regional Jet-Fuel Spreads Arbitrage During COVID Shutdowns: methods</title>
<link rel="icon" href="data:,">
<style>""" + CSS + """</style>
</head>
<body>
<header>
<p class="kicker">METHODS AND FINDINGS &middot; 2011 TO 2020</p>
<h1>Regional Jet-Fuel Spreads Arbitrage During COVID Shutdowns</h1>
</header>
<main>
<nav>
<a href="index.html">Overview</a>
<a href="detail.html">Methods</a>
</nav>
<section>
<h2>Price selection</h2>
<ul>
<li><span class="lab">Method.</span> Ran an Augmented Dickey-Fuller test and a KPSS test on
every series through February 2020, measured the half-life from a one-lag fit, measured the typical
weekly move, dropped series that are arithmetic sums of others, and kept the largest weekly move in
each correlated group.</li>
<li><span class="lab">Reason.</span> The two tests answer the same question from opposite
directions: Dickey-Fuller starts from the assumption that a series never returns and looks for
evidence that it does, while KPSS starts from the assumption that it returns to a fixed level and
looks for evidence that it does not. Running both gives a verdict with its disagreements visible
instead of one test's default. The half-life converts the fitted persistence into weeks, which is
the unit a trading horizon is set in. The group screen removes series carrying the same information
twice, which would otherwise be mistaken for independent evidence.</li>
<li><span class="lab">Result.</span> Outright front-month prices keep drifting instead of returning:
Dickey-Fuller p reaches 1.00 and the fitted persistence sits between 0.978 and 0.998, so a shock
to them decays across years instead of weeks. Four spreads pass every screen: LA_GC_1 with a
half-life of {{LA_HL}} weeks and a weekly move of {{LA_SD}} c/gal; SING_GC_1 at {{SING_HL}} and
{{SING_SD}}; LA_JET_M2M3 at {{M2M3_HL}} and {{M2M3_SD}}; HO_BRENT at {{HO_HL}} and {{HO_SD}}.
NY_GC_1 failed the 1 c/gal move screen at {{NY_SD}}. NWE_GC_1 and LA_JET_M1M2 each passed the first
three screens and lost the group screen to SING_GC_1 and LA_GC_1. {{N_ID}} series were dropped as
arithmetic sums of others.</li>
<li><span class="lab">What it means.</span> A half-life of {{LA_HL}} weeks says half of any
departure from the average in LA_GC_1 is gone within {{LA_HL}} weeks, which sets the holding period
used later. The contrast with outright prices is the project's foundation and it has a physical
cause: shipping fuel between regions costs a known amount per gallon, which bounds a regional
spread from both sides, while nothing bounds the level of crude oil. NY_GC_1's exclusion shows the
screens bind, since it failed by 0.01 c/gal.</li>
</ul>
{{SCATTER}}
<p class="cap">Half-life against weekly move for {{N_CAND}} candidates. Teal box: half-life at most
8 weeks and weekly move at least 1 c/gal. Dark dots: the four that pass every screen.</p>
</section>
<section>
<h2>Seasonality</h2>
<ul>
<li><span class="lab">Method.</span> Regressed each spread on a set of month indicators and
recorded the share of its variation the month of the year accounts for, with an F-test p-value.</li>
<li><span class="lab">Reason.</span> Month indicators are the plainest test for a repeating
annual pattern: each month gets its own average, and the regression reports how much of the
movement that fixed pattern explains. A forecast that repeats the calendar adds nothing a trader lacks.</li>
<li><span class="lab">Result.</span> {{SEAS_TOP}} is the most seasonal series in the set, with
the month of the year accounting for {{SEAS_TOP_R2}} percent of its variation at p {{SEAS_TOP_P}}.
Gulf Coast calendar spreads and the heating oil crack sit at the top of the list. LA_GC_1 is the
exception among the traded names: month accounts for {{LA_MONTH}} percent of its variation at p
{{LA_MONTH_P}}, which does not clear the 5 percent level.</li>
<li><span class="lab">What it means.</span> Jet fuel and distillate demand move with the seasons, so
a calendar spread inside one region inherits that pattern, which is why the Gulf Coast
calendar spreads score highest. A regional spread subtracts two locations that share the same
seasonal demand, so most of the season cancels, and LA_GC_1's failure to clear the 5 percent level
is that cancellation showing up in the statistics. This is the reason the fair value for LA_GC_1
uses inventory and refinery readings and no calendar term: month accounts for {{LA_MONTH}} percent
of that spread at p {{LA_MONTH_P}}, while inventory accounts for {{R2FV}} percent of its four-week
move.</li>
</ul>
{{SEASON}}
<p class="cap">Share of each spread's variation accounted for by the month of the year.</p>
</section>
<section>
<h2>Physical-data regressions</h2>
<ul>
<li><span class="lab">Method.</span> Shifted every physical column forward one week so each row
holds only values already published, ran the two stationarity tests on 2015 to February 2020,
measured correlation and the variance inflation factor among drivers, and tested fourteen
spread-driver pairs whose expected sign was written down first.</li>
<li><span class="lab">Reason.</span> A same-week inventory figure is not public when the
week trades, so using it would score a forecast on information a trader could not have had. The
variance inflation factor measures how far one driver is reproducible from the others; two columns
correlated at 0.96 carry one column's information and fitting both splits a single effect across
two unstable coefficients. Writing the expected sign first makes each pair a test of a stated prediction.</li>
<li><span class="lab">Result.</span> 13 of the 14 signs matched the prediction. The exception
was LA_GC_1 against PADD 3 jet stocks at &minus;0.04, which was kept because the Gulf Coast is the
other leg of that spread and the sign is ambiguous by construction. Refinery runs and utilization
correlate at 0.96, as do US and PADD 1 distillate stocks. Distillate stocks measured against their
five-year normal drifts rather than returning to an average. Next-week correlations fall between
&minus;0.14 and 0.13.</li>
<li><span class="lab">What it means.</span> Thirteen matching signs out of fourteen supports the
physical story: regional scarcity widens the spread, and the
inventory and refinery numbers measure that scarcity. One of each correlated pair was dropped, and
the distillate-against-normal column was dropped because a fair value needs a driver that returns
to a fixed average. Next-week correlations between &minus;0.14 and 0.13 set the
expectation: these drivers describe the current state of the market and account for almost none of
next week's change, so the forecast horizon is four weeks.</li>
</ul>
</section>
<section>
<h2>Fair-value forecast</h2>
<ul>
<li><span class="lab">Method.</span> Ran {{NTEST}} regressions of spread change on one driver
plus the 26-week gap with Newey-West standard errors, applied Benjamini-Hochberg at q=0.10, then
required the same sign and lower error on 2019 to 2020. For each week t the same code also fitted the
spread on a fixed set of regional balances using weeks through t and forecast the change from t+1
to t+5 three ways: from the fair-value gap, from the 26-week gap, and from both.</li>
<li><span class="lab">Reason.</span> Newey-West standard errors are used because
overlapping four-week windows share weeks and therefore move together, which makes ordinary
standard errors too small and p-values too generous. Benjamini-Hochberg is used because
{{NTEST}} tests at a 5 percent threshold produce chance passes in bulk. The walk-forward fit exists
so that no week's forecast uses a coefficient estimated from its own outcome.</li>
<li><span class="lab">Result.</span> {{NPASS}} training p-values fell below 0.05 against
about {{NCHANCE}} expected from chance alone; Benjamini-Hochberg kept {{NFDR}} at {{BH03}}; and
{{NCONF}} survived the later window. The ordering then runs backwards: results with the strongest
training evidence, p below 0.001, survived the later window {{HOLD_LO}} percent of the time, while
the weakest, p above 0.2, survived {{HOLD_HI}} percent. On the four-week horizon LA_GC_1 reached
{{R2FV}} percent for the fair value against {{R2OWN}} percent for its own average. One-week
R-squared sits near zero across every spread.</li>
<li><span class="lab">What it means.</span> Strong training results survived the later window least
often, at {{HOLD_LO}} percent against {{HOLD_HI}} percent for the weakest results.
The training p-value carries no information about which pairings hold up, so the {{NCONF}}
survivors out of {{NTEST}} match what noise produces.
The fair value rests on separate ground because its inputs were fixed in advance rather than selected by the search.
Its advantage is confined to a four-week horizon and to some spreads: it improves five of eight and
makes GC_JET_M1M2 and HO_BRENT worse, which bounds the claim to Los Angeles and Northwest Europe
regional spreads.</li>
</ul>
{{R2CHART}}
<p class="cap">Four-week R-squared by spread. Grey: the spread's own 26-week average. Teal: the
regional-balance fair value. Bars left of zero forecast worse than assuming no change.</p>
</section>
<section>
<h2>Simulated portfolio results before trading costs</h2>
<ul>
<li><span class="lab">Method.</span> Took a +1 or &minus;1 position from the sign of the
existing four-week forecast, scored against the following week's average-to-average spread change,
held one week, and repeated for
{{WEEKS}} weeks on revised EIA history. Gross spread changes. Two books: the four screen survivors, and the three West Coast names.</li>
<li><span class="lab">Reason.</span> Scoring a forecast as a signed one-week hold keeps the
test to the forecast itself, with no position sizing or stop rule.
The peak for the drawdown calculation starts at zero, so the worst fall is measured
from the start of trading.</li>
<li><span class="lab">Result.</span> Over {{WEEKS}} weeks the West Coast three returned
{{TOTAL}} c/gal in total, {{PY}} c/gal a year, at a Sharpe ratio of {{SHARPE}}, with {{WIN}} of
weeks profitable and a worst fall of {{DD}} c/gal. The shortlist four returned {{STOTAL}} total,
{{SPY}} a year, Sharpe {{SSHARPE}}, {{SWIN}} of weeks profitable, worst fall {{SDD}} c/gal.</li>
<li><span class="lab">What it means.</span> A Sharpe of {{SHARPE}} means the annual result is about
{{SHARPE}} times the size of its own variation, which over {{WEEKS}} weeks is a wide interval.
The West Coast book beating the wider shortlist puts the return in
the Los Angeles names: adding SING_GC_1 and HO_BRENT diluted it, consistent with the
fair value making those two spreads worse on the four-week horizon. Both books were chosen with these weeks visible, so neither is an out-of-sample result.
The figures are gross: each change of sign pays the bid-offer spread, and bid-offer, fees and depth
for these swaps are absent from the dataset, so the cost per unit traded and the break-even cost
remain unmeasured and are the first thing to establish.</li>
</ul>
</section>
<section>
<h2>Air-traffic test</h2>
<ul>
<li><span class="lab">Method.</span> Estimated each week's demand as flight miles times the
prior eight weeks' demand-per-mile ratio, and scored the root mean squared error against last
week's demand and the four-week average, over 53 weeks before 2020 and 13 weeks of the collapse.
Dated the first week each series fell 20 percent below its eight-week mean, by public release date.
Ran {{MILESN}} regressions of spread changes on miles features plus the 26-week gap with
Benjamini-Hochberg at q=0.10.</li>
<li><span class="lab">Reason.</span> The eight-week ratio converts miles into barrels using
only past data, so the estimate is available on Saturday, four days before the Wednesday report.
The two simple alternatives are the benchmark because a forecast has to beat what a person could
write down unaided. Release dates are used in place of data dates because a signal is usable
once it is public.</li>
<li><span class="lab">Result.</span> Before 2020 the error was {{NOW_P5}} percent lower for
the West Coast and {{NOW_US}} percent lower for the United States than the better alternative.
Four-week demand targets were worse by {{NOW_P5_4W}} and {{NOW_US_4W}} percent. In the 13 collapse
weeks the West Coast error was {{NOW_COVID}} percent lower. Order of first signal: the Gulf Coast
crack on {{COVID_CRACK}}, East Coast miles on {{COVID_P1M}}, the EIA weekly figure on
{{COVID_EIA}}, West Coast miles on {{COVID_P5M}}, the EIA four-week figure on {{COVID_EIA4}}.
Against spreads: {{MILESP}} of {{MILESN}} tests below 0.05 and {{MILESFDR}} Benjamini-Hochberg
keeps at {{BH04}}, with no later window.</li>
<li><span class="lab">What it means.</span> Three to four percent is a small gain, and the reason is
that in a calm week the four-week average is already close to the answer, so four days of notice is
worth little. The collapse weeks are where the gain appears: miles hold information
about the speed of a change. That is one episode, so the 2020 reading is a description of that
episode. The four-week figures show the method does not
carry across horizons. Miles stay out of the spread rule and stand as a
demand reading only.</li>
</ul>
{{NOWCHART}}
<p class="cap">Estimation error against the two simple alternatives. Lower is better.</p>
</section>
<section>
<h2>Sources</h2>
<p>Price inputs came from Bloomberg and are not redistributed. Weekly physical data came from the
U.S. Energy Information Administration. Flight observations came from the OpenSky Network
(Sch&auml;fer, M., Strohmeier, M., Lenders, V., Martinovic, I. and Wilhelm, M., 2014, Bringing up
OpenSky: A large-scale ADS-B sensor network for research, IPSN 2014, pp. 83&ndash;94).</p>
</section>
</main>
<footer>
<a href="index.html">Overview</a>
</footer>
</body>
</html>
"""


def fail(msg) -> NoReturn:
    raise ValueError(msg)


def load_csv(rel):
    path = ROOT / rel
    if not path.exists():
        fail(f"missing required result: {rel}")
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        fail(f"empty required result: {rel}")
    return rows


def fnum(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def fbool(x):
    return str(x).strip().lower() in ("true", "1", "yes")


def bh_cutoff(pvals, q=0.10):
    ranked = sorted(pvals)
    m = len(ranked)
    k = 0
    for i, p in enumerate(ranked, 1):
        if p <= i * q / m:
            k = i
    return k, (ranked[k - 1] if k else -1.0)


def port_row(bt, name):
    hit = next(
        (r for r in bt
         if r.get("spread") == name
         and r.get("model") == "f_fair_value"
         and r.get("period") == "2017 to Feb 2020"),
        None,
    )
    if hit is None:
        fail(f"missing required result: backtest {name}")
    exp = PORT_EXPECT[name]
    got_weeks = int(float(hit["weeks"]))
    if got_weeks != exp["weeks"]:
        fail(f"{name} weeks {got_weeks} != {exp['weeks']}")
    for key, tol in (
        ("total_cents", 0.06),
        ("cents_per_year", 0.06),
        ("sharpe", 0.015),
        ("weeks_won", 1e-9),
        ("worst_drawdown", 0.06),
    ):
        got = fnum(hit[key])
        if got is None or abs(got - exp[key]) > tol:
            fail(f"{name} {key} {got} != {exp[key]}")
    return hit


def comparison_chart(west, short):
    books = [("West Coast three", west), ("Shortlist four", short)]
    totals = [float(b["total_cents"]) for _, b in books]
    mx = max(totals) if max(totals) > 0 else 1.0
    w, h, l, top, row_h = 880, 156, 16, 14, 66
    bar_l, bar_w, bar_h = 186, 420, 22
    parts = [
        f'<svg viewBox="0 0 {w} {h}" role="img" '
        'aria-label="West Coast and shortlist pre-COVID portfolio totals">'
    ]
    for i, (lab, b) in enumerate(books):
        y = top + i * row_h
        tot = float(b["total_cents"])
        bw = tot / mx * bar_w
        py = float(b["cents_per_year"])
        sh = float(b["sharpe"])
        win = float(b["weeks_won"])
        dd = float(b["worst_drawdown"])
        parts.append(f'<text x="{l}" y="{y + 20}" class="pl">{lab}</text>')
        parts.append(
            f'<rect x="{bar_l}" y="{y + 4}" width="{bw:.1f}" height="{bar_h}" '
            f'fill="#087e83" rx="3"/>'
        )
        parts.append(
            f'<text x="{bar_l + bw + 10:.1f}" y="{y + 20}" class="pl">'
            f"{tot} c/gal total</text>"
        )
        parts.append(
            f'<text x="{bar_l}" y="{y + 46}" class="tk">'
            f"{py} c/gal a year · Sharpe {sh:.2f} · win {win:.2f} · DD {dd}</text>"
        )
    parts.append("</svg>")
    return "\n".join(parts)


def funnel_chart(counts):
    """Survivors after each screen cut. Carries the selection claim in Price selection."""
    labels = [
        ("Candidate spreads built", "start"),
        ("Return to an average (ADF p below 0.05)", "cut"),
        ("Half-life at most 8 weeks", "cut"),
        ("Weekly move at least 1 c/gal", "cut"),
        ("One name per correlated group", "cut"),
    ]
    w, h, l, top, row_h = 880, 196, 16, 16, 36
    bar_l, bar_w, bar_h = 352, 400, 20
    mx = counts[0] if counts[0] else 1
    parts = [
        f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="Spreads surviving each '
        'screen cut, from candidates down to the shortlist">'
    ]
    for i, ((lab, _kind), n) in enumerate(zip(labels, counts)):
        y = top + i * row_h
        bwid = n / mx * bar_w
        fill = "#173344" if i == len(counts) - 1 else "#087e83"
        parts.append(f'<text x="{l}" y="{y + 15}" class="pl">{lab}</text>')
        parts.append(
            f'<rect x="{bar_l}" y="{y + 1}" width="{bwid:.1f}" height="{bar_h}" '
            f'fill="{fill}" fill-opacity="{0.85 if i in (0, len(counts) - 1) else 0.55}" rx="3"/>'
        )
        parts.append(
            f'<text x="{bar_l + bwid + 9:.1f}" y="{y + 16}" class="pl">{n}</text>'
        )
        if i:
            parts.append(
                f'<text x="{bar_l + bwid + 34:.1f}" y="{y + 16}" class="tk">'
                f"&minus;{counts[i - 1] - n}</text>"
            )
    parts.append("</svg>")
    return "\n".join(parts)


def pvalue_chart(pvals, n_pass, n_chance):
    """p-value spread of the open search against the flat line chance alone would draw."""
    bins = 20
    counts = [0] * bins
    for p in pvals:
        counts[min(int(p * bins), bins - 1)] += 1
    flat = len(pvals) / bins
    w, h, l, r, t, b = 880, 280, 60, 20, 18, 52
    mx = max(max(counts), flat * 1.15)
    bw = (w - l - r) / bins
    xs = lambda i: l + i * bw
    ys = lambda v: t + (1 - v / mx) * (h - t - b)
    parts = [
        f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="How the {len(pvals)} search '
        "p-values are spread, against the flat line chance alone would produce\">"
    ]
    for g in range(0, int(mx) + 1, max(1, int(mx // 4))):
        parts.append(
            f'<line x1="{l}" y1="{ys(g):.1f}" x2="{w - r}" y2="{ys(g):.1f}" stroke="#e4ecef"/>'
            f'<text x="{l - 8}" y="{ys(g) + 4:.1f}" text-anchor="end" class="tk">{g}</text>'
        )
    for i, c in enumerate(counts):
        fill = "#173344" if i == 0 else "#087e83"
        parts.append(
            f'<rect x="{xs(i) + 1:.1f}" y="{ys(c):.1f}" width="{bw - 2:.1f}" '
            f'height="{ys(0) - ys(c):.1f}" fill="{fill}" fill-opacity="0.8"/>'
        )
    parts.append(
        f'<line x1="{l}" y1="{ys(flat):.1f}" x2="{w - r}" y2="{ys(flat):.1f}" '
        'stroke="#8b4513" stroke-width="1.6" stroke-dasharray="6 4"/>'
    )
    parts.append(
        f'<text x="{w - r - 4}" y="{ys(flat) - 8:.1f}" text-anchor="end" class="tk" '
        f'style="paint-order:stroke;stroke:#fff;stroke-width:4">'
        f"chance alone: {flat:.0f} per bar</text>"
    )
    parts.append(
        f'<text x="{xs(0) + bw + 8:.1f}" y="{ys(counts[0]) + 14:.1f}" class="tk" '
        f'style="paint-order:stroke;stroke:#fff;stroke-width:4">'
        f"{n_pass} below 0.05; {n_chance} expected by chance</text>"
    )
    for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
        parts.append(
            f'<text x="{l + frac * (w - l - r):.1f}" y="{ys(0) + 16:.1f}" '
            f'text-anchor="middle" class="tk">{frac:g}</text>'
        )
    parts.append(
        f'<text x="{(l + w - r) / 2:.0f}" y="{h - 12}" text-anchor="middle" class="ax">'
        "Training p-value</text>"
    )
    parts.append(
        f'<text x="14" y="{(t + h - b) / 2:.0f}" text-anchor="middle" class="ax" '
        f'transform="rotate(-90 14 {(t + h - b) / 2:.0f})">Tests</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


def r2_chart(rows):
    """Fair value against the spread's own 26-week average, per spread, four-week horizon."""
    rows = sorted(rows, key=lambda r: -r[2])
    w, l, r_, top, row_h = 880, 130, 150, 16, 30
    h = top + len(rows) * row_h + 40
    zero = l + 70
    scale = (w - l - r_ - 70) / 20.0
    xs = lambda v: zero + v * scale
    parts = [
        f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="Four-week R-squared for the '
        'fair value and for the own 26-week average, by spread">'
    ]
    for i, (name, own, fv) in enumerate(rows):
        y = top + i * row_h
        parts.append(f'<text x="8" y="{y + 17}" class="pl">{name}</text>')
        for val, fill, off in ((own, "#8a9aa3", 0), (fv, "#087e83", 11)):
            x0, x1 = (xs(min(val, 0)), xs(max(val, 0)))
            parts.append(
                f'<rect x="{x0:.1f}" y="{y + off:.1f}" width="{max(x1 - x0, 1):.1f}" '
                f'height="9" fill="{fill}" rx="2"/>'
            )
        parts.append(
            f'<text x="{w - r_ + 10}" y="{y + 17}" class="tk">'
            f"own {own:.1f}, fair value {fv:.1f}</text>"
        )
    parts.append(
        f'<line x1="{zero:.1f}" y1="{top - 4}" x2="{zero:.1f}" y2="{h - 40}" '
        'stroke="#173344" stroke-width="1.2"/>'
    )
    parts.append(
        f'<text x="{zero:.1f}" y="{h - 24}" text-anchor="middle" class="tk">0</text>'
    )
    parts.append(
        f'<text x="{xs(10):.1f}" y="{h - 24}" text-anchor="middle" class="tk">10</text>'
    )
    parts.append(
        f'<text x="{xs(20):.1f}" y="{h - 24}" text-anchor="middle" class="tk">20</text>'
    )
    parts.append(
        f'<text x="{(zero + w - r_) / 2:.0f}" y="{h - 6}" text-anchor="middle" class="ax">'
        "Percent of the four-week move accounted for (grey: own average; teal: fair value)</text>"
    )
    parts.append("</svg>")
    return "\n".join(parts)


def season_chart(rows):
    """Share of each spread's variation that the month of the year accounts for."""
    rows = sorted(rows, key=lambda r: -r[1])
    w, top, row_h = 880, 16, 28
    h = top + len(rows) * row_h + 38
    bar_l, bar_w = 300, 380
    parts = [
        f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="Share of each spread variation '
        'accounted for by the month of the year">'
    ]
    for i, (name, r2, p) in enumerate(rows):
        y = top + i * row_h
        bwid = r2 / 40.0 * bar_w
        solid = p < 0.05
        parts.append(f'<text x="8" y="{y + 16}" class="pl">{name}</text>')
        parts.append(
            f'<rect x="{bar_l}" y="{y + 3}" width="{bwid:.1f}" height="16" '
            f'fill="{"#087e83" if solid else "#ffffff"}" '
            f'{"" if solid else "stroke=\'#8a9aa3\' stroke-width=\'1.3\'"} rx="2"/>'
        )
        parts.append(
            f'<text x="{bar_l + bwid + 9:.1f}" y="{y + 16}" class="tk">'
            f"{r2:.0f}% of variation, p {p:.3f}</text>"
        )
    parts.append(
        f'<text x="{bar_l + bar_w / 2:.0f}" y="{h - 8}" text-anchor="middle" class="ax">'
        "Teal: month effect holds at the 5 percent level. Outline: it does not</text>"
    )
    parts.append("</svg>")
    return "\n".join(parts)


def nowcast_chart(rows):
    """Nowcast error against the two simple guesses, normal weeks and the 2020 collapse."""
    w, top, grp_h, row_h = 880, 22, 124, 26
    h = top + len(rows) * grp_h + 20
    bar_l, bar_w = 320, 360
    mx = max(max(v for _, _, v in r[1]) for r in rows) or 1
    parts = [
        f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="Nowcast error from flight miles '
        'against last week and the four-week average">'
    ]
    for gi, (title, bars) in enumerate(rows):
        gy = top + gi * grp_h
        parts.append(f'<text x="8" y="{gy + 12}" class="pl">{title}</text>')
        for bi, (lab, fill, val) in enumerate(bars):
            y = gy + 20 + bi * row_h
            bwid = val / mx * bar_w
            parts.append(f'<text x="150" y="{y + 14}" class="tk">{lab}</text>')
            parts.append(
                f'<rect x="{bar_l}" y="{y + 2}" width="{bwid:.1f}" height="14" '
                f'fill="{fill}" rx="2"/>'
            )
            parts.append(
                f'<text x="{bar_l + bwid + 9:.1f}" y="{y + 14}" class="tk">{val:.0f}</text>'
            )
    parts.append(
        f'<text x="{bar_l + bar_w / 2:.0f}" y="{h - 2}" text-anchor="middle" class="ax">'
        "Root mean squared error, thousand barrels a day. Lower is better</text>"
    )
    parts.append("</svg>")
    return "\n".join(parts)


def scatter_chart(scorecard, key):
    cand = [
        r for r in scorecard
        if r.get("group") != "flat" and not fbool(r.get("rebuilt"))
    ]
    w, h, l, rgt, top, bot = 720, 360, 54, 18, 16, 48
    x0, x1, ymax = math.log10(1.5), math.log10(80), 4.0

    def X(v):
        v = min(max(v, 1.6), 79)
        return l + (math.log10(v) - x0) / (x1 - x0) * (w - l - rgt)

    def Y(v):
        v = min(v, 3.95)
        return top + (1 - v / ymax) * (h - top - bot)

    parts = [
        f'<svg viewBox="0 0 {w} {h}" role="img" '
        'aria-label="Half-life against weekly move for candidate spreads">'
    ]
    parts.append(
        f'<rect x="{X(1.5):.1f}" y="{Y(4):.1f}" width="{X(8) - X(1.5):.1f}" '
        f'height="{Y(1) - Y(4):.1f}" fill="#e3f1f1"/>'
    )
    for v in [2, 4, 8, 16, 32, 64]:
        parts.append(
            f'<line x1="{X(v):.1f}" y1="{top}" x2="{X(v):.1f}" y2="{h - bot}" '
            f'stroke="#e4ecef"/><text x="{X(v):.1f}" y="{h - bot + 16}" '
            f'text-anchor="middle" class="tk">{v}</text>'
        )
    for v in range(5):
        parts.append(
            f'<line x1="{l}" y1="{Y(v):.1f}" x2="{w - rgt}" y2="{Y(v):.1f}" '
            f'stroke="#e4ecef"/><text x="{l - 8}" y="{Y(v) + 4:.1f}" '
            f'text-anchor="end" class="tk">{v}</text>'
        )
    parts.append(
        f'<line x1="{X(8):.1f}" y1="{top}" x2="{X(8):.1f}" y2="{h - bot}" '
        f'stroke="#087e83" stroke-width="1.4" stroke-dasharray="5 4"/>'
    )
    parts.append(
        f'<line x1="{l}" y1="{Y(1):.1f}" x2="{w - rgt}" y2="{Y(1):.1f}" '
        f'stroke="#087e83" stroke-width="1.4" stroke-dasharray="5 4"/>'
    )
    parts.append(
        f'<text x="{(l + w - rgt) / 2:.0f}" y="{h - 10}" text-anchor="middle" '
        f'class="ax">Half-life, weeks</text>'
    )
    parts.append(
        f'<text x="14" y="{(top + h - bot) / 2:.0f}" text-anchor="middle" class="ax" '
        f'transform="rotate(-90 14 {(top + h - bot) / 2:.0f})">Weekly move, c/gal</text>'
    )
    lab = {
        "LA_GC_1": (8, -8, "start"),
        "LA_JET_M2M3": (8, -4, "start"),
        "SING_GC_1": (8, 14, "start"),
        "HO_BRENT": (8, 4, "start"),
    }
    ordered = sorted(cand, key=lambda r: fbool(r.get("shortlist")))
    for r in ordered:
        hl = fnum(r.get("half_life_weeks"))
        sd = fnum(r.get("typical_weekly_move"))
        if hl is None or sd is None:
            continue
        x, y = X(hl), Y(sd)
        name = r[key]
        if fbool(r.get("shortlist")):
            parts.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="#173344" '
                f'stroke="#ffffff" stroke-width="1.4"/>'
            )
        elif fbool(r.get("rule_1_comes_back")):
            parts.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.2" fill="#087e83" fill-opacity=".7"/>'
            )
        else:
            parts.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.2" fill="#ffffff" '
                f'stroke="#8a9aa3" stroke-width="1.4"/>'
            )
        if name in lab:
            dx, dy, a = lab[name]
            parts.append(
                f'<text x="{x + dx:.1f}" y="{y + dy:.1f}" text-anchor="{a}" class="pl">{name}</text>'
            )
    parts.append("</svg>")
    return "\n".join(parts)


def fmt_cut(x):
    return f"{x:.6g}"


def fmt_date(iso):
    y, m, d = iso.split("-")
    months = ["January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December"]
    return f"{int(d)} {months[int(m) - 1]} {y}"


def compute():
    missing = [p for p in NEED if not (ROOT / p).exists()]
    if missing:
        fail(f"missing required result: {missing}")

    sc = load_csv("results/price_eda_scorecard.csv")
    ss = load_csv("results/signal_search.csv")
    fvs = load_csv("results/fair_value_scores.csv")
    bt = load_csv("results/backtest.csv")
    now = load_csv("results/nowcast_scores.csv")
    miles = load_csv("results/miles_search.csv")
    covid = load_csv("results/covid_first_signals.csv")
    steps = load_csv("results/analysis_steps.csv")

    if list(bt[0].keys()) != [
        "spread", "model", "period", "weeks", "total_cents",
        "cents_per_year", "sharpe", "weeks_won", "worst_drawdown",
    ]:
        fail("missing required result: backtest reduced schema")
    if not any(r.get("id") == "SIG_books" for r in steps):
        fail("missing required result: analysis_steps SIG_books")

    west = port_row(bt, "WEST_COAST_3")
    short = port_row(bt, "SHORTLIST_4")

    key = "series" if "series" in sc[0] else list(sc[0].keys())[0]
    cand = [r for r in sc if r.get("group") != "flat" and not fbool(r.get("rebuilt"))]
    r1 = [r for r in cand if fbool(r.get("rule_1_comes_back"))]
    r2 = [r for r in r1 if fbool(r.get("rule_2_half_life"))]
    r3 = [r for r in r2 if fbool(r.get("rule_3_moves_1c"))]
    r4 = [r for r in r3 if fbool(r.get("rule_4_best_in_cluster"))]
    shortlist = [r for r in sc if fbool(r.get("shortlist"))]
    if len(shortlist) != 4:
        fail(f"missing required result: shortlist four, got {len(shortlist)}")
    names = [r[key] for r in r4]
    if set(names) != {r[key] for r in shortlist}:
        fail("missing required result: shortlist / rule-4 mismatch")

    def row(name):
        hit = next((r for r in sc if r[key] == name), None)
        if hit is None:
            fail(f"missing required result: scorecard {name}")
        return hit

    la, sing, m2m3, ho, ny = (row(n) for n in
                              ["LA_GC_1", "SING_GC_1", "LA_JET_M2M3", "HO_BRENT", "NY_GC_1"])
    n_id = sum(1 for r in sc if fbool(r.get("rebuilt")))

    pv = [fnum(r["p_train"]) for r in ss]
    if any(p is None for p in pv):
        fail("missing required result: signal_search p_train")
    k3, cut3 = bh_cutoff(pv)
    cand_col = "confirmed" if "confirmed" in ss[0] else (
        "holdout_candidate" if "holdout_candidate" in ss[0] else None
    )
    if cand_col:
        n_hold = sum(1 for r in ss if fbool(r[cand_col]))
    else:
        n_hold = sum(
            1 for r in ss
            if fbool(r.get("fdr_pass") or r.get("bh_pass")) and fbool(r["holds_in_test"])
        )

    lo = [r for r in ss if fnum(r["p_train"]) < 0.001]
    hi = [r for r in ss if fnum(r["p_train"]) > 0.2]

    def hold_pct(rows):
        if not rows:
            fail("missing required result: search hold bin")
        return round(100 * sum(1 for r in rows if fbool(r["holds_in_test"])) / len(rows))

    la4 = next((r for r in fvs if r["spread"] == "LA_GC_1" and str(r["h"]) == "4"), None)
    if la4 is None:
        fail("missing required result: LA_GC_1 h=4 scores")
    r2fv = round(float(la4["r2_fair_value"]) * 100, 1)
    r2own = round(float(la4["r2_own"]) * 100, 1)

    def now_pct(target, period):
        hit = next((r for r in now if r["target"] == target and r["period"].startswith(period)), None)
        if hit is None:
            fail(f"missing required result: nowcast {target} {period}")
        return int(float(hit["pct_better_than_best_simple"]))

    mp = [fnum(r.get("p") or r.get("p_train")) for r in miles]
    if any(p is None for p in mp):
        fail("missing required result: miles_search p")
    k4, cut4 = bh_cutoff(mp)

    def covid_known(prefix):
        hit = next((r for r in covid if r["signal"].lower().startswith(prefix.lower())), None)
        if hit is None:
            fail(f"missing required result: covid signal {prefix}")
        return fmt_date(hit["known on"])

    scatter = scatter_chart(sc, key)
    chart = comparison_chart(west, short)
    n_pass = sum(1 for p in pv if p < 0.05)
    n_chance = round(len(pv) * 0.05)
    funnel = funnel_chart([len(cand), len(r1), len(r2), len(r3), len(r4)])
    pvchart = pvalue_chart(pv, n_pass, n_chance)
    r2rows = [
        (r["spread"], float(r["r2_own"]) * 100, float(r["r2_fair_value"]) * 100)
        for r in fvs if str(r["h"]) == "4"
    ]
    if len(r2rows) != 8:
        fail(f"missing required result: h=4 scores for 8 spreads, got {len(r2rows)}")
    r2fig = r2_chart(r2rows)
    seas = [
        (r[key], fnum(r["r_squared_month"]) * 100, fnum(r["p_month"]))
        for r in sc
        if fnum(r.get("r_squared_month")) is not None
        and fnum(r.get("p_month")) is not None
        and not fbool(r.get("rebuilt"))
    ]
    seas = sorted(seas, key=lambda t: -t[1])[:7]
    if not seas:
        fail("missing required result: scorecard month-effect columns")
    seasfig = season_chart(seas)

    def nrow(target, period):
        hit = next(
            (r for r in now if r["target"] == target and r["period"].startswith(period)),
            None,
        )
        if hit is None:
            fail(f"missing required result: nowcast {target} {period}")
        return hit

    ncrows = []
    for title, target, period in (
        ("West Coast, 53 normal weeks", "P5_JET_DEMAND", "before"),
        ("West Coast, 13 weeks of the 2020 collapse", "P5_JET_DEMAND", "COVID"),
    ):
        h4 = nrow(target, period)
        ncrows.append((title, [
            ("flight miles", "#087e83", float(h4["error_miles"])),
            ("last week", "#8a9aa3", float(h4["error_last_week"])),
            ("4-week average", "#c3ced4", float(h4["error_4wk_average"])),
        ]))
    ncfig = nowcast_chart(ncrows)
    seas_top, seas_top_r2, seas_top_p = seas[0]
    la_m = fnum(la["r_squared_month"]) * 100
    la_mp = fnum(la["p_month"])

    def share(row, key_name):
        return f"{float(row[key_name]):.2f}"

    values = {
        "{{COMP_CHART}}": chart,
        "{{SCATTER}}": scatter,
        "{{FUNNEL}}": funnel,
        "{{PVCHART}}": pvchart,
        "{{R2CHART}}": r2fig,
        "{{SEASON}}": seasfig,
        "{{NOWCHART}}": ncfig,
        "{{NCHANCE}}": str(n_chance),
        "{{SEAS_TOP}}": seas_top,
        "{{SEAS_TOP_R2}}": f"{seas_top_r2:.0f}",
        "{{SEAS_TOP_P}}": f"{seas_top_p:.3f}",
        "{{LA_MONTH}}": f"{la_m:.0f}",
        "{{LA_MONTH_P}}": f"{la_mp:.3f}",
        "{{N_CAND}}": str(len(cand)),
        "{{N_ADF}}": str(len(r1)),
        "{{N_HL}}": str(len(r2)),
        "{{N_MOVE}}": str(len(r3)),
        "{{N_SHORT}}": str(len(r4)),
        "{{N_ID}}": str(n_id),
        "{{SHORTLIST}}": ", ".join(names),
        "{{NY_SD}}": f"{fnum(ny['typical_weekly_move']):.2f}",
        "{{LA_HL}}": f"{fnum(la['half_life_weeks']):.1f}",
        "{{LA_SD}}": f"{fnum(la['typical_weekly_move']):.2f}",
        "{{SING_HL}}": f"{fnum(sing['half_life_weeks']):.1f}",
        "{{SING_SD}}": f"{fnum(sing['typical_weekly_move']):.2f}",
        "{{M2M3_HL}}": f"{fnum(m2m3['half_life_weeks']):.1f}",
        "{{M2M3_SD}}": f"{fnum(m2m3['typical_weekly_move']):.2f}",
        "{{HO_HL}}": f"{fnum(ho['half_life_weeks']):.1f}",
        "{{HO_SD}}": f"{fnum(ho['typical_weekly_move']):.2f}",
        "{{NTEST}}": f"{len(ss):,}",
        "{{NPASS}}": str(sum(1 for p in pv if p < 0.05)),
        "{{NFDR}}": str(k3),
        "{{NCONF}}": str(n_hold),
        "{{BH03}}": fmt_cut(cut3),
        "{{BH04}}": fmt_cut(cut4),
        "{{HOLD_LO}}": str(hold_pct(lo)),
        "{{HOLD_HI}}": str(hold_pct(hi)),
        "{{R2FV}}": f" {r2fv}".strip(),
        "{{R2OWN}}": f"{r2own}",
        "{{R2GAP}}": f"{round(r2fv - r2own, 1)}",
        "{{R2REST}}": f"{round(100 - r2fv, 1)}",
        "{{WEEKS}}": str(int(float(west["weeks"]))),
        "{{TOTAL}}": f"{float(west['total_cents'])}",
        "{{PY}}": f"{float(west['cents_per_year'])}",
        "{{SHARPE}}": f"{float(west['sharpe']):.2f}",
        "{{WIN}}": share(west, "weeks_won"),
        "{{DD}}": f"{float(west['worst_drawdown'])}",
        "{{STOTAL}}": f"{float(short['total_cents'])}",
        "{{SPY}}": f"{float(short['cents_per_year'])}",
        "{{SSHARPE}}": f"{float(short['sharpe']):.2f}",
        "{{SWIN}}": share(short, "weeks_won"),
        "{{SDD}}": f"{float(short['worst_drawdown'])}",
        "{{NOW_P5}}": str(now_pct("P5_JET_DEMAND", "before")),
        "{{NOW_US}}": str(now_pct("US_JET_DEMAND", "before")),
        "{{NOW_P5_4W}}": str(now_pct("P5_JET_DEMAND_4W", "before")),
        "{{NOW_US_4W}}": str(now_pct("US_JET_DEMAND_4W", "before")),
        "{{NOW_COVID}}": str(now_pct("P5_JET_DEMAND", "COVID")),
        "{{MILESN}}": str(len(miles)),
        "{{MILESP}}": str(sum(1 for p in mp if p < 0.05)),
        "{{MILESFDR}}": str(k4),
        "{{COVID_CRACK}}": covid_known("Gulf Coast"),
        "{{COVID_P1M}}": covid_known("East Coast miles"),
        "{{COVID_EIA}}": covid_known("EIA weekly"),
        "{{COVID_P5M}}": covid_known("West Coast miles"),
        "{{COVID_EIA4}}": covid_known("EIA 4-week"),
    }
    return values


def visible_words(html_text):
    t = re.sub(r"<script\b[^>]*>.*?</script>", " ", html_text, flags=re.I | re.S)
    t = re.sub(r"<style\b[^>]*>.*?</style>", " ", t, flags=re.I | re.S)
    t = re.sub(r"<svg\b[^>]*>.*?</svg>", " ", t, flags=re.I | re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t)
    t = re.sub(r"\s+", " ", t).strip()
    return t.split() if t else []


def check_page(name, text):
    if PLACEHOLDER_RE.search(text):
        fail(f"{name}: unfilled placeholders")
    if ANALYTICS_RE.search(text):
        fail(f"{name}: external analytics")
    if ABS_PATH_RE.search(text):
        fail(f"{name}: absolute local path")
    prose = " ".join(visible_words(text))
    if re.search(r"Energy Aspects", prose):
        fail(f"{name}: forbidden comparison language")
    for href in HREF_RE.findall(text):
        if href.startswith("#") or href.startswith("data:"):
            continue
        if re.match(r"https?:", href, re.I) or href.startswith("//"):
            fail(f"{name}: non-local link {href}")
        target = (href.split("#", 1)[0]).split("?", 1)[0]
        if not target:
            continue
        path = (OUT / target).resolve()
        try:
            path.relative_to(OUT.resolve())
        except ValueError:
            fail(f"{name}: link escapes docs {href}")
        if not path.exists() and target not in ("index.html", "detail.html"):
            fail(f"{name}: broken local link {href}")
    n = len(visible_words(text))
    cap = WORD_CAPS[name]
    if n > cap:
        fail(f"{name}: visible-word cap {n} > {cap}")
    return n


def page_tokens(text):
    return {"{{" + m + "}}" for m in re.findall(r"\{\{([A-Za-z0-9_]+)\}\}", text)}


def build(check_only=False):
    templates = {"index.html": INDEX_TPL, "detail.html": DETAIL_TPL}
    values = compute()
    want = page_tokens(INDEX_TPL) | page_tokens(DETAIL_TPL)
    extra = sorted(set(values) - want)
    missing = sorted(want - set(values))
    if extra:
        fail(f"unused computed result: {extra[:8]}")
    if missing:
        fail(f"missing required result: {missing[:8]}")
    by_page = {
        name: {k: values[k] for k in page_tokens(text)}
        for name, text in templates.items()
    }
    rendered = validate_render(templates, by_page)
    charts = 0
    words = {}
    for name, text in rendered.items():
        charts += len(re.findall(r"<svg\b", text, re.I))
        words[name] = check_page(name, text)
    if charts > CHART_CAP:
        fail(f"chart cap {charts} > {CHART_CAP}")
    if check_only:
        print(
            f"check ok: placeholders filled, {charts} charts, "
            f"index {words['index.html']} words, detail {words['detail.html']} words"
        )
        return rendered
    for name, text in rendered.items():
        (OUT / name).write_text(text, encoding="utf-8")
        print(f"docs/{name}", words[name], "words", len(text) // 1024, "KB")
    return rendered


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    build(check_only="--check" in args)


if __name__ == "__main__":
    main()
