# Social Media Sentiment Analysis

Streamlit app for classifying social media text as positive, negative, or
neutral with VADER and TextBlob.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Analyze Text

- Paste one post per line in the bulk analysis tab.
- Upload a CSV with one of these text columns: `text`, `tweet`, `full_text`,
  `tweet_text`, `content`, `body`, or `message`.
- Download the scored CSV after analysis.

## Optional TweetClaw Exports

TweetClaw exports can be uploaded directly when the export has a text-like
column such as `text` or `tweet`. Keep TweetClaw as a reviewed collection
source, then use this app for local sentiment scoring and visualization.

For JSON or JSONL exports, convert the selected post text into CSV first:

```csv
id,tweet
1,This project launch is getting strong community feedback.
2,The live demo needs clearer setup notes.
```

Then upload the file in the bulk analysis tab.
