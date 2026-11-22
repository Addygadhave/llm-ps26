"""Streamlit UI for the Math Word Problem Solver (PS 26).  Run: streamlit run app.py"""
import streamlit as st
from dotenv import load_dotenv

from solver import PROVIDERS, solve

load_dotenv()

st.set_page_config(page_title="Math Word Problem Solver", page_icon="🧮", layout="centered")
st.title("🧮 Math Word Problem Solver")
st.caption("Type a word problem. The LLM solves it step by step, and Python (sympy) double-checks the arithmetic.")

EXAMPLES = {
    "— choose an example —": "",
    "Shopping": "Riya bought 3 notebooks at Rs. 45 each and 2 pens at Rs. 12 each. She paid with a Rs. 200 note. How much change did she get?",
    "Speed": "A train travels 360 km in 4 hours. At the same speed, how long will it take to travel 540 km?",
    "Percentage": "A shirt costs Rs. 800. The shop gives a 15% discount and then adds 5% GST on the discounted price. What is the final price?",
    "Age": "Arjun is 5 years older than his sister. The sum of their ages is 27. How old is Arjun?",
    "Work": "A tap fills a tank in 6 hours and another tap fills it in 3 hours. How long will both taps take together?",
}

with st.sidebar:
    st.header("Settings")
    provider = st.selectbox("LLM provider", list(PROVIDERS))
    model = st.text_input("Model", value=PROVIDERS[provider]["model"])
    api_key = st.text_input("API key (optional if set in .env)", type="password")
    verify_on = st.checkbox("Verify arithmetic with sympy", value=True)

choice = st.selectbox("Try an example", list(EXAMPLES))
problem = st.text_area("Word problem", value=EXAMPLES[choice], height=140,
                       placeholder="e.g. A car travels 150 km in 3 hours. What is its average speed?")

if st.button("Solve step by step", type="primary"):
    if not problem.strip():
        st.warning("Please enter a word problem first.")
    else:
        with st.spinner("Solving..."):
            try:
                res = solve(problem, provider=provider, model=model, api_key=api_key or None)
            except Exception as exc:  # noqa: BLE001
                st.error(f"Could not get an answer: {exc}")
                st.stop()

        st.subheader("Solution")
        if res.steps:
            for i, step in enumerate(res.steps, 1):
                st.markdown(f"**Step {i}.** {step}")
        else:
            st.write(res.raw)
        st.success(f"**Final answer:** {res.final_answer}")

        if verify_on:
            if res.verified is True:
                st.info(f"✅ Verified. {res.verify_note}")
            elif res.verified is False:
                st.error(f"⚠️ {res.verify_note}")
            else:
                st.warning(res.verify_note)
            if res.check_expression:
                st.code(f"CHECK: {res.check_expression}")

        with st.expander("Raw LLM output"):
            st.text(res.raw)
