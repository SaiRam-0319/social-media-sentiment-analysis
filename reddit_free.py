# =============================================================================
#  collectors/reddit_free.py
#  FREE Reddit collector using PRAW — completely free, no payment needed
# =============================================================================

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import config

def collect_reddit(subreddits=None, limit=None):
    """
    Collect Reddit posts — 100% free, no payment.
    Get keys at: https://www.reddit.com/prefs/apps (takes 2 minutes)
    """
    subreddits = subreddits or config.REDDIT_SUBREDDITS
    limit      = limit      or config.MAX_REDDIT_POSTS
    all_posts  = []

    if config.REDDIT_CLIENT_ID == "YOUR_REDDIT_CLIENT_ID":
        print("  ⚠️  Reddit keys not set in config.py")
        print("  👉  Get free keys at: https://www.reddit.com/prefs/apps")
        return []

    try:
        import praw
        reddit = praw.Reddit(
            client_id=config.REDDIT_CLIENT_ID,
            client_secret=config.REDDIT_CLIENT_SECRET,
            user_agent=config.REDDIT_USER_AGENT,
            username=config.REDDIT_USERNAME,
            password=config.REDDIT_PASSWORD,
        )

        for subreddit_name in subreddits:
            print(f"  👾 Collecting r/{subreddit_name}")
            try:
                subreddit = reddit.subreddit(subreddit_name)
                for post in subreddit.hot(limit=limit):
                    text = post.title
                    if post.selftext and post.selftext != "[removed]":
                        text += " " + post.selftext

                    all_posts.append({
                        "post_id":    f"rd_{post.id}",
                        "platform":   "Reddit",
                        "text":       text.strip(),
                        "author_id":  str(post.author) if post.author else "deleted",
                        "author_name": str(post.author) if post.author else "deleted",
                        "username":   f"u/{post.author}" if post.author else "u/deleted",
                        "timestamp":  str(post.created_utc),
                        "language":   "en",
                        "hashtags":   [],
                        "mentions":   [],
                        "urls":       [],
                        "engagement": {
                            "upvotes":      post.score,
                            "num_comments": post.num_comments,
                        },
                        "keyword":    subreddit_name,
                        "raw":        text,
                    })

                print(f"     ✅ Got {limit} posts from r/{subreddit_name}")

            except Exception as e:
                print(f"     ⚠️  Error on r/{subreddit_name}: {e}")

    except ImportError:
        print("  ⚠️  praw not installed. Run: pip install praw")
    except Exception as e:
        print(f"  ⚠️  Reddit error: {e}")

    print(f"  Reddit total: {len(all_posts)} posts collected")
    return all_posts


if __name__ == "__main__":
    posts = collect_reddit(["technology"], limit=5)
    for p in posts[:3]:
        print(p["text"][:100])
