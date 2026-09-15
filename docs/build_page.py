"""Build docs/index.html from results/ and data/weekly_panel.csv."""
import json
import math
import shutil
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs'
SPREADS = ['LA_GC_1', 'LA_JET_M1M2', 'LA_JET_M2M3', 'SING_GC_1', 'NWE_GC_1', 'NY_GC_1', 'GC_JET_M1M2', 'HO_BRENT']

PANEL = pd.read_csv(ROOT / 'data/weekly_panel.csv', index_col=0, parse_dates=True)
WF = pd.read_csv(ROOT / 'results/fair_value_walkforward.csv', parse_dates=['week'])
BT = pd.read_csv(ROOT / 'results/backtest.csv')
FVS = pd.read_csv(ROOT / 'results/fair_value_scores.csv')
SC = pd.read_csv(ROOT / 'results/price_eda_scorecard.csv', index_col=0)
NOW = pd.read_csv(ROOT / 'results/nowcast_scores.csv')
SS = pd.read_csv(ROOT / 'results/signal_search.csv')

# ---------- embedded weekly data ----------
DATA = {}
for sp in SPREADS:
    g = WF[(WF['spread'] == sp) & (WF['h'] == 4)].set_index('week')
    s = PANEL[sp]
    move = (s.shift(-2) - s.shift(-1)).reindex(g.index)
    r = lambda v: [None if pd.isna(x) else round(float(x), 6) for x in v]
    DATA[sp] = {'week': [d.strftime('%Y-%m-%d') for d in g.index], 'level': r(g['spread_level']), 'fv': r(g['fair_value']),
                'f_own': r(g['f_own']), 'f_fair_value': r(g['f_fair_value']), 'f_both': r(g['f_both']), 'move': r(move)}

EXPECT = []
for _, row in BT.iterrows():
    EXPECT.append({'spread': row['spread'], 'model': row['model'], 'period': 'pre' if row['period'].startswith('2017') else 'covid',
                   'total': row['total_cents'], 'sharpe': row['sharpe'], 'weeks': int(row['weeks'])})
EXPECT_BOOKS = [
    {'spreads': ['LA_GC_1', 'LA_JET_M1M2', 'LA_JET_M2M3'], 'perYear': 28.8, 'sharpe': 1.50, 'drawdown': -14.0},
    {'spreads': ['LA_GC_1', 'LA_JET_M2M3', 'SING_GC_1', 'HO_BRENT'], 'perYear': 16.4, 'sharpe': 0.63, 'drawdown': -38.3},
]
SCORES = {}
for _, row in FVS.iterrows():
    SCORES.setdefault(row['spread'], {})[int(row['h'])] = {k: float(row[k]) for k in ['r2_own', 'hit_own', 'r2_fair_value', 'hit_fair_value', 'r2_both', 'hit_both']}


# ---------- static pieces ----------
LEGS = {'LA_GC_1': 'Los Angeles jet − Gulf Coast jet, front month', 'LA_JET_M1M2': 'Los Angeles jet, front month − second month', 'LA_JET_M2M3': 'Los Angeles jet, second month − third month', 'SING_GC_1': 'Singapore kerosene − Gulf Coast jet, front month', 'NWE_GC_1': 'Northwest Europe jet − Gulf Coast jet, front month', 'NY_GC_1': 'New York Harbor jet − Gulf Coast jet, front month', 'GC_JET_M1M2': 'Gulf Coast jet, front month − second month', 'HO_BRENT': 'NYMEX heating oil − Brent crude, front month'}
REGION = {'P1': 'PADD 1', 'P3': 'PADD 3', 'P5': 'PADD 5', 'US': 'US'}
BODY = {'JET_STOCKS_VS_5Y': 'jet stocks against 5-year normal', 'DIST_STOCKS_VS_5Y': 'distillate stocks against 5-year normal',
        'OUTPUT_VS_52W': 'jet output against prior 52-week mean', 'RUNS_VS_5Y': 'refinery runs against 5-year normal',
        'UTIL_VS_5Y': 'refinery utilization against 5-year normal', 'DAYS_SUPPLY': 'days of supply', 'DEMAND': 'jet demand',
        'IMPORTS_4W': '4-week jet imports', 'EXPORTS_4W': '4-week jet exports', 'STOCK_SURPRISE': 'stock surprise'}


