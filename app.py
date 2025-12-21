import streamlit as st
from hypotheses.ten_am_reversal import load_5m, run_10am_reversal

st.title("Market Hypothesis Testing")

df = load_5m()
results = run_10am_reversal(df)

st.subheader("10AM Reversal Hypothesis")
st.write(results)

