# Regional Jet-Fuel Spreads Arbitrage During COVID Shutdowns

**Dashboard: https://mosesrahnama.github.io/regional-jet-fuel-arbitrage/**

Statistical analysis of saved 2011-2020 weekly jet-fuel spreads and physical market data. The
dashboard carries the thesis and the headline figures on its first page, and the methods, the
diagnostic tests and the seven charts on its second.

## Reproduce

pip install -r requirements.txt
python verify.py

## Notebooks

01_price_eda: spread stationarity screens and the 4-spread descriptive shortlist.
02_fundamentals_panel: weekly physical panel build.
03_signal_search: 3,240-regression search, fair-value walk-forward, raw-price direction check.
04_air_traffic: flight-miles demand nowcast and spread search.

## Findings

30 candidate spreads narrow to 4 descriptive shortlist entries.
3,240 regressions give 264 nominal p-values below 0.05, 15 Benjamini-Hochberg survivors, 3 held-out candidates.
Air-traffic search gives 720 tests, 70 nominal results, and 11 Benjamini-Hochberg survivors that remain in-sample.
For Los Angeles minus Gulf Coast at four weeks, fair-value R-squared is 17.9% versus 12.6% for the own-history baseline.
Over 53 pre-COVID weeks, the weekly demand nowcast lowers error by 3% to 4%; the four-week demand version raises error by 33% to 63%.

## Raw-price direction check

Four-week forecast direction is scored against the following week's average-to-average spread change with a one-week hold. This is a stylized gross price-path test using revised EIA history. Totals and drawdown are cents per gallon; winning weeks are a share; Sharpe is unitless. Simple annualized Sharpe assumes independent weeks. Both portfolios are retrospective.

West Coast three, 163 weeks: 135.9 total, 43.4 per year, Sharpe 2.29, winning-week share 0.65, drawdown -12.5.
Four-spread shortlist, 163 weeks: 105.3 total, 33.6 per year, Sharpe 1.30, winning-week share 0.60, drawdown -33.5.

The historical gross price-path simulation produces positive cumulative spread changes. It uses weekly average prices and current revised EIA history; achievable account results also depend on execution costs and real-time data.
