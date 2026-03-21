# =============================================================================
#  collectors/twitter_collector.py — Twitter/X Data Collection via Tweepy
# =============================================================================

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import tweepy
from utils.helpers import setup_logger, format_timestamp
import config

logger = setup_logger("TwitterCollector", config.LOG_FILE, config.LOG_LEVEL)


class TwitterCollector:
    """
    Collects tweets using Twitter API v2 via Tweepy.
    Handles authentication, search, and normalization into standard schema.
    """

    def __init__(self):
        self.client = None
        self._authenticate()

    def _authenticate(self):
        """Authenticate with Twitter API v2 using Bearer Token."""
        try:
            self.client = tweepy.Client(
                bearer_token=config.TWITTER_BEARER_TOKEN,
                consumer_key=config.TWITTER_API_KEY,
                consumer_secret=config.TWITTER_API_SECRET,
                access_token=config.TWITTER_ACCESS_TOKEN,
                access_token_secret=config.TWITTER_ACCESS_TOKEN_SECRET,
                wait_on_rate_limit=True,  # Auto-pause when rate limited
            )
            # Quick test — get own user details to verify credentials
            me = self.client.get_me()
            logger.info(f"Twitter authenticated as: @{me.data.username if me.data else 'unknown'}")
        except tweepy.TweepyException as e:
            logger.error(f"Twitter authentication failed: {e}")
            self.client = None

    def search_recent_tweets(self, query: str, max_results: int = None) -> list:
        """
        Search the most recent tweets matching `query`.
        Returns a list of normalized post dictionaries.
        """
        if not self.client:
            logger.warning("Twitter client not authenticated. Skipping collection.")
            return []

        max_results = max_results or config.MAX_TWEETS
        # API allows 10–100 per page; cap to valid range
        per_page = min(max(10, max_results), 100)

        logger.info(f"Searching Twitter for: '{query}' (max {max_results})")

        posts = []
        try:
            # Exclude retweets for cleaner data; add lang:en for English only
            full_query = f"{query} -is:retweet lang:en"

            response = self.client.search_recent_tweets(
                query=full_query,
                max_results=per_page,
                tweet_fields=[
                    "created_at", "text", "author_id",
                    "public_metrics", "entities", "lang"
                ],
                expansions=["author_id"],
                user_fields=["name", "username", "public_metrics"],
            )

            if not response.data:
                logger.info(f"No tweets found for: '{query}'")
                return []

            # Build a lookup map: author_id → user object
            users = {}
            if response.includes and "users" in response.includes:
                users = {u.id: u for u in response.includes["users"]}

            for tweet in response.data:
                author = users.get(tweet.author_id)
                metrics = tweet.public_metrics or {}
                entities = tweet.entities or {}

                hashtags = [h["tag"] for h in entities.get("hashtags", [])]
                mentions = [m["username"] for m in entities.get("mentions", [])]
                urls = [u["expanded_url"] for u in entities.get("urls", [])]

                posts.append({
                    "post_id":    f"tw_{tweet.id}",
                    "platform":   "Twitter",
                    "text":       tweet.text,
                    "author_id":  str(tweet.author_id),
                    "author_name": author.name if author else "Unknown",
                    "username":   f"@{author.username}" if author else "Unknown",
                    "timestamp":  format_timestamp(tweet.created_at),
                    "language":   tweet.lang or "en",
                    "hashtags":   hashtags,
                    "mentions":   mentions,
                    "urls":       urls,
                    "engagement": {
                        "likes":    metrics.get("like_count", 0),
                        "retweets": metrics.get("retweet_count", 0),
                        "replies":  metrics.get("reply_count", 0),
                        "quotes":   metrics.get("quote_count", 0),
                    },
                    "keyword":    query,
                    "raw":        tweet.text,
                })

            logger.info(f"Collected {len(posts)} tweets for '{query}'")
        except tweepy.TooManyRequests:
            logger.warning("Twitter rate limit hit. Try again later.")
        except tweepy.TweepyException as e:
            logger.error(f"Twitter search error: {e}")

        return posts

    def collect_all(self, keywords: list = None, max_per_keyword: int = None) -> list:
        """Collect tweets for all configured keywords."""
        keywords = keywords or config.SEARCH_KEYWORDS
        all_posts = []
        for kw in keywords:
            posts = self.search_recent_tweets(kw, max_per_keyword)
            all_posts.extend(posts)
        logger.info(f"Twitter total collected: {len(all_posts)} tweets")
        return all_posts


# ─────────────────────────────────────────────
#  Quick standalone test
# ─────────────────────────────────────────────
if __name__ == "__main__":
    collector = TwitterCollector()
    results = collector.collect_all(["python programming"], max_per_keyword=10)
    for r in results[:3]:
        print(r["text"][:100], "|", r["timestamp"])