def plain(code):
    chg = code.endswith('_CHG4')
    core = code[:-5] if chg else code
    text = f"{REGION[core[:2]]} {BODY[core[3:]]}" + (', 4-week change' if chg else '')
    return f'{text} <span class="sub">({code})</span>'


def trs(rows, num=()):
    return '\n'.join('<tr>' + ''.join(f'<td class="n">{c}</td>' if i in num else f'<td>{c}</td>' for i, c in enumerate(row)) + '</tr>' for row in rows)


cand = SC[(SC['group'] != 'flat') & (~SC['rebuilt'])]
r1 = cand[cand['rule_1_comes_back']]
r2 = r1[r1['rule_2_half_life']]
r3 = r2[r2['rule_3_moves_1c']]
r4 = r3[r3['rule_4_best_in_cluster']]
n_id = int(SC['rebuilt'].sum())
FUNNEL = trs([
    ('Spreads, diffs, cracks built from Prices.csv', len(cand) + n_id, 'c/gal'),
    ('After identities', len(cand), f'{n_id} exact sums removed'),
    ('ADF p &lt; 0.05', len(r1), 'level reverts'),
    ('Half-life ≤ 8 weeks', len(r2), 'log(0.5) / log(φ)'),
    ('Weekly sd ≥ 1 c/gal', len(r3), 'sd of weekly changes'),
    ('Largest weekly sd in cluster', len(r4), ', '.join(r4.index)),
], num={1})

NAMES = {'flat': 'Flat prices', 'regional': 'Regional', 'foreign': 'Foreign against GC', 'time': 'Time spreads',
         'diff': 'Jet-HO diffs', 'crack': 'Cracks', 'other': 'Other'}
live = SC[~SC['rebuilt']]
stat = []
for g, name in NAMES.items():
    d = live[live['group'] == g]
    v = d['verdict'].value_counts()
    stat.append((name, len(d), int(v.get('fixed level', 0)), int(v.get('shifting level', 0)), int(v.get('wanders', 0)),
                 f"{d['half_life_weeks'].min():.1f} to {d['half_life_weeks'].max():.1f}"))
STAT = trs(stat, num={1, 2, 3, 4, 5})

vif = live[live['vif'] > 10].sort_values('vif', ascending=False)
VIF = trs([(n, f"{r['vif']:.1f}", int(r['cluster'])) for n, r in vif.iterrows()], num={1, 2})
sea = live[live['r_squared_month'].notna()].sort_values('r_squared_month', ascending=False).head(8)
SEA = trs([(n, f"{r['r_squared_month']:.2f}", f"{r['p_month']:.3f}") for n, r in sea.iterrows()]
          + [('LA_GC_1', f"{SC.loc['LA_GC_1', 'r_squared_month']:.2f}", f"{SC.loc['LA_GC_1', 'p_month']:.3f}")], num={1, 2})
SHORT = trs([(n, f"{r['adf_p']:.3f}", r['verdict'], f"{r['half_life_weeks']:.1f}", f"{r['typical_weekly_move']:.2f}", int(r['cluster']))
             for n, r in r4.iterrows()], num={1, 3, 4, 5})

# scatter
W, H, L, R, T, B = 720, 400, 58, 20, 18, 52
x0, x1, ymax = math.log10(1.5), math.log10(80), 4.0
X = lambda v: L + (math.log10(v) - x0) / (x1 - x0) * (W - L - R)
Y = lambda v: T + (1 - v / ymax) * (H - T - B)
sv = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Half-life against weekly standard deviation for 30 candidate series">',
      f'<rect x="{X(1.5):.1f}" y="{Y(4):.1f}" width="{X(8) - X(1.5):.1f}" height="{Y(1) - Y(4):.1f}" fill="#e3f1f1"/>']
for v in [2, 4, 8, 16, 32, 64]:
    sv.append(f'<line x1="{X(v):.1f}" y1="{T}" x2="{X(v):.1f}" y2="{H - B}" stroke="#e4ecef"/><text x="{X(v):.1f}" y="{H - B + 18}" text-anchor="middle" class="tk">{v}</text>')
