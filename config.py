# =============================================================================
#  config.py — Central Configuration & API Keys
#  Social Media Sentiment Analysis System
#  Replace all placeholder values with your real credentials.
# =============================================================================

# ─────────────────────────────────────────────
#  TWITTER / X  API v2
#  Get keys at: https://developer.twitter.com/
# ─────────────────────────────────────────────
TWITTER_API_KEY             = "YOUR_TWITTER_API_KEY"
TWITTER_API_SECRET          = "YOUR_TWITTER_API_SECRET"
TWITTER_ACCESS_TOKEN        = "YOUR_TWITTER_ACCESS_TOKEN"
TWITTER_ACCESS_TOKEN_SECRET = "YOUR_TWITTER_ACCESS_TOKEN_SECRET"
TWITTER_BEARER_TOKEN        = "YOUR_TWITTER_BEARER_TOKEN"

# ─────────────────────────────────────────────
#  REDDIT  API
#  Get keys at: https://www.reddit.com/prefs/apps
# ─────────────────────────────────────────────
REDDIT_CLIENT_ID     = "YOUR_REDDIT_CLIENT_ID"
REDDIT_CLIENT_SECRET = "YOUR_REDDIT_CLIENT_SECRET"
REDDIT_USER_AGENT    = "smsa_bot/1.0 by YourUsername"
REDDIT_USERNAME      = "YOUR_REDDIT_USERNAME"
REDDIT_PASSWORD      = "YOUR_REDDIT_PASSWORD"

# ─────────────────────────────────────────────
#  YOUTUBE  DATA API v3
#  Get key at: https://console.cloud.google.com/
# ─────────────────────────────────────────────
YOUTUBE_API_KEY = "YOUR_YOUTUBE_DATA_API_KEY"

# ─────────────────────────────────────────────
#  COLLECTION SETTINGS
# ─────────────────────────────────────────────
SEARCH_KEYWORDS = ["python", "AI", "machine learning"]   # Topics to track
MAX_TWEETS      = 100          # Max tweets per keyword per run
MAX_REDDIT_POSTS = 50          # Max Reddit posts per subreddit
MAX_YOUTUBE_COMMENTS = 50     # Max YouTube comments per video
REDDIT_SUBREDDITS = ["technology", "worldnews", "science"]  # Subreddits to monitor

# ─────────────────────────────────────────────
#  MODEL SETTINGS
# ─────────────────────────────────────────────
# Options: "vader", "textblob", "transformer", "ensemble"
SENTIMENT_MODEL = "ensemble"

# HuggingFace transformer model (used when SENTIMENT_MODEL includes transformer)
# Good options:
#   "cardiffnlp/twitter-roberta-base-sentiment-latest"  ← best for Twitter
#   "distilbert-base-uncased-finetuned-sst-2-english"   ← fast general purpose
#   "nlptown/bert-base-multilingual-uncased-sentiment"  ← multilingual
TRANSFORMER_MODEL_NAME = "cardiffnlp/twitter-roberta-base-sentiment-latest"

# Ensemble weights (must sum to 1.0)
ENSEMBLE_WEIGHTS = {
    "vader":       0.25,
    "textblob":    0.15,
    "transformer": 0.60,
}

# ─────────────────────────────────────────────
#  STORAGE SETTINGS
# ─────────────────────────────────────────────
SQLITE_DB_PATH = "output/sentiment_results.db"
CSV_OUTPUT_PATH = "output/sentiment_results.csv"

# ─────────────────────────────────────────────
#  FLASK API SETTINGS
# ─────────────────────────────────────────────
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000
FLASK_DEBUG = True
API_SECRET_KEY = "change-this-to-a-random-secret"

# ─────────────────────────────────────────────
#  LOGGING
# ─────────────────────────────────────────────
LOG_LEVEL = "INFO"   # DEBUG | INFO | WARNING | ERROR
LOG_FILE  = "output/smsa.log"
