# app.py — Complete Sentiment Analysis Web App
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from textblob import TextBlob
from datetime import datetime

# ── Page Setup ──────────────────────────────
st.set_page_config(
    page_title = "Sentiment Analysis",
    page_icon  = "🧠",
    layout     = "wide"
)

# ── Title ───────────────────────────────────
st.title("🧠 Social Media Sentiment Analysis")
st.markdown("Analyze the sentiment of any text instantly — **Positive, Negative or Neutral**")
st.divider()

# ── Load Model ──────────────────────────────
@st.cache_resource
def load_model():
    return SentimentIntensityAnalyzer()

analyzer = load_model()

# ── Analyze Function ────────────────────────
def analyze(text):
    scores   = analyzer.polarity_scores(text)
    compound = scores["compound"]
    tb       = TextBlob(text).sentiment.polarity
    combined = (compound * 0.6) + (tb * 0.4)

    if combined >= 0.05:    sentiment = "POSITIVE"
    elif combined <= -0.05: sentiment = "NEGATIVE"
    else:                   sentiment = "NEUTRAL"

    return sentiment, combined, scores, tb

# ════════════════════════════════════════════
# TAB 1 — Single Text
# TAB 2 — Multiple Texts
# TAB 3 — About
# ════════════════════════════════════════════
tab1, tab2, tab3 = st.tabs([
    "📝 Analyze Single Text",
    "📋 Analyze Multiple Texts",
    "ℹ️ About"
])

# ── TAB 1 ────────────────────────────────────
with tab1:
    st.subheader("Type or paste any text below")

    user_text = st.text_area(
        "Enter your text here:",
        placeholder = "Example: I love this project so much!",
        height      = 150,
    )

    platform = st.selectbox(
        "Select Platform:",
        ["Twitter", "Reddit", "YouTube", "News", "Other"]
    )

    if st.button("🔍 Analyze Sentiment", type="primary"):
        if user_text.strip():
            sentiment, combined, scores, tb = analyze(user_text)

            # Result box
            if sentiment == "POSITIVE":
                st.success(f"😊 Result: **{sentiment}**")
            elif sentiment == "NEGATIVE":
                st.error(f"😠 Result: **{sentiment}**")
            else:
                st.warning(f"😐 Result: **{sentiment}**")

            # Score columns
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Overall Score",  f"{combined:+.3f}")
            col2.metric("Positive %",     f"{scores['pos']*100:.1f}%")
            col3.metric("Negative %",     f"{scores['neg']*100:.1f}%")
            col4.metric("Neutral %",      f"{scores['neu']*100:.1f}%")

            st.divider()

            # Pie chart
            fig, ax = plt.subplots(figsize=(4, 4))
            labels  = ["Positive", "Negative", "Neutral"]
            values  = [scores["pos"], scores["neg"], scores["neu"]]
            colors  = ["#28a745", "#dc3545", "#ffc107"]
            ax.pie(values, labels=labels, colors=colors,
                   autopct="%1.1f%%", startangle=90)
            ax.set_title("Sentiment Breakdown")
            st.pyplot(fig)

        else:
            st.warning("⚠️ Please enter some text first!")

# ── TAB 2 ────────────────────────────────────
with tab2:
    st.subheader("Analyze multiple texts at once")
    st.markdown("Enter **one text per line** in the box below:")

    bulk_text = st.text_area(
        "Enter multiple texts (one per line):",
        placeholder = "I love this!\nThis is terrible.\nToday was okay.",
        height      = 200,
    )

    if st.button("🔍 Analyze All", type="primary"):
        lines = [l.strip() for l in bulk_text.strip().split("\n") if l.strip()]

        if lines:
            results = []
            for line in lines:
                sentiment, combined, scores, tb = analyze(line)
                results.append({
                    "Text":       line[:60] + ("..." if len(line) > 60 else ""),
                    "Sentiment":  sentiment,
                    "Score":      round(combined, 3),
                    "Positive %": f"{scores['pos']*100:.1f}%",
                    "Negative %": f"{scores['neg']*100:.1f}%",
                    "Neutral %":  f"{scores['neu']*100:.1f}%",
                })

            df = pd.DataFrame(results)

            # Color the sentiment column
            def color_row(val):
                if val == "POSITIVE": return "background-color: #d4edda"
                if val == "NEGATIVE": return "background-color: #f8d7da"
                return "background-color: #fff3cd"

            st.dataframe(
                df.style.applymap(color_row, subset=["Sentiment"]),
                use_container_width=True,
                hide_index=True,
            )

            # Summary
            st.divider()
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total",    len(results))
            col2.metric("😊 Positive", sum(1 for r in results if r["Sentiment"] == "POSITIVE"))
            col3.metric("😠 Negative", sum(1 for r in results if r["Sentiment"] == "NEGATIVE"))
            col4.metric("😐 Neutral",  sum(1 for r in results if r["Sentiment"] == "NEUTRAL"))

            # Download CSV
            csv = df.to_csv(index=False)
            st.download_button(
                label     = "⬇️ Download Results as CSV",
                data      = csv,
                file_name = "sentiment_results.csv",
                mime      = "text/csv",
            )
        else:
            st.warning("⚠️ Please enter at least one line of text!")

# ── TAB 3 ────────────────────────────────────
with tab3:
    st.subheader("About This Project")
    st.markdown("""
    ### 🧠 Social Media Sentiment Analysis

    This app uses **Natural Language Processing (NLP)** to analyze
    the emotional tone of text from social media platforms.

    ---

    ### 🤖 Models Used

    | Model | Type | Purpose |
    |-------|------|---------|
    | **VADER** | Rule-based | Best for social media short text |
    | **TextBlob** | Linguistic | Polarity and subjectivity |
    | **Ensemble** | Combined | Final weighted result |

    ---

    ### 📊 Sentiment Classes

    - 😊 **Positive** — Happy, excited, satisfied
    - 😠 **Negative** — Angry, sad, disappointed
    - 😐 **Neutral**  — No strong emotion

    ---

    ### 🛠️ Built With
    - Python 3.11
    - Streamlit
    - VADER Sentiment
    - TextBlob
    - Pandas
    - Matplotlib

    ---
    Made with ❤️ for learning purposes
    """)