for v in range(5):
    sv.append(f'<line x1="{L}" y1="{Y(v):.1f}" x2="{W - R}" y2="{Y(v):.1f}" stroke="#e4ecef"/><text x="{L - 8}" y="{Y(v) + 4:.1f}" text-anchor="end" class="tk">{v}</text>')
sv.append(f'<line x1="{X(8):.1f}" y1="{T}" x2="{X(8):.1f}" y2="{H - B}" stroke="#087e83" stroke-width="1.5" stroke-dasharray="5 4"/>')
sv.append(f'<line x1="{L}" y1="{Y(1):.1f}" x2="{W - R}" y2="{Y(1):.1f}" stroke="#087e83" stroke-width="1.5" stroke-dasharray="5 4"/>')
sv.append(f'<text x="{X(8) + 6:.1f}" y="{T + 14}" class="tk">8 weeks</text><text x="{W - R - 4}" y="{Y(1) - 7:.1f}" text-anchor="end" class="tk">1 c/gal</text>')
sv.append(f'<text x="{(L + W - R) / 2:.0f}" y="{H - 10}" text-anchor="middle" class="ax">Half-life, weeks (log scale)</text>')
sv.append(f'<text x="14" y="{(T + H - B) / 2:.0f}" text-anchor="middle" class="ax" transform="rotate(-90 14 {(T + H - B) / 2:.0f})">Weekly sd, c/gal</text>')
LAB = {'LA_GC_1': (8, -8, 'start'), 'LA_JET_M2M3': (8, -4, 'start'), 'SING_GC_1': (8, 14, 'start'), 'HO_BRENT': (8, 4, 'start'), 'NY_GC_1': (-8, 14, 'end')}
for n, r in cand.assign(k=cand['shortlist'].astype(int)).sort_values('k').iterrows():
    x, y = X(min(max(r['half_life_weeks'], 1.6), 79)), Y(min(r['typical_weekly_move'], 3.95))
    tip = f"<title>{n}: ADF p {r['adf_p']}, half-life {r['half_life_weeks']}, sd {r['typical_weekly_move']}</title>"
    if r['shortlist']:
        sv.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6.5" fill="#173344" stroke="#ffffff" stroke-width="1.5">{tip}</circle>')
    elif r['rule_1_comes_back']:
        sv.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="#087e83" fill-opacity=".7">{tip}</circle>')
    else:
        sv.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="#ffffff" stroke="#8a9aa3" stroke-width="1.5">{tip}</circle>')
    if n in LAB:
        dx, dy, a = LAB[n]
        sv.append(f'<text x="{x + dx:.1f}" y="{y + dy:.1f}" text-anchor="{a}" class="pl{" b" if r["shortlist"] else ""}">{n}</text>')
sv.append('</svg>')
SCATTER = '\n'.join(sv)

HYP = trs([
    ('LA_GC_1', 'PADD 5 jet stocks against 5-year normal', '−', '−0.16'),
    ('LA_GC_1', 'PADD 5 days of supply', '−', '−0.14'),
    ('LA_GC_1', 'PADD 5 runs against 5-year normal', '−', '−0.14'),
    ('LA_GC_1', 'PADD 5 jet output against prior 52 weeks', '−', '−0.31'),
    ('LA_GC_1', 'PADD 3 jet stocks against 5-year normal', '+', '−0.04'),
    ('LA_JET_M2M3', 'PADD 5 jet stocks against 5-year normal', '−', '−0.01'),
    ('LA_JET_M2M3', 'PADD 5 days of supply', '−', '−0.20'),
    ('SING_GC_1', 'PADD 3 jet stocks against 5-year normal', '+', '+0.32'),
    ('SING_GC_1', 'PADD 3 runs against 5-year normal', '+', '+0.34'),
    ('NY_GC_1', 'PADD 1 jet stocks against 5-year normal', '−', '−0.22'),
    ('GC_JET_M1M2', 'PADD 3 jet stocks against 5-year normal', '−', '−0.20'),
    ('HO_BRENT', 'US distillate stocks against 5-year normal', '−', '−0.68'),
    ('HO_BRENT', 'PADD 1 distillate stocks against 5-year normal', '−', '−0.69'),
    ('HO_BRENT', 'US utilization against 5-year normal', '−', '−0.13'),
], num={2, 3})
DRIVERS = {
    'LA_GC_1': 'PADD 5 days of supply · PADD 5 runs · PADD 3 jet stocks', 'LA_JET_M1M2': 'PADD 5 days of supply · PADD 5 runs',
    'LA_JET_M2M3': 'PADD 5 days of supply · PADD 5 runs', 'SING_GC_1': 'PADD 3 jet stocks · PADD 3 runs',
    'NWE_GC_1': 'PADD 3 jet stocks · PADD 3 runs', 'NY_GC_1': 'PADD 1 jet stocks · PADD 3 jet stocks',
    'GC_JET_M1M2': 'PADD 3 jet stocks · PADD 3 runs', 'HO_BRENT': 'US distillate stocks · US utilization'}
