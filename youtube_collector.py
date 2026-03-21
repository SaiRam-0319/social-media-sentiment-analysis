# =============================================================================
#  collectors/youtube_collector.py — YouTube Comment Collection via Data API v3
# =============================================================================

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from utils.helpers import setup_logger, format_timestamp
import config

logger = setup_logger("YouTubeCollector", config.LOG_FILE, config.LOG_LEVEL)


class YouTubeCollector:
    """
    Collects video metadata and comments from YouTube using the Data API v3.
    Searches for videos by keyword, then pulls top-level comments.
    """

    def __init__(self):
        self.youtube = None
        self._authenticate()

    def _authenticate(self):
        """Build the YouTube API client."""
        try:
            self.youtube = build(
                "youtube", "v3",
                developerKey=config.YOUTUBE_API_KEY,
            )
            logger.info("YouTube API client initialized successfully.")
        except Exception as e:
            logger.error(f"YouTube API init failed: {e}")
            self.youtube = None

    def search_videos(self, query: str, max_results: int = 5) -> list:
        """
        Search YouTube for videos matching `query`.
        Returns list of video IDs and titles.
        """
        if not self.youtube:
            return []
        try:
            response = self.youtube.search().list(
                q=query,
                part="id,snippet",
                type="video",
                maxResults=max_results,
                relevanceLanguage="en",
                order="relevance",
            ).execute()

            videos = []
            for item in response.get("items", []):
                videos.append({
                    "video_id":      item["id"]["videoId"],
                    "title":         item["snippet"]["title"],
                    "channel":       item["snippet"]["channelTitle"],
                    "published_at":  item["snippet"]["publishedAt"],
                    "description":   item["snippet"]["description"],
                })
            logger.info(f"Found {len(videos)} videos for '{query}'")
            return videos
        except HttpError as e:
            logger.error(f"YouTube search error: {e}")
            return []

    def get_video_comments(self, video_id: str, video_title: str = "",
                           max_comments: int = None) -> list:
        """
        Fetch top-level comments for a YouTube video.
        Returns list of normalized post dictionaries.
        """
        if not self.youtube:
            return []

        max_comments = max_comments or config.MAX_YOUTUBE_COMMENTS
        logger.info(f"Fetching comments for video: {video_id} (max={max_comments})")

        posts = []
        page_token = None

        try:
            while len(posts) < max_comments:
                fetch_count = min(100, max_comments - len(posts))  # API max is 100
                request_kwargs = {
                    "part":       "snippet",
                    "videoId":    video_id,
                    "maxResults": fetch_count,
                    "order":      "relevance",  # or "time"
                    "textFormat": "plainText",
                }
                if page_token:
                    request_kwargs["pageToken"] = page_token

                response = self.youtube.commentThreads().list(**request_kwargs).execute()

                for item in response.get("items", []):
                    snippet = item["snippet"]["topLevelComment"]["snippet"]
                    posts.append({
                        "post_id":    f"yt_{item['id']}",
                        "platform":   "YouTube",
                        "text":       snippet["textDisplay"],
                        "author_id":  snippet.get("authorChannelId", {}).get("value", "unknown"),
                        "author_name": snippet.get("authorDisplayName", "Unknown"),
                        "username":   snippet.get("authorDisplayName", "Unknown"),
                        "timestamp":  format_timestamp(snippet.get("publishedAt", "")),
                        "language":   "en",
                        "hashtags":   [],
                        "mentions":   [],
                        "urls":       [],
                        "engagement": {
                            "likes":     snippet.get("likeCount", 0),
                            "replies":   item["snippet"].get("totalReplyCount", 0),
                        },
                        "video_id":   video_id,
                        "video_title": video_title,
                        "keyword":    video_title,
                        "raw":        snippet["textDisplay"],
                    })

                page_token = response.get("nextPageToken")
                if not page_token:
                    break  # No more pages

        except HttpError as e:
            error_reason = e.error_details[0]["reason"] if e.error_details else str(e)
            if "commentsDisabled" in error_reason:
                logger.info(f"Comments disabled for video {video_id}")
            else:
                logger.error(f"YouTube comment fetch error for {video_id}: {e}")

        logger.info(f"Collected {len(posts)} comments from video {video_id}")
        return posts

    def collect_all(self, keywords: list = None, videos_per_keyword: int = 3,
                    comments_per_video: int = None) -> list:
        """
        For each keyword: search videos → fetch comments.
        Returns all comments as normalized post dicts.
        """
        keywords = keywords or config.SEARCH_KEYWORDS
        comments_per_video = comments_per_video or config.MAX_YOUTUBE_COMMENTS
        all_posts = []

        for keyword in keywords:
            videos = self.search_videos(keyword, max_results=videos_per_keyword)
            for video in videos:
                comments = self.get_video_comments(
                    video["video_id"],
                    video_title=video["title"],
                    max_comments=comments_per_video,
                )
                all_posts.extend(comments)

        logger.info(f"YouTube total collected: {len(all_posts)} comments")
        return all_posts


if __name__ == "__main__":
    collector = YouTubeCollector()
    results = collector.collect_all(["python programming"], videos_per_keyword=2, comments_per_video=5)
    for r in results[:3]:
        print(r["text"][:100], "|", r["timestamp"])
