# Treasury Futures Basis Trading

A Python framework to analyze the valuation gap between U.S. Treasury bonds and 
their futures contracts — covering bond pricing, cheapest-to-deliver selection, 
cash-and-carry strategy simulation and risk analysis.

Built as a quantitative research project for Sales & Trading interview preparation.

---

## Research Question

Under what conditions does the valuation gap between a U.S. Treasury bond and its 
futures contract represent a cash-and-carry opportunity, after accounting for 
financing costs, coupons, transaction costs and hedging risk?

The project answers this in two layers:

- **Layer A** — a pricing and analysis engine built entirely on free public data 
  (FRED yields, CME conversion factor formula, Hull futures pricing)
- **Layer B** — a strategy simulation and risk framework, with explicit 
  documentation of where simulated inputs replace unavailable market data

---

## Why This Project

Treasury basis trading sits at the intersection of fixed income pricing, repo 
financing and futures mechanics. It requires understanding:

- How a bond's price responds to rate moves (duration, DV01, convexity)
- How futures contracts handle delivery of non-identical bonds (conversion factors)
- Why the cheapest-to-deliver bond changes as rates move
- How financing costs determine whether an apparent arbitrage is actually profitable

These are exactly the mechanics a rates trader works with daily.

---

## Libraries Used

| Library | Role in this project |
|---------|---------------------|
| `pandas` | Time series manipulation — FRED data loading, cleaning, alignment of yield and financing series, DataFrame-based bond basket handling |
| `numpy` | Numerical computation — continuous compounding (`np.exp`), rate shock grids (`np.linspace`), array operations on basis series |
| `matplotlib` | All visualizations — yield curves, basis time series, z-score signals, P&L curves, drawdown charts, CTD switch heatmaps |
| `pandas-datareader` | Direct FRED API access — downloads DGS10, SOFR and EFFR series without manual CSV handling |
| `pytest` | Unit testing — validates pricing formulas against textbook examples, checks for look-ahead bias, verifies CTD selection consistency |
| `streamlit` | Interactive dashboard — parameter sliders, live strategy recalculation, tabbed analysis views |
| `scipy` | Numerical utilities (reserved for yield solving if extended) |
| `ipykernel` | Jupyter kernel integration with the project's virtual environment |

**Deliberately not used:** `QuantLib`. While it offers professional-grade bond 
calendars and day count conventions, implementing the pricing logic manually makes 
the mechanics explicit and auditable — which matters more for an interview project 
than production-grade precision.

---

## Project Structure
treasury-basis-trading/
│
├── data/
│ ├── raw/ # Downloaded FRED files (gitignored)
│ ├── processed/ # Cleaned data (gitignored)
│ └── sample/ # Small synthetic datasets for testing
│
├── notebooks/
│ ├── 01_data_exploration.ipynb # FRED pipeline, data quality checks
│ ├── 02_bond_pricing.ipynb # Price/yield relationship, DV01 validation
│ ├── 03_basis_analysis.ipynb # Hull pricing, CTD selection, rate shocks
│ ├── 04_strategy.ipynb # Z-score signals, P&L simulation
│ └── 05_risk_analysis.ipynb # Sharpe, drawdown, sensitivity, stress tests
│
├── src/treasury_basis/
│ ├── data_loader.py # FRED data pipeline
│ ├── bond_pricing.py # Pricing, accrued interest, DV01, conversion factors
│ ├── futures.py # Hull futures pricing, CTD identification
│ ├── basis.py # Gross basis, carry, net basis, implied repo rate
│ ├── strategy.py # Signal generation, P&L calculation
│ └── risk.py # Performance metrics, sensitivity, stress testing
│
├── tests/
│ ├── test_bond_pricing.py # Pricing and CF validation
│ ├── test_basis.py # Basis formulas, CTD consistency, Hull example
│ └── test_backtest.py # Signal logic, look-ahead bias, risk metrics
│
├── app.py # Streamlit dashboard
├── setup.py # Package configuration for local imports
├── requirements.txt
└── README.md

**Why `src/` and `notebooks/` are separate:** notebooks are for exploration and 
narrative. `src/` holds validated, reusable, tested functions. This separation 
means the same pricing logic powers the notebooks, the tests and the dashboard 
without duplication.

---

## Functions Reference

### `bond_pricing.py` — Bond valuation primitives

**`price_bond_simple(face, coupon_rate, yield_rate, periods)`**

Computes the dirty price of a fixed-coupon bond by discounting all future cash 
flows at the market yield:

