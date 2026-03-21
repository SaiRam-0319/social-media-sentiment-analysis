# =============================================================================
#  storage/database.py — SQLite Storage + CSV Export
# =============================================================================

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import csv
import json
import sqlite3
from datetime import datetime
from utils.helpers import setup_logger
import config

logger = setup_logger("Storage", config.LOG_FILE, config.LOG_LEVEL)


# ─────────────────────────────────────────────
#  SQLITE DATABASE MANAGER
# ─────────────────────────────────────────────
class DatabaseManager:
    """
    Manages SQLite database for storing raw posts and sentiment results.
    Creates tables automatically on first run.
    """

    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.SQLITE_DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row   # Rows behave like dicts
        self._create_tables()
        logger.info(f"Database connected: {self.db_path}")

    def _create_tables(self):
        """Create all required tables if they don't exist."""
        cursor = self.conn.cursor()

        # Raw posts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS raw_posts (
                post_id         TEXT PRIMARY KEY,
                platform        TEXT NOT NULL,
                text            TEXT NOT NULL,
                author_id       TEXT,
                username        TEXT,
                timestamp       TEXT,
                language        TEXT DEFAULT 'en',
                hashtags        TEXT,
                mentions        TEXT,
                engagement_json TEXT,
                keyword         TEXT,
                collected_at    TEXT DEFAULT (datetime('now'))
            )
        """)

        # Sentiment results table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sentiment_results (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id              TEXT NOT NULL,
                platform             TEXT,
                text                 TEXT,
                cleaned_text         TEXT,
                sentiment            TEXT,
                confidence           REAL,
                score_positive       REAL,
                score_negative       REAL,
                score_neutral        REAL,
                emotion              TEXT,
                vader_score          REAL,
                textblob_score       REAL,
                transformer_sentiment TEXT,
                transformer_score    REAL,
                keywords             TEXT,
                model_version        TEXT,
                timestamp            TEXT,
                language             TEXT,
                author               TEXT,
                keyword              TEXT,
                likes                INTEGER DEFAULT 0,
                shares               INTEGER DEFAULT 0,
                analyzed_at          TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (post_id) REFERENCES raw_posts(post_id)
            )
        """)

        # Aggregated stats table (for dashboard queries)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_stats (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                date           TEXT NOT NULL,
                platform       TEXT NOT NULL,
                keyword        TEXT,
                total_posts    INTEGER DEFAULT 0,
                positive_count INTEGER DEFAULT 0,
                negative_count INTEGER DEFAULT 0,
                neutral_count  INTEGER DEFAULT 0,
                avg_confidence REAL,
                avg_vader      REAL,
                top_emotion    TEXT,
                updated_at     TEXT DEFAULT (datetime('now')),
                UNIQUE(date, platform, keyword)
            )
        """)

        self.conn.commit()
        logger.info("Database tables verified/created.")

    def insert_raw_post(self, post: dict) -> bool:
        """Insert a raw post. Returns True if inserted, False if already exists."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO raw_posts
                (post_id, platform, text, author_id, username, timestamp,
                 language, hashtags, mentions, engagement_json, keyword)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (
                post.get("post_id", ""),
                post.get("platform", ""),
                post.get("text", ""),
                post.get("author_id", ""),
                post.get("username", ""),
                post.get("timestamp", ""),
                post.get("language", "en"),
                json.dumps(post.get("hashtags", [])),
                json.dumps(post.get("mentions", [])),
                json.dumps(post.get("engagement", {})),
                post.get("keyword", ""),
            ))
            self.conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"DB insert error (raw_post): {e}")
            return False

    def insert_raw_posts_batch(self, posts: list) -> int:
        """Insert multiple raw posts. Returns count of newly inserted rows."""
        inserted = 0
        for post in posts:
            if self.insert_raw_post(post):
                inserted += 1
        logger.info(f"Inserted {inserted}/{len(posts)} new raw posts.")
        return inserted

    def insert_sentiment_result(self, result) -> bool:
        """Insert a SentimentResult into the database."""
        try:
            d = result.to_dict() if hasattr(result, "to_dict") else result
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO sentiment_results
                (post_id, platform, text, cleaned_text, sentiment, confidence,
                 score_positive, score_negative, score_neutral, emotion,
                 vader_score, textblob_score, transformer_sentiment, transformer_score,
                 keywords, model_version, timestamp, language, author, keyword, likes, shares)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                d.get("post_id", ""),
                d.get("platform", ""),
                d.get("text", ""),
                d.get("cleaned_text", ""),
                d.get("sentiment", ""),
                d.get("confidence", 0.0),
                d.get("score_positive", 0.0),
                d.get("score_negative", 0.0),
                d.get("score_neutral", 0.0),
                d.get("emotion", ""),
                d.get("vader_score", 0.0),
                d.get("textblob_score", 0.0),
                d.get("transformer_sentiment", ""),
                d.get("transformer_score", 0.0),
                d.get("keywords", ""),
                d.get("model_version", ""),
                d.get("timestamp", ""),
                d.get("language", "en"),
                d.get("author", ""),
                d.get("keyword", ""),
                d.get("likes", 0),
                d.get("shares", 0),
            ))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"DB insert error (sentiment_result): {e}")
            return False

    def insert_results_batch(self, results: list) -> int:
        """Insert multiple SentimentResult objects."""
        count = 0
        for r in results:
            if self.insert_sentiment_result(r):
                count += 1
        logger.info(f"Saved {count}/{len(results)} sentiment results to DB.")
        return count

    def update_daily_stats(self):
        """Recalculate and upsert daily aggregated stats."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO daily_stats
            (date, platform, keyword, total_posts, positive_count, negative_count,
             neutral_count, avg_confidence, avg_vader, top_emotion)
            SELECT
                DATE(analyzed_at)   AS date,
                platform,
                keyword,
                COUNT(*)            AS total_posts,
                SUM(CASE WHEN sentiment = 'positive' THEN 1 ELSE 0 END),
                SUM(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END),
                SUM(CASE WHEN sentiment = 'neutral'  THEN 1 ELSE 0 END),
                AVG(confidence),
                AVG(vader_score),
                (SELECT emotion FROM sentiment_results s2
                 WHERE DATE(s2.analyzed_at) = DATE(s1.analyzed_at)
                   AND s2.platform = s1.platform
                 GROUP BY emotion ORDER BY COUNT(*) DESC LIMIT 1)
            FROM sentiment_results s1
            GROUP BY DATE(analyzed_at), platform, keyword
        """)
        self.conn.commit()
        logger.info("Daily stats updated.")

    # ── QUERY METHODS ──────────────────────────

    def get_all_results(self, limit: int = 1000, platform: str = None,
                        sentiment: str = None) -> list:
        """Fetch sentiment results with optional filters."""
        cursor = self.conn.cursor()
        query = "SELECT * FROM sentiment_results WHERE 1=1"
        params = []
        if platform:
            query += " AND platform = ?"
            params.append(platform)
        if sentiment:
            query += " AND sentiment = ?"
            params.append(sentiment)
        query += " ORDER BY analyzed_at DESC LIMIT ?"
        params.append(limit)
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_sentiment_summary(self) -> dict:
        """Return overall sentiment counts and percentages."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN sentiment='positive' THEN 1 ELSE 0 END) as positive,
                SUM(CASE WHEN sentiment='negative' THEN 1 ELSE 0 END) as negative,
                SUM(CASE WHEN sentiment='neutral'  THEN 1 ELSE 0 END) as neutral,
                AVG(confidence) as avg_confidence,
                AVG(vader_score) as avg_vader
            FROM sentiment_results
        """)
        row = cursor.fetchone()
        if not row or row["total"] == 0:
            return {}
        total = row["total"]
        return {
            "total":          total,
            "positive":       row["positive"],
            "negative":       row["negative"],
            "neutral":        row["neutral"],
            "positive_pct":   round(row["positive"] / total * 100, 1),
            "negative_pct":   round(row["negative"] / total * 100, 1),
            "neutral_pct":    round(row["neutral"]  / total * 100, 1),
            "avg_confidence": round(row["avg_confidence"] or 0, 4),
            "avg_vader":      round(row["avg_vader"] or 0, 4),
        }

    def get_platform_breakdown(self) -> list:
        """Sentiment counts grouped by platform."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT platform,
                   COUNT(*) as total,
                   SUM(CASE WHEN sentiment='positive' THEN 1 ELSE 0 END) as positive,
                   SUM(CASE WHEN sentiment='negative' THEN 1 ELSE 0 END) as negative,
                   SUM(CASE WHEN sentiment='neutral'  THEN 1 ELSE 0 END) as neutral
            FROM sentiment_results
            GROUP BY platform
            ORDER BY total DESC
        """)
        return [dict(row) for row in cursor.fetchall()]

    def get_trend(self, days: int = 7) -> list:
        """Daily sentiment trend for the last N days."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT DATE(analyzed_at) as date,
                   SUM(CASE WHEN sentiment='positive' THEN 1 ELSE 0 END) as positive,
                   SUM(CASE WHEN sentiment='negative' THEN 1 ELSE 0 END) as negative,
                   SUM(CASE WHEN sentiment='neutral'  THEN 1 ELSE 0 END) as neutral,
                   COUNT(*) as total
            FROM sentiment_results
            WHERE analyzed_at >= datetime('now', ?)
            GROUP BY DATE(analyzed_at)
            ORDER BY date ASC
        """, (f"-{days} days",))
        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed.")