f4 = FVS[FVS['h'] == 4].set_index('spread')
DRV = trs([(sp, DRIVERS[sp], f"{f4.loc[sp, 'r2_own'] * 100:.1f}", f"{f4.loc[sp, 'r2_fair_value'] * 100:.1f}", f"{f4.loc[sp, 'hit_fair_value'] * 100:.0f}") for sp in SPREADS], num={2, 3, 4})

conf = SS[SS['confirmed']]
CONF = trs([(r['spread'], plain(r['physical_number']), int(r['h']), f"{r['p_train']:.4f}", f"{r['b_train']:.2f}", f"{r['b_test']:.2f}") for _, r in conf.iterrows()], num={2, 3, 4, 5})
bins = SS.groupby('training_strength', sort=False)['holds_in_test'].agg(['size', 'mean'])
HOLD = trs([(k, int(v['size']), f"{v['mean'] * 100:.0f}%") for k, v in bins.iterrows()], num={1, 2})

TARGET = {'P5_JET_DEMAND': 'PADD 5 weekly demand', 'P5_JET_DEMAND_4W': 'PADD 5 4-week demand', 'US_JET_DEMAND': 'US weekly demand', 'US_JET_DEMAND_4W': 'US 4-week demand'}
NOWT = trs([(TARGET[r['target']], r['period'], int(r['weeks']), f"{r['error_miles']:.1f}", f"{r['error_last_week']:.1f}", f"{r['error_4wk_average']:.1f}", f"{r['pct_better_than_best_simple']:+.0f}%")
            for _, r in NOW.iterrows()], num={2, 3, 4, 5, 6})

SPREAD_OPTS = '\n'.join(f'<option value="{sp}" title="{LEGS[sp]}">{sp}</option>' for sp in SPREADS)
CHECKS = '\n'.join(f'<label class="chk" for="bk_{sp}"><input type="checkbox" id="bk_{sp}" value="{sp}"{" checked" if sp in ("LA_GC_1", "LA_JET_M1M2", "LA_JET_M2M3") else ""}><span class="chk-code">{sp}</span><span class="chk-legs">{LEGS[sp]}</span></label>' for sp in SPREADS)

HTML = (OUT / 'template.html').read_text(encoding='utf-8')
for key, val in {
    '{{FUNNEL}}': FUNNEL, '{{STAT}}': STAT, '{{VIF}}': VIF, '{{SEA}}': SEA, '{{SHORT}}': SHORT, '{{SCATTER}}': SCATTER,
    '{{HYP}}': HYP, '{{DRV}}': DRV, '{{CONF}}': CONF, '{{HOLD}}': HOLD, '{{NOWT}}': NOWT, '{{SPREAD_OPTS}}': SPREAD_OPTS,
    '{{CHECKS}}': CHECKS,
    '{{DATA}}': json.dumps({'series': DATA, 'expect': EXPECT, 'books': EXPECT_BOOKS, 'scores': SCORES}, separators=(',', ':')),
}.items():
    assert key in HTML, key
    HTML = HTML.replace(key, val)
(OUT / 'index.html').write_text(HTML, encoding='utf-8')
(OUT / 'figures').mkdir(exist_ok=True)
for f in ['search_carryover.png', 'nowcast_west_coast.png', 'covid_timeline.png']:
    shutil.copy(ROOT / 'figures' / f, OUT / 'figures' / f)
print('docs/index.html', len(HTML) // 1024, 'KB')