$$P = \sum_{i=1}^{n} \frac{C/2}{(1 + y/2)^i} + \frac{100}{(1 + y/2)^n}$$

Uses the closed-form annuity formula rather than a loop — faster and numerically 
stable. Returns the **dirty** price (including accrued interest), which is the 
economically correct price for discounting purposes.

*Validation:* when coupon rate equals yield, the price is exactly 100 (at par). 
This is tested in `test_at_par()`.

**`accrued_interest(face, coupon_rate, days_since_coupon, days_in_period)`**

Computes interest accrued since the last coupon payment, pro-rated by days 
elapsed. Follows the Actual/Actual convention used on U.S. Treasuries.

Market quotes use the **clean** price (excluding accrued interest) so that prices 
don't jump artificially on coupon dates. The relationship is:

$$P_{clean} = P_{dirty} - AI$$

**`dv01(face, coupon_rate, yield_rate, periods)`**

Computes the dollar value of a 1 basis point move via symmetric numerical shock:

$$DV01 = \frac{P(y - 0.0001) - P(y + 0.0001)}{2}$$

*Why symmetric shock rather than analytical duration:* the numerical approach 
captures convexity effects automatically and generalizes to any pricing function 
without re-deriving a formula. The symmetric (two-sided) version is more accurate 
than a one-sided shock because first-order errors cancel.

**`calcul_cf(coupon_rate, periods)`**

Computes the CME conversion factor — the bond's price per dollar of principal 
assuming a flat 6% yield with semi-annual compounding:

$$CF = \sum_{i=1}^{n} \frac{c/2}{1.03^i} + \frac{1}{1.03^n}$$

*Why 6%:* the CME fixed this reference rate when standardizing Treasury futures. 
It creates a predictable property — bonds with coupons below 6% have CF < 1, 
above 6% have CF > 1. This asymmetry is what drives CTD switches as rates move.

*Validation:* a 10% coupon, 20-year bond gives CF = 1.4623, matching the textbook 
example. Tested in `test_calcul_cf_hull_example()`.

---

### `futures.py` — Futures pricing and CTD selection

**`futures_quoted_price(clean_price, coupon, CF, days_since_coupon, days_to_next_coupon, days_to_delivery, days_in_period, rate)`**

Implements the Hull futures pricing method in five explicit steps:

1. **Dirty price today** — clean price plus accrued interest
2. **Present value of coupons** received during the futures contract life, 
   discounted at continuous compounding: $PV = C \cdot e^{-rt}$
3. **Cash futures price** — $F_0 = (S_0 - I) \cdot e^{rT}$
4. **Accrued interest at delivery** — subtracted to get the clean futures price
5. **Quoted price** — divided by the conversion factor

Returns a dictionary with **every intermediate step**, not just the final price. 
This makes the calculation auditable — you can verify each stage independently, 
which is essential when debugging pricing logic.

*Why continuous compounding:* it's the standard convention in derivatives pricing 
(Hull, Black-Scholes framework) and avoids compounding frequency ambiguity when 
the holding period isn't a whole number of coupon periods.

*Validation:* reproduces the textbook example exactly — a 12% coupon bond at 115, 
CF 1.6, 270 days to delivery, 10% flat curve gives a quoted futures price of 71.79. 
Tested in `test_futures_price_hull_example()`.

**`identifier_ctd(obligations, rate, ...)`**

First-generation CTD identification. For each bond in the deliverable basket, 
computes the price, the theoretical futures price via Hull, the delivery cost and 
the implied repo rate. Identifies the CTD as the bond minimizing:

$$Delivery\ cost = P_{clean} - F \times CF$$

*Why delivery cost and not implied repo rate:* both criteria are theoretically 
equivalent — the bond minimizing delivery cost is the one maximizing IRR. This 
equivalence is explicitly tested in `test_ctd_same_by_cost_and_irr()`. Using 
delivery cost is more direct and matches how the short position actually decides 
what to deliver.

*Known limitation:* because the futures price is computed from each bond's own 
characteristics, the conversion factor partially cancels algebraically in the 
delivery cost expression. The result is that the CTD ranking barely changes with 
rates — no switches appear. This led to the second function below.

**`identifier_ctd_avec_recalibrage(obligations, rate, ..., n_iterations)`**

Second-generation CTD identification with iterative price recalibration. This 
reflects how the market actually works:

