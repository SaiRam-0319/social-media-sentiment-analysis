# =============================================================================
#  collectors/twitter_free.py
#  FREE Twitter scraper using ntscraper — NO API KEY NEEDED
# =============================================================================

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import config

def collect_tweets_free(keywords=None, max_tweets=None):
    """
    Scrape tweets for free using ntscraper.
    No Twitter API key needed at all!
    """
    keywords   = keywords   or config.SEARCH_KEYWORDS
    max_tweets = max_tweets or config.MAX_TWEETS
    all_posts  = []

    try:
        from ntscraper import Nitter
        scraper = Nitter(log_level=0, skip_instance_check=False)

        for keyword in keywords:
            print(f"  🐦 Scraping tweets for: '{keyword}'")
            try:
                tweets = scraper.get_tweets(keyword, mode="term", number=max_tweets)

                for tweet in tweets.get("tweets", []):
                    text = tweet.get("text", "").strip()
                    if not text:
                        continue

                    all_posts.append({
                        "post_id":    f"tw_{tweet.get('link','').split('/')[-1]}",
                        "platform":   "Twitter",
                        "text":       text,
                        "author_id":  tweet.get("user", {}).get("username", "unknown"),
                        "author_name": tweet.get("user", {}).get("name", "Unknown"),
                        "username":   f"@{tweet.get('user', {}).get('username', 'unknown')}",
                        "timestamp":  tweet.get("date", ""),
                        "language":   "en",
                        "hashtags":   [],
                        "mentions":   [],
                        "urls":       [],
                        "engagement": {
                            "likes":    tweet.get("stats", {}).get("likes", 0),
                            "retweets": tweet.get("stats", {}).get("retweets", 0),
                            "comments": tweet.get("stats", {}).get("comments", 0),
                        },
                        "keyword": keyword,
                        "raw":     text,
                    })

                print(f"     ✅ Got {len(tweets.get('tweets', []))} tweets")

            except Exception as e:
                print(f"     ⚠️  Could not scrape '{keyword}': {e}")
                continue

    except ImportError:
        print("  ⚠️  ntscraper not installed. Run: pip install ntscraper")
    except Exception as e:
        print(f"  ⚠️  Twitter scraper error: {e}")

    print(f"  Twitter total: {len(all_posts)} tweets collected")
    return all_posts


if __name__ == "__main__":
    posts = collect_tweets_free(["python programming"], max_tweets=5)
    for p in posts[:3]:
        print(p["text"][:80])
