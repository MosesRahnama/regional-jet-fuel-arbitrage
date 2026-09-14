# Regional jet fuel arbitrage

**Dashboard: https://mosesrahnama.github.io/regional-jet-fuel-arbitrage/**

US regional jet spreads revert to a fair value fitted each week on EIA stocks, refinery runs and jet output. OpenSky flight miles give PADD 1 and PADD 5 jet demand 4 days before the EIA publishes it.

| Result | Value |
|---|---|
| West Coast three (LA_GC_1, LA_JET_M1M2, LA_JET_M2M3), 2017-01 to 2020-02 | 28.8 c/gal a year, Sharpe 1.50, max drawdown 14.0 c/gal |
| Same rule, 14 COVID weeks | +103.1 c/gal |
| Notebook 01 shortlist (LA_GC_1, LA_JET_M2M3, SING_GC_1, HO_BRENT) | 16.4 c/gal a year, Sharpe 0.63 |
| LA_GC_1, 4-week out-of-sample R² | 17.9% fair value, 12.6% own 26-week mean |
| Open search, 3,240 regressions | 264 with train p < 0.05 (162 by chance), 16 pass FDR, 3 confirmed in test |
| Miles nowcast of EIA demand, error against best benchmark | 3 to 4% lower in normal weeks, 10 to 34% lower in COVID weeks |
| Break-even cost per unit traded, 2017-01 to 2020-02 | West Coast three 0.74 c/gal; shortlist 0.49 c/gal |

Backtest rules: walk-forward fit on weeks up to t, position = sign of the 4-week forecast, entry at next week's mean price, one-week hold, 0.25 c/gal per unit traded.

## Notebooks

Run in order from `notebooks/`.

| Notebook | Content | Output |
|---|---|---|
| 01_price_eda | units, defects, ADF/KPSS, ACF/PACF, half-life, PCA, VIF, Granger, seasonality, shortlist | data/prices_clean.csv, results/price_eda_scorecard.csv |
| 02_fundamentals_panel | EIA balances against 5-year normal, PADD 5 and US demand, days of supply, publication dates | data/weekly_panel.csv |
| 03_signal_search | 3,240-regression search with FDR, weekly fair values, backtest | results/signal_search.csv, fair_value_walkforward.csv, backtest.csv |
| 04_air_traffic | miles nowcast, COVID sequence, miles against spreads | results/nowcast_scores.csv, miles_search.csv, covid_first_signals.csv |

Dashboard source: `docs/template.html` and `docs/build_page.py`; the built page is served from the `gh-pages` branch.

## Data

| Folder | Contents |
|---|---|
| bloomberg_data | weekly prices, 21 products × 6 delivery months, 2011-01 to 2020-06; EIA weekly series |
| supporting_data | EIA PADD balances from 2015; OpenSky miles and monthly demand, 2019-01 to 2020-06 |
| eia_imp_exp | EIA jet imports, exports and inter-PADD movements, weekly and monthly |
| airports_planes | ICAO airport list |
| python_modules | 2020 download scripts: Bloomberg, EIA, OpenSky |

## Limits

| Limit | Effect |
|---|---|
| Liquidity: bid-ask, depth and volume for LA, GC and NY jet swaps are outside the dataset | results assume fills at 0.25 c/gal per unit and 50,000 bbl per spread; West Coast three Sharpe 0.72 at 0.50 c/gal, −0.69 at 1.00 c/gal |
| Weekly prices = mean of 5 daily settlements | fills at weekly mean price |
| Test sample: 163 weeks + 14 COVID weeks | Sharpe from 163 weeks |
| Miles: 75 weeks; level drifts with OpenSky receiver count | miles price test open |
| PADD 5 weekly exports from monthly shares | error about 7 kb/d |

Requirements: Python 3, pandas, numpy, statsmodels, scipy, matplotlib, nbformat.