1. The futures price is anchored on the **current** CTD
2. All bonds' delivery costs are computed against **that** futures price
3. If a different bond is now cheapest, it becomes the new CTD
4. The futures price re-anchors on the new CTD
5. Repeat until the CTD stops changing (convergence, typically 2-3 iterations)

*Why this matters:* in reality the futures price isn't computed independently for 
each deliverable bond — it's a single market price anchored on whichever bond is 
currently cheapest to deliver. When rates move enough for a different bond to take 
over, the futures price recalibrates. This circularity is what produces genuine 
CTD switches.

*Result:* with a basket spanning coupons from 2% to 11%, switches appear at 5.62% 
(OBL_A → OBL_F) and 7.23% (OBL_F → OBL_E) — consistent with CME theory where low-
coupon bonds dominate below the 6% reference and high-coupon bonds above it.

*Documented artifact:* the recalibration is instantaneous in the model, which 
creates visible discontinuities in the IRR and basis plots at switch points. Real 
markets adjust progressively as participants reprice.

---

### `basis.py` — Basis and carry calculations

**`gross_basis(p_clean, F, CF)`**

The raw valuation gap:

$$Gross\ Basis = P_{clean} - F \times CF$$

Note this is numerically identical to the delivery cost used for CTD selection — 
they are the same quantity viewed from different angles.

**`carry(p_dirty, financing_rate, coupon_received, holding_days)`**

Net profit from holding the bond over the trade's life:

$$Carry = Coupon\ received - Financing\ cost$$

where financing cost is $P_{dirty} \times r \times \frac{days}{360}$.

*Why 360 and not 365:* money market convention for repo financing in USD. Using 
365 would understate the financing cost by roughly 1.4%.

*Why `p_dirty` and not `p_clean` as the financed amount:* you pay the full dirty 
price to acquire the bond, so that's what you need to borrow.

**`net_basis(...)`**

$$Net\ Basis = Gross\ Basis - Carry$$

The economically meaningful measure — gross basis tells you the apparent gap, net 
basis tells you what's left after financing.

**`implied_repo_rate(p_dirty, F, CF, ai_delivery, days)`**

$$IRR = \frac{F \times CF + AI_{delivery} - P_{dirty}}{P_{dirty}} \times \frac{360}{days}$$

The financing rate at which cash-and-carry breaks even. Compare it to the actual 
repo rate: IRR above market repo means the trade is profitable, below means it 
loses money.

---

### `strategy.py` — Signal generation and P&L

**`calculate_zscore(series, window=60)`**

Rolling z-score of the basis:

$$z_t = \frac{basis_t - \mu_{t-60:t}}{\sigma_{t-60:t}}$$

*Why rolling and not a fixed historical mean:* markets change regime. A 60-day 
rolling window (roughly one quarter) adapts to shifts in the basis level while 
still having enough observations for a stable standard deviation estimate.

**`generate_signals(zscore, entry_threshold, exit_threshold)`**

State machine producing position signals:

| Condition | Position | Trade |
|-----------|----------|-------|
| z > +entry | −1 (short basis) | Sell bond, buy futures |
| z < −entry | +1 (long basis) | Buy bond, sell futures |
| \|z\| < exit | 0 (flat) | Close position |

*Why a state machine rather than a simple threshold rule:* positions must persist 
between entry and exit. A naive rule that recomputes position from the current 
z-score alone would flip in and out of positions on every minor fluctuation, 
generating enormous transaction costs.

*Why exit at ±0.5 and not 0:* two reasons. Transaction costs make waiting for 
perfect mean reversion wasteful — by ±0.5 roughly 80% of the convergence move is 
already captured. And market noise around the mean would cause repeated exit/
re-entry cycles if the exit threshold were too tight.

**`calculate_pnl(basis, signals, nominal, transaction_cost_bps)`**

$$P\&L_t = signal_{t-1} \times (basis_t - basis_{t-1}) \times \frac{nominal}{100} - costs$$

*The critical detail — `signals.shift(1)`:* the basis closing level on day $t$ 
isn't known until after the close. A signal derived from it can only be executed 
at the open of day $t+1$. Using the same-day signal would mean trading on 
information you couldn't have had — look-ahead bias, the most common fatal flaw 
in amateur backtests.

This is explicitly tested in `test_no_lookahead_bias()`, which verifies that the 
first day of a new position produces zero P&L.

*Why `nominal / 100`:* the basis is quoted in price points per 100 of face value. 
On a $1M position, one full point of basis equals $10,000.

