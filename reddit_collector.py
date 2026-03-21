# =============================================================================
#  collectors/reddit_collector.py — Reddit Data Collection via PRAW
# =============================================================================

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import praw
from praw.exceptions import PRAWException
from utils.helpers import setup_logger, format_timestamp
import config

logger = setup_logger("RedditCollector", config.LOG_FILE, config.LOG_LEVEL)


class RedditCollector:
    """
    Collects posts and top-level comments from Reddit using PRAW.
    Supports subreddit hot/new/top feeds and keyword search.
    """

    def __init__(self):
        self.reddit = None
        self._authenticate()

    def _authenticate(self):
        """Authenticate with Reddit API."""
        try:
            self.reddit = praw.Reddit(
                client_id=config.REDDIT_CLIENT_ID,
                client_secret=config.REDDIT_CLIENT_SECRET,
                user_agent=config.REDDIT_USER_AGENT,
                username=config.REDDIT_USERNAME,
                password=config.REDDIT_PASSWORD,
            )
            # Verify by accessing the authenticated user
            username = self.reddit.user.me()
            logger.info(f"Reddit authenticated as: u/{username}")
        except PRAWException as e:
            logger.error(f"Reddit authentication failed: {e}")
            self.reddit = None

    def collect_subreddit_posts(self, subreddit_name: str,
                                feed: str = "hot",
                                limit: int = None) -> list:
        """
        Collect posts from a subreddit.
        feed: 'hot' | 'new' | 'top' | 'rising'
        """
        if not self.reddit:
            logger.warning("Reddit client not authenticated. Skipping.")
            return []

        limit = limit or config.MAX_REDDIT_POSTS
        logger.info(f"Collecting r/{subreddit_name} [{feed}] (limit={limit})")

        posts = []
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            feed_map = {
                "hot":    subreddit.hot,
                "new":    subreddit.new,
                "top":    subreddit.top,
                "rising": subreddit.rising,
            }
            fetcher = feed_map.get(feed, subreddit.hot)

            for submission in fetcher(limit=limit):
                # Combine title + selftext for richer analysis
                combined_text = submission.title
                if submission.selftext and submission.selftext != "[removed]":
                    combined_text += " " + submission.selftext

                posts.append({
                    "post_id":    f"rd_{submission.id}",
                    "platform":   "Reddit",
                    "text":       combined_text,
                    "title":      submission.title,
                    "selftext":   submission.selftext or "",
                    "author_id":  str(submission.author) if submission.author else "[deleted]",
                    "author_name": str(submission.author) if submission.author else "[deleted]",
                    "username":   f"u/{submission.author}" if submission.author else "u/[deleted]",
                    "timestamp":  format_timestamp(submission.created_utc),
                    "language":   "en",
                    "hashtags":   [],
                    "mentions":   [],
                    "urls":       [submission.url] if submission.url else [],
                    "engagement": {
                        "upvotes":        submission.score,
                        "upvote_ratio":   submission.upvote_ratio,
                        "num_comments":   submission.num_comments,
                        "awards":         submission.total_awards_received,
                    },
                    "subreddit":  subreddit_name,
                    "permalink":  f"https://reddit.com{submission.permalink}",
                    "is_nsfw":    submission.over_18,
                    "flair":      submission.link_flair_text or "",
                    "keyword":    subreddit_name,
                    "raw":        combined_text,
                })

        except PRAWException as e:
            logger.error(f"Error fetching r/{subreddit_name}: {e}")

        logger.info(f"Reddit: collected {len(posts)} posts from r/{subreddit_name}")
        return posts

    def collect_comments(self, submission_id: str, limit: int = 20) -> list:
        """Collect top-level comments from a specific Reddit submission."""
        if not self.reddit:
            return []
        comments = []
        try:
            submission = self.reddit.submission(id=submission_id)
            submission.comments.replace_more(limit=0)  # Flatten comment tree
            for comment in list(submission.comments)[:limit]:
                if not comment.body or comment.body in ("[removed]", "[deleted]"):
                    continue
                comments.append({
                    "post_id":    f"rd_c_{comment.id}",
                    "platform":   "Reddit",
                    "text":       comment.body,
                    "author_id":  str(comment.author) if comment.author else "[deleted]",
                    "author_name": str(comment.author) if comment.author else "[deleted]",
                    "username":   f"u/{comment.author}" if comment.author else "u/[deleted]",
                    "timestamp":  format_timestamp(comment.created_utc),
                    "language":   "en",
                    "hashtags":   [],
                    "mentions":   [],
                    "urls":       [],
                    "engagement": {"upvotes": comment.score, "replies": len(comment.replies)},
                    "subreddit":  str(submission.subreddit),
                    "parent_id":  f"rd_{submission_id}",
                    "keyword":    str(submission.subreddit),
                    "raw":        comment.body,
                })
        except PRAWException as e:
            logger.error(f"Error fetching comments for {submission_id}: {e}")
        return comments

    def search_reddit(self, query: str, limit: int = None) -> list:
        """Search Reddit across all subreddits for a keyword."""
        if not self.reddit:
            return []
        limit = limit or config.MAX_REDDIT_POSTS
        logger.info(f"Searching Reddit for: '{query}'")
        posts = []
        try:
            for submission in self.reddit.subreddit("all").search(query, limit=limit, sort="new"):
                combined_text = submission.title
                if submission.selftext and submission.selftext != "[removed]":
                    combined_text += " " + submission.selftext
                posts.append({
                    "post_id":    f"rd_{submission.id}",
                    "platform":   "Reddit",
                    "text":       combined_text,
                    "author_id":  str(submission.author) if submission.author else "[deleted]",
                    "author_name": str(submission.author) if submission.author else "[deleted]",
                    "username":   f"u/{submission.author}" if submission.author else "u/[deleted]",
                    "timestamp":  format_timestamp(submission.created_utc),
                    "language":   "en",
                    "hashtags":   [],
                    "mentions":   [],
                    "urls":       [],
                    "engagement": {"upvotes": submission.score, "num_comments": submission.num_comments},
                    "subreddit":  str(submission.subreddit),
                    "keyword":    query,
                    "raw":        combined_text,
                })
        except PRAWException as e:
            logger.error(f"Reddit search error: {e}")
        return posts

    def collect_all(self, subreddits: list = None, limit: int = None) -> list:
        """Collect posts from all configured subreddits."""
        subreddits = subreddits or config.REDDIT_SUBREDDITS
        all_posts = []
        for sub in subreddits:
            posts = self.collect_subreddit_posts(sub, feed="hot", limit=limit)
            all_posts.extend(posts)
        logger.info(f"Reddit total collected: {len(all_posts)} posts")
        return all_posts


if __name__ == "__main__":
    collector = RedditCollector()
    results = collector.collect_all(["technology"], limit=5)
    for r in results[:3]:
        print(r["text"][:100], "|", r["timestamp"])
