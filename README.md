# 🧪 OHLC Hypothesis Testing — 10AM Breakout Study

This project is a **data-driven investigation** into the well-known “10AM reversal / breakout” behavior on NQ (Nasdaq futures), using 5-minute OHLC data.

The goal is **not** to present a polished trading system upfront, but to demonstrate:
- Hypothesis formulation
- Statistical testing
- Strategy rejection
- Iterative refinement
- Evidence-based conclusions

This mirrors how real research and strategy development actually work.

---

## 📌 Project Overview

**Market:** NQ (Nasdaq Futures)  
**Timeframe:** 5-minute  
**Session Focus:** 6:50–7:10 AM (PT) range → post-10:00 AM behavior  
**Data Type:** OHLC (no indicators required)

The project explores whether early-session consolidation followed by a breakout around 10AM can produce a **repeatable edge**.

---

## 🧪 Hypotheses Tested

### 1. Baseline Hypothesis  
> A clean breakout above/below the morning range around 10AM produces a profitable continuation trade.

This hypothesis was tested using:
- Entry at breakout
- Stop at range extreme
- Fixed R:R targets (1R, 1.5R, 2R)

**Result:**  
❌ *Rejected* — performance hovered near breakeven with poor expectancy.

This outcome triggered deeper investigation.

---

## 🔍 Key Diagnostic Insight

Instead of forcing filters, the next step was to ask:

> *What actually happens between breakout and target?*

A conditional probability test was run:

- How often does price retrace **50% / 75% of the breakout candle**
- **Before** reaching +1R?

### Result (simplified):
- **50% retrace occurs ~70% of the time**
- **75% retrace occurs ~55–60% of the time**

This was the turning point.

---

## 🛠️ Strategy Development (Rejected → Refined)

### ❌ Strategy A — Breakout Entry
- Entry: Breakout candle close
- Stop: Opposite breakout extreme
- Targets: 1R / 1.5R / 2R

**KPIs (approximate):**
- Win rate: ~45–47%
- Expectancy: ~0R
- Profit factor: ~1.0

**Conclusion:**  
🔴 *Not viable as a standalone strategy.*

---

## ✅ Final Strategy — 50% Retrace Entry

### Core Logic
Instead of chasing the breakout:

- **Wait for a 50% retracement of the breakout candle**
- Enter only if price pulls back
- Risk is defined precisely at the breakout extreme

This aligns entries with **observed market behavior**, not assumptions.

### Rules
- Entry: 50% retrace of breakout candle
- Stop: Breakout candle extreme
- Targets tested: 1R / 1.5R / 2R

---

## 📊 Final Strategy Results

**Target: 1.0R**
- Trades: 238  
- Win rate: **62.03%**  
- Profit factor: **1.63**  
- Expectancy: **+0.239R**

**Target: 1.5R**
- Win rate: 47.86%  
- Profit factor: 1.38  
- Expectancy: +0.193R  

**Target: 2.0R**
- Win rate: 39.57%  
- Profit factor: 1.31  
- Expectancy: +0.181R  

✔️ Edge is present  
✔️ Stable across targets  
✔️ Risk is well-defined  

---

## 📈 Performance Visualization

The final strategy is evaluated using three key performance charts:

1. **Cumulative R (Equity Curve)**  
   Shows long-term edge and sequence robustness.

2. **Drawdown Curve**  
   Quantifies psychological and capital stress.

3. **Rolling Expectancy (20 trades)**  
   Verifies stability vs regime dependence.

All charts are generated directly from backtest output.

---

## 🧠 Key Takeaways

- Most strategies fail not because markets are random, but because **entry timing is misaligned**
- Breakouts often work — **just not immediately**
- Studying *what happens before success* is often more valuable than optimizing exits
- Rejecting ideas is progress, not failure

---

## 📁 Project Structure

<details>
<summary>Click to expand</summary>

<pre><code>.
├── app.py                          # Streamlit research dashboard
├── hypotheses/                     # Individual hypothesis tests
│   ├── ten_am_reversal.py
│   ├── close_vs_wick.py
│   ├── stairstep_acceptance.py
│   ├── retrace_before_1R.py
│   └── strategy_backtest.py        # Final strategy backtest logic
├── data/
│   └── processed/                  # Cleaned OHLC datasets
│       ├── nq_5m_clean.csv
│       └── nq_1h_clean.csv
├── assets/                         # Charts & visual examples
│   └── *.png
└── README.md
</code></pre>

</details>


---

## 🚀 Next Steps (Optional Extensions)

- Monte Carlo sequencing analysis (separate project recommended)
- Regime tagging (trend vs range)
- Time-of-day sensitivity analysis
- Cross-market validation

---

## ⚠️ Disclaimer

This project is for **research and educational purposes only**.  
It does not constitute financial advice.

---

*Built to demonstrate process, not hype.*


---

## 🚀 Next Steps (Optional Extensions)

- Monte Carlo sequencing analysis (separate project recommended)
- Regime tagging (trend vs range)
- Time-of-day sensitivity analysis
- Cross-market validation

---

## ⚠️ Disclaimer

This project is for **research and educational purposes only**.  
It does not constitute financial advice.

---

*Built to demonstrate process, not hype.*