*Transaction costs* are applied on position **changes**, computed as 
`signals.diff().abs()` — entering, exiting or reversing all incur a cost.

---

### `risk.py` — Performance and robustness

**`sharpe_ratio(pnl_daily, risk_free_rate)`**

$$Sharpe = \frac{E[P\&L] - R_f/252}{\sigma_{P\&L}} \times \sqrt{252}$$

*Why filter to days in position:* including flat days (P&L exactly zero) would 
artificially deflate the standard deviation and inflate the Sharpe ratio. The 
metric should describe the risk/return profile of the trade, not of sitting in cash.

**`max_drawdown(pnl_cumulative)`**

Largest peak-to-trough decline. Computed as the minimum of 
`pnl_cumulative - pnl_cumulative.cummax()`.

The most intuitive risk metric for a trader — it answers "what's the worst 
unrealized loss I'd have sat through?"

**`calmar_ratio(pnl_daily, pnl_cumulative)`**

Annualized return divided by absolute maximum drawdown. Complements Sharpe by 
focusing on tail risk rather than volatility.

**`win_rate(pnl_daily)`**

Fraction of profitable days among days in position. A mean-reversion strategy 
typically shows a high win rate with occasional large losses — the inverse profile 
of a trend-following strategy.

**`performance_summary(...)`**

Aggregates all metrics plus trade count and days in position into a single 
dictionary. Convenience wrapper used by both notebooks and the dashboard.

**`sensitivity_analysis(basis, entry_thresholds, exit_thresholds, ...)`**

Grid search across entry/exit threshold combinations, returning full metrics for 
each. Combinations where exit ≥ entry are skipped as economically meaningless.

*Why this matters more than a single backtest:* a strategy that only works at one 
specific parameter combination is overfitted. Sensitivity analysis shows whether 
performance is robust across a parameter region or balanced on a knife edge.

**`stress_test(basis, signals, scenarios, nominal)`**

Applies an instantaneous shock to the basis on a single day and measures the P&L 
impact.

*Design decisions learned through debugging:*

- **Shock one day, not the whole series.** A constant shift applied to the entire 
  series leaves all daily *changes* identical — and since P&L depends on changes, 
  not levels, the result would be unchanged. The shock must create a sudden move.

- **Keep the original signals.** Recomputing signals from the shocked basis would 
  let the strategy "see" the shock coming and adapt. A real stress event hits 
  positions already in place.

- **Apply the shock on a day where the *previous* day's signal is non-zero.** 
  Because of `shift(1)`, a shock on the first day of a position produces zero P&L. 
  The function searches for a day where the position is already active.

*Results:* a +100bp basis shock costs $10,000 on a $1M short-basis position and 
gains the same on a long-basis position. The symmetry confirms the P&L logic is 
internally consistent.

---

## Data Sources and the SOFR Gap

| Series | Source | Coverage | Role |
|--------|--------|----------|------|
| DGS10 | FRED | 2016–2024 | 10Y Treasury constant maturity yield — drives bond pricing |
| SOFR | FRED | Apr 2018–2024 | Secured overnight financing rate — repo benchmark |
| EFFR | FRED | 2016–2024 | Effective Fed Funds rate — pre-2018 financing proxy |

**The SOFR problem and how it's handled**

SOFR did not exist before April 2018 — the New York Fed created it to replace 
LIBOR after the 2012 manipulation scandal. This isn't missing data, it's a genuine 
historical boundary.

Rather than truncating the sample to 2018+ and losing two years of observations, 
the project builds a composite `financing_rate` series: EFFR before April 2018, 
SOFR after. This is standard practitioner practice for constructing long financing 
series. Both source columns are retained in the DataFrame so the transition can be 
inspected and explained.

```python
df["financing_rate"] = df["sofr"].fillna(df["effr"])
```

---

## Data Limitations

These are stated explicitly because a quantitative project that hides its 
assumptions is not credible.

**Bond and futures prices are simulated, not observed.** Free data sources provide 
Treasury yields and financing rates, but not synchronized historical price series 
for a specific futures contract and its deliverable bonds. The project computes 
bond prices from DGS10 yields and futures prices via Hull — mathematically 
consistent, but not market prices.

**Consequence for the basis:** because both the bond price and the futures price 
derive from the same yield input through related formulas, the simulated basis has 
lower variance than a real market basis. Real basis moves reflect supply/demand 
imbalances in the cash and futures markets that this model cannot capture.

