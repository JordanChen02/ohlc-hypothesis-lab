import streamlit as st
import pandas as pd

from hypotheses.ten_am_reversal import load_5m
from hypotheses.am_macro_range import run_am_macro_range

# -------------------------------------------------
# Page configuration
# -------------------------------------------------
st.set_page_config(
    page_title="Market Hypothesis Research",
    layout="centered",
)

# -------------------------------------------------
# Header
# -------------------------------------------------
st.title("Market Hypothesis Research")
st.caption(
    "Testing structured intraday market behavior using historical NQ price action."
)

st.divider()

# -------------------------------------------------
# Load data & run hypothesis
# -------------------------------------------------
df = load_5m()
results = run_am_macro_range(df)

meta = results["meta"]

# -------------------------------------------------
# Hypothesis description
# -------------------------------------------------
st.subheader("10AM Reversal Hypothesis")

st.markdown(
    """
**Hypothesis**  
The price range formed between **9:50–10:10 EST** acts as a short-term macro range.
After 10:10, whichever side of this range breaks first,
the opposing side is unlikely to be revisited before late morning.
"""
)

st.markdown(
    f"""
**Test Parameters**
- Range window: `{meta['range_window']}`
- Evaluation cutoffs: `{", ".join(meta['evaluation_cutoffs'])}`
"""
)

st.divider()

# -------------------------------------------------
# Results table
# -------------------------------------------------
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
            "Opposite side NOT revisited by 11:00": f"{s['held_11']*100:.2f}%",
            "Opposite side NOT revisited by 12:00": f"{s['held_12']*100:.2f}%",
        }
    )

table = pd.DataFrame(rows)

st.markdown("### Results")
st.dataframe(
    table,
    use_container_width=True,
    hide_index=True,
)

# -------------------------------------------------
# Visual examples
# -------------------------------------------------
st.markdown("### Example Chart Patterns")

st.markdown("**Break ABOVE range first**")
st.image(
    "assets/am_range_break_high.png",
    caption="Price breaks above the 9:50–10:10 range and does not revisit the lower boundary.",
    use_container_width=True,
)

st.markdown("---")

st.markdown("**Break BELOW range first**")
st.image(
    "assets/am_range_break_low.png",
    caption="Price breaks below the 9:50–10:10 range and does not revisit the upper boundary.",
    use_container_width=True,
)

# -------------------------------------------------
# Plain-English conclusion
# -------------------------------------------------
hi = results["break_high_first"]
lo = results["break_low_first"]

st.markdown("### Conclusion")

st.success(
    f"""
When price breaks **above** the 9:50–10:10 range first,
the lower boundary of that range is not revisited
until **11:00** in **{hi['held_11']*100:.2f}%** of cases,
and until **12:00** in **{hi['held_12']*100:.2f}%** of cases.

When price breaks **below** the range first,
the upper boundary is not revisited
until **11:00** in **{lo['held_11']*100:.2f}%** of cases,
and until **12:00** in **{lo['held_12']*100:.2f}%** of cases.
"""
)

# -------------------------------------------------
# Methodology & caveats
# -------------------------------------------------
with st.expander("Methodology & Caveats"):
    dbg = results["debug"]
    st.markdown(
        f"""
- Days without a complete 9:50–10:10 range: **{dbg['no_range']}**
- Days without a post-range breakout: **{dbg['no_break']}**
- Ambiguous breakouts (both sides broken on same bar): **{dbg['ambiguous']}**

**Notes**
- This test is descriptive, not predictive.
- Results are conditional on a clean post-range breakout.
- The goal is to measure *directional commitment*, not signal entries.
"""
    )
