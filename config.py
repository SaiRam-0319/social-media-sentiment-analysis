# =============================================================================
#  FREE config.py — No Payment Required
#  Social Media Sentiment Analysis — Free Version
# =============================================================================

# ─────────────────────────────────────────────
#  REDDIT API  (100% Free — No Credit Card)
#  Get keys at: https://www.reddit.com/prefs/apps
#  Takes only 2 minutes to get!
# ─────────────────────────────────────────────
REDDIT_CLIENT_ID     = "YOUR_REDDIT_CLIENT_ID"
REDDIT_CLIENT_SECRET = "YOUR_REDDIT_CLIENT_SECRET"
REDDIT_USER_AGENT    = "smsa_free_bot/1.0"
REDDIT_USERNAME      = "YOUR_REDDIT_USERNAME"
REDDIT_PASSWORD      = "YOUR_REDDIT_PASSWORD"

# ─────────────────────────────────────────────
#  NEWS API  (100% Free for Students)
#  Get free key at: https://newsapi.org/
#  Sign up with email → get key instantly!
# ─────────────────────────────────────────────
NEWS_API_KEY = "YOUR_NEWSAPI_KEY"

# ─────────────────────────────────────────────
#  TWITTER  — No API Key Needed!
#  Uses free ntscraper library (web scraping)
# ─────────────────────────────────────────────
# No keys required for Twitter scraping!

# ─────────────────────────────────────────────
#  WHAT TO SEARCH FOR
# ─────────────────────────────────────────────
SEARCH_KEYWORDS   = ["python", "AI", "technology"]
REDDIT_SUBREDDITS = ["technology", "worldnews", "science"]
MAX_REDDIT_POSTS  = 50
MAX_TWEETS        = 30
MAX_NEWS_ARTICLES = 50

# ─────────────────────────────────────────────
#  MODEL SETTINGS
# ─────────────────────────────────────────────
# "vader"    → fastest, no download needed ✅
# "textblob" → lightweight
# "ensemble" → most accurate (needs internet for first download)
SENTIMENT_MODEL = "vader"

# ─────────────────────────────────────────────
#  OUTPUT
# ─────────────────────────────────────────────
import os
os.makedirs("output", exist_ok=True)
SQLITE_DB_PATH  = "output/sentiment_results.db"
CSV_OUTPUT_PATH = "output/sentiment_results.csv"
LOG_FILE        = "output/smsa.log"