**The deliverable basket is synthetic.** Six hypothetical bonds with coupons from 
2% to 11% and maturities from 6.5 to 11 years, with conversion factors computed 
from the CME formula. Real CME deliverable baskets would produce different switch 
points.

**CTD switches are modeled, not observed.** The iterative recalibration produces 
switches at theoretically sensible rate levels, but the instantaneous adjustment 
creates discontinuities that real markets would smooth out.

**Backtest results are methodological demonstrations.** The P&L figures show that 
the framework works end to end — they are not estimates of real trading performance.

---

## Validation Tests

Run with `pytest tests/ -v`. The suite covers:

| Test | What it validates |
|------|-------------------|
| `test_at_par` | Bond priced at par when coupon = yield |
| `test_price_increases_when_yield_falls` | Inverse price/yield relationship |
| `test_accrued_interest_zero_at_coupon_date` | AI resets on coupon payment |
| `test_dv01_positive` | DV01 sign convention |
| `test_calcul_cf_hull_example` | CF matches textbook (1.4623) |
| `test_calcul_cf_at_par` | 6% coupon bond has CF ≈ 1 |
| `test_futures_price_hull_example` | Hull pricing matches textbook (71.79) |
| `test_gross_basis_formula` | Basis formula correctness |
| `test_carry_positive_when_coupon_exceeds_financing` | Carry sign logic |
| `test_ctd_is_unique` | Exactly one CTD identified |
| `test_ctd_same_by_cost_and_irr` | Delivery-cost and IRR criteria agree |
| `test_no_lookahead_bias` | P&L uses previous day's signal |
| `test_transaction_costs_reduce_pnl` | Costs reduce net P&L |
| `test_max_drawdown_is_negative` | Drawdown sign convention |

The Hull reproduction tests are the most important — they prove the pricing engine 
produces results matching an established reference, not just internally consistent 
numbers.

---

## Results

Strategy with ±3 z-score entry threshold, ±0.5 exit, $1M nominal, 2bp costs:

| Metric | ±2 threshold | ±3 threshold |
|--------|--------------|--------------|
| Total P&L | −$26,846 | +$5,692 |
| Sharpe ratio | −0.23 | +0.05 |
| Max drawdown | −$58,138 | −$18,894 |
| Days in position | 511 | 288 |

**Interpretation:** the tighter ±2 threshold trades too frequently, entering on 
deviations that aren't statistically meaningful. Transaction costs and noise 
consume the P&L. The ±3 threshold is more selective — fewer trades, but each one 
based on a genuine statistical anomaly with a higher probability of mean reversion.

This is not a claim that ±3 is universally optimal. On different data or different 
instruments the optimal threshold would differ — which is exactly why the project 
includes systematic sensitivity analysis rather than reporting a single 
hand-tuned result.

**DV01 hedge ratio:** covering a $1M cash position in OBL_A requires approximately 
8 ZN futures contracts. The bond's DV01 is $0.0836 per 100 face; the futures DV01 
is $0.1062 (higher because OBL_A's conversion factor is below 1, which amplifies 
sensitivity when dividing).

---

## Installation

```bash
git clone https://github.com/chrisyoann24-coder/Treasury-basis-trading.git
cd Treasury-basis-trading

python -m venv .venv
.\.venv\Scripts\Activate.ps1          # Windows PowerShell
# source .venv/bin/activate           # macOS/Linux

pip install -r requirements.txt
pip install -e .
```

The `pip install -e .` step installs the project as an editable package, which 
lets `tests/` and `app.py` import from `src/treasury_basis/` without path 
manipulation.

---

## Usage

**Run notebooks in order** — notebook 01 downloads and caches the FRED data that 
the others depend on:

```bash
jupyter notebook notebooks/01_data_exploration.ipynb
```

**Launch the dashboard:**

```bash
streamlit run app.py
```

The dashboard exposes entry/exit thresholds, z-score window, nominal and 
transaction costs as live parameters — the strategy recomputes on every change.

**Run the test suite:**

```bash
pytest tests/ -v
```

---

## References

- Hull, J.C. (2018). *Options, Futures, and Other Derivatives*, 10th ed. — futures 
  pricing methodology, conversion factor mechanics
- CME Group. *U.S. Treasury Futures Conversion Factor Lookup Tables* — contract 
  specifications and CF reference rate
- Federal Reserve Bank of St. Louis. *FRED Economic Data* — DGS10, SOFR, EFFR series
- Federal Reserve Bank of New York. *SOFR Publication* — financing benchmark 
  methodology and history

