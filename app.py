import streamlit as st
import pandas as pd

from hypotheses.ten_am_reversal import load_5m
from hypotheses.am_macro_range import run_am_macro_range
from hypotheses.close_vs_wick import run_close_vs_wick_test
from hypotheses.stairstep_acceptance import run_stairstep


# -------------------------------------------------
# Page config
# -------------------------------------------------
st.set_page_config(
    page_title="Market Hypothesis Research",
    layout="wide",
)

# -------------------------------------------------
# 15 / 70 / 15 layout wrapper
# -------------------------------------------------
left, center, right = st.columns([2, 6, 2])

def fmt_pct(x: float) -> str:
    """
    Accepts either:
      - decimal rate (0.8264) OR
      - percent value (82.64)

    Returns "82.64%".
    """
    if x is None:
        return "—"
    try:
        x = float(x)
    except Exception:
        return "—"

    # If it's already a percent (e.g., 82.64), convert to decimal
    if x > 1.5:
        x = x / 100.0

    return f"{x * 100:.2f}%"


with center:
    st.title("Market Hypothesis Research")
    st.caption("Structured hypothesis testing on intraday NQ price action (5-minute bars).")
    st.divider()

    # -------------------------------------------------
    # Load data once
    # -------------------------------------------------
    df = load_5m()

    # -------------------------------------------------
    # Tabs (INTRO first)
    # -------------------------------------------------
    tabs = st.tabs(
        [
            "Overview",
            "10AM Reversal",
            "Close vs Wick",
            "Stairstep Acceptance",
            "Strategy",
        ]
    )

    # =================================================
    # TAB 0 — OVERVIEW
    # =================================================
    with tabs[0]:
        st.header("Overview")

        st.markdown(
            """
This project demonstrates a **data-analytic workflow** applied to market behavior:

- Define a precise hypothesis
- Convert it into testable rules
- Run it on historical data
- Report results with clear metrics and sample sizes
- Summarize implications (and limitations) in plain language

Even if you don’t trade, you can read this as **time-series event analysis**.
"""
        )

        st.subheader("Data")
        st.markdown(
            """
- Instrument: **NQ (Nasdaq futures)**  
- Timeframe: **5-minute candles**  
- Session context: Tests focus on the **morning window** where intraday structure often forms.
"""
        )

        st.subheader("How to read the results")
        st.markdown(
            """
- **Samples** = number of days where the setup occurred  
- “Held until 11:00 / 12:00” = frequency that an opposing boundary was **not revisited** by that time  
- These are **descriptive statistics**, not guarantees or financial advice.
"""
        )

        st.subheader("What’s inside")
        st.markdown(
            """
1. **10AM Reversal**: The 9:50–10:10 range acts as a short-term macro range after it breaks.  
2. **Close vs Wick**: Close-confirmed breakouts are more reliable than wick-only breaches.  
3. **Stairstep Acceptance**: After a close-confirmed breakout, the next candle often confirms acceptance.  
4. **Strategy**: A synthesis tab showing how these findings could inform a rules-based model.
"""
        )

        st.info(
            "Goal: show structured hypothesis research + clean presentation — "
            "the same analytical approach used in product analytics, A/B tests, or time-series monitoring."
        )

    # =================================================
    # TAB 1 — 10AM REVERSAL
    # =================================================
    with tabs[1]:
        results = run_am_macro_range(df)
        meta = results["meta"]

        st.header("10AM Reversal Hypothesis")

        st.subheader("Hypothesis")
        st.markdown(
            """
The price range formed between **9:50–10:10 EST** acts as a short-term macro range.
After 10:10, whichever side of this range breaks first,
the opposing side is unlikely to be revisited before late morning.
"""
        )

        st.subheader("Test Parameters")
        st.markdown(
            f"""
- **Range window:** `{meta['range_window']}`
- **Evaluation cutoffs:** `{", ".join(meta['evaluation_cutoffs'])}`
"""
        )

        rows = []
        for side_key, label in [
            ("break_high_first", "Break ABOVE range first"),
            ("break_low_first", "Break BELOW range first"),
        ]:
            s = results[side_key]
            rows.append(
                {
                    "Scenario": label,
                    "Samples": s["samples"],
                    "Opposite side NOT revisited by 11:00": fmt_pct(s["held_11"]),
                    "Opposite side NOT revisited by 12:00": fmt_pct(s["held_12"]),
                }
            )

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )

        st.subheader("Example Scenarios")
        col1, col2 = st.columns(2)

        with col1:
            st.image(
                "assets/am_range_break_high.png",
                caption="Break above range → low protected",
                use_container_width=True,
            )
        with col2:
            st.image(
                "assets/am_range_break_low.png",
                caption="Break below range → high protected",
                use_container_width=True,
            )

        # Statistical conclusion using numbers directly
        hi = results["break_high_first"]
        lo = results["break_low_first"]

        st.success(
            f"**Conclusion (statistical):** When price breaks **above** the 9:50–10:10 range first "
            f"(n={hi['samples']}), the opposing boundary is not revisited by 11:00 in **{fmt_pct(hi['held_11'])}** "
            f"and by 12:00 in **{fmt_pct(hi['held_12'])}**. "
            f"When price breaks **below** first (n={lo['samples']}), the opposing boundary is not revisited by 11:00 in "
            f"**{fmt_pct(lo['held_11'])}** and by 12:00 in **{fmt_pct(lo['held_12'])}**."
        )

    # =================================================
    # TAB 2 — CLOSE VS WICK
    # =================================================
    with tabs[2]:
        st.header("Close vs Wick Breakouts")

        st.subheader("Question")
        st.markdown(
            "Are **close-confirmed breakouts** more reliable than **wick-only breaches**?"
        )

        cvw = run_close_vs_wick_test(df)

        wick = cvw["wick"]
        close = cvw["close"]

        table_rows = [
            {
                "Type": "Wick Breakouts",
                "Samples": wick["samples"],
                "Held until 11:00": fmt_pct(wick["held_11"]),
                "Held until 12:00": fmt_pct(wick["held_12"]),
            },
            {
                "Type": "Close Breakouts",
                "Samples": close["samples"],
                "Held until 11:00": fmt_pct(close["held_11"]),
                "Held until 12:00": fmt_pct(close["held_12"]),
            },
        ]

        st.dataframe(
            pd.DataFrame(table_rows),
            use_container_width=True,
            hide_index=True,
        )

        # Statistical conclusion with deltas
        # Convert to decimals for delta math
        def as_decimal(x: float) -> float:
            x = float(x)
            return (x / 100.0) if x > 1.5 else x

        d11 = (as_decimal(close["held_11"]) - as_decimal(wick["held_11"])) * 100
        d12 = (as_decimal(close["held_12"]) - as_decimal(wick["held_12"])) * 100

        st.info(
            f"**Conclusion (statistical):** Close-confirmed breakouts outperform wick-only breaches. "
            f"By 11:00, close-confirmed holds are higher by **{d11:.2f} pp** "
            f"({fmt_pct(close['held_11'])} vs {fmt_pct(wick['held_11'])}). "
            f"By 12:00, the advantage is **{d12:.2f} pp** "
            f"({fmt_pct(close['held_12'])} vs {fmt_pct(wick['held_12'])})."
        )

    # =================================================
    # TAB 3 — STAIRSTEP ACCEPTANCE
    # =================================================
    with tabs[3]:
        st.header("Stairstep Acceptance")

        st.markdown(
            """
**Definition**  
A *stairstep* exists only while each consecutive 5-minute candle preserves the prior structure.
Once a step fails, the sequence is invalidated (it does not “restart”).
"""
        )

        steps = 4
        ss = run_stairstep(df, steps=steps)

        def build_rows(side):
            base = ss[side]["base"]
            rows = []
            for n in range(1, steps + 1):
                rows.append(
                    {
                        "Step": f"Survives through Step {n}",
                        "Probability": fmt_pct(ss[side]["survivors"][n] / base if base else 0),
                    }
                )
            return rows, base

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**UP Breakouts**")
            rows_up, base_up = build_rows("up")
            st.dataframe(
                pd.DataFrame(rows_up),
                use_container_width=True,
                hide_index=True,
            )
            st.caption(f"Base samples: {base_up}")

        with col2:
            st.markdown("**DOWN Breakouts**")
            rows_dn, base_dn = build_rows("down")
            st.dataframe(
                pd.DataFrame(rows_dn),
                use_container_width=True,
                hide_index=True,
            )
            st.caption(f"Base samples: {base_dn}")

        # Step-1 emphasis conclusion with numbers
        if base_up and base_dn:
            step1_up = ss["up"]["survivors"][1] / base_up
            step1_dn = ss["down"]["survivors"][1] / base_dn

            st.warning(
                f"**Conclusion (statistical):** Step-1 acceptance is the strongest filter. "
                f"After an up breakout, Step-1 holds in **{fmt_pct(step1_up)}** (n={base_up}). "
                f"After a down breakout, Step-1 holds in **{fmt_pct(step1_dn)}** (n={base_dn}). "
                f"Survival probabilities decline materially after Step-1."
            )

    # =================================================
    # TAB 4 — STRATEGY
    # =================================================
    with tabs[4]:
        st.header("Strategy Synthesis")

        st.markdown(
            """
This is a **rules-based interpretation** of the research (not a full backtest):

**1) Structural Setup**
- Define the 9:50–10:10 range
- Wait for the first breakout after 10:10

**2) Quality Filter (Hypothesis 2)**
- Prefer **close-confirmed** breakouts over wick-only breaches

**3) Acceptance Filter (Hypothesis 3)**
- Require **Step-1 stairstep acceptance** (next candle does not invalidate)

**Rationale**
- The edge is front-loaded: the best information is **acceptance vs invalidation** immediately after breakout.
"""
        )

        st.success(
            "If you want, the next step is a dedicated Backtest tab that tests entries/exits built on these filters."
        )