# ─────────────────────────────────────────────
#  CSV EXPORTER
# ─────────────────────────────────────────────
class CSVExporter:
    """Export sentiment results to CSV file."""

    FIELDNAMES = [
        "post_id", "platform", "text", "sentiment", "confidence",
        "score_positive", "score_negative", "score_neutral",
        "emotion", "vader_score", "textblob_score",
        "transformer_sentiment", "transformer_score",
        "keywords", "author", "timestamp", "language",
        "keyword", "likes", "shares", "model_version",
    ]

    def __init__(self, filepath: str = None):
        self.filepath = filepath or config.CSV_OUTPUT_PATH
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)

    def export(self, results: list, append: bool = False) -> str:
        """
        Export list of SentimentResult or dict objects to CSV.
        append=True adds to existing file, False overwrites.
        """
        mode = "a" if append else "w"
        write_header = not (append and os.path.exists(self.filepath))

        rows = []
        for r in results:
            if hasattr(r, "to_dict"):
                rows.append(r.to_dict())
            elif isinstance(r, dict):
                rows.append(r)

        with open(self.filepath, mode, newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES, extrasaction="ignore")
            if write_header:
                writer.writeheader()
            writer.writerows(rows)

        logger.info(f"Exported {len(rows)} results to {self.filepath}")
        return self.filepath

    def export_from_db(self, db: DatabaseManager) -> str:
        """Pull all results from DB and export to CSV."""
        results = db.get_all_results(limit=100000)
        return self.export(results)


if __name__ == "__main__":
    db = DatabaseManager()
    summary = db.get_sentiment_summary()
    print("DB Summary:", summary)
    db.close()
