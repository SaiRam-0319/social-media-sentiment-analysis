# =============================================================================
#  collectors/news_collector.py
#  FREE News Articles using NewsAPI — https://newsapi.org (free for students)
# =============================================================================

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import requests
import config

def collect_news(keywords=None, max_articles=None):
    """
    Collect news articles using NewsAPI.
    Free plan: 1000 requests/day — no credit card needed.
    Get free key at: https://newsapi.org/
    """
    keywords     = keywords     or config.SEARCH_KEYWORDS
    max_articles = max_articles or config.MAX_NEWS_ARTICLES
    all_posts    = []

    if not config.NEWS_API_KEY or config.NEWS_API_KEY == "YOUR_NEWSAPI_KEY":
        print("  ⚠️  NewsAPI key not set in config.py")
        print("  👉  Get free key at: https://newsapi.org/")
        return []

    base_url = "https://newsapi.org/v2/everything"

    for keyword in keywords:
        print(f"  📰 Fetching news for: '{keyword}'")
        try:
            response = requests.get(base_url, params={
                "q":        keyword,
                "language": "en",
                "sortBy":   "publishedAt",
                "pageSize": min(max_articles, 100),  # Max 100 per request
                "apiKey":   config.NEWS_API_KEY,
            }, timeout=10)

            data = response.json()

            if data.get("status") != "ok":
                print(f"     ⚠️  NewsAPI error: {data.get('message', 'Unknown error')}")
                continue

            for article in data.get("articles", []):
                # Combine title + description for richer analysis
                text = ""
                if article.get("title"):
                    text += article["title"]
                if article.get("description"):
                    text += " " + article["description"]
                text = text.strip()

                if not text or text == "[Removed]":
                    continue

                all_posts.append({
                    "post_id":    f"news_{hash(article.get('url', text)) % 999999}",
                    "platform":   "News",
                    "text":       text,
                    "author_id":  article.get("source", {}).get("id", "unknown"),
                    "author_name": article.get("author", "Unknown"),
                    "username":   article.get("source", {}).get("name", "Unknown Source"),
                    "timestamp":  article.get("publishedAt", ""),
                    "language":   "en",
                    "hashtags":   [],
                    "mentions":   [],
                    "urls":       [article.get("url", "")],
                    "engagement": {},
                    "keyword":    keyword,
                    "raw":        text,
                })

            print(f"     ✅ Got {len(data.get('articles', []))} articles")

        except requests.exceptions.RequestException as e:
            print(f"     ⚠️  News fetch error for '{keyword}': {e}")

    print(f"  News total: {len(all_posts)} articles collected")
    return all_posts


if __name__ == "__main__":
    posts = collect_news(["artificial intelligence"], max_articles=5)
    for p in posts[:3]:
        print(p["text"][:100])
