# =============================================================================
#  api/app.py — Flask REST API for Sentiment Analysis
#  Endpoints: analyze, batch, trends, summary, platform breakdown, health
# =============================================================================

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, request, jsonify, abort
from flask_cors import CORS
from datetime import datetime
from functools import wraps

import config
from models.sentiment_model import SentimentEngine
from storage.database import DatabaseManager, CSVExporter
from utils.helpers import setup_logger

logger = setup_logger("FlaskAPI", config.LOG_FILE, config.LOG_LEVEL)

# ─────────────────────────────────────────────
#  App Initialization
# ─────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = config.API_SECRET_KEY
CORS(app)  # Allow all origins (restrict in production)

# Lazy-loaded singletons (loaded on first request to keep startup fast)
_engine  = None
_db      = None
_exporter = None


def get_engine() -> SentimentEngine:
    global _engine
    if _engine is None:
        logger.info("Loading SentimentEngine...")
        _engine = SentimentEngine()
    return _engine


def get_db() -> DatabaseManager:
    global _db
    if _db is None:
        _db = DatabaseManager()
    return _db


def get_exporter() -> CSVExporter:
    global _exporter
    if _exporter is None:
        _exporter = CSVExporter()
    return _exporter


# ─────────────────────────────────────────────
#  Auth Decorator (simple API key check)
# ─────────────────────────────────────────────
def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get("X-API-Key") or request.args.get("api_key")
        if not key or key != config.API_SECRET_KEY:
            return jsonify({"error": "Unauthorized. Provide a valid X-API-Key header."}), 401
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────
#  ROUTES
# ─────────────────────────────────────────────

@app.route("/", methods=["GET"])
def index():
    """API root — lists all available endpoints."""
    return jsonify({
        "name":    "Social Media Sentiment Analysis API",
        "version": "1.0",
        "status":  "running",
        "endpoints": {
            "POST /analyze":            "Analyze a single post",
            "POST /analyze/batch":      "Analyze up to 100 posts",
            "GET  /results":            "Fetch stored results (with filters)",
            "GET  /summary":            "Overall sentiment summary stats",
            "GET  /platforms":          "Sentiment breakdown by platform",
            "GET  /trends":             "Daily sentiment trend (last N days)",
            "GET  /export/csv":         "Export all results to CSV",
            "GET  /health":             "System health check",
        },
    })


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({
        "status":    "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "model":     config.SENTIMENT_MODEL,
        "db":        config.SQLITE_DB_PATH,
    })


@app.route("/analyze", methods=["POST"])
@require_api_key
def analyze():
    """
    Analyze a single post.
    Body (JSON):
        {
            "text":     "I love this product!",
            "platform": "Twitter",          (optional)
            "post_id":  "my_post_001",      (optional)
            "save":     true                (optional, saves to DB)
        }
    """
    data = request.get_json(force=True, silent=True)
    if not data or "text" not in data:
        return jsonify({"error": "Request body must include 'text' field."}), 400

    post = {
        "post_id":   data.get("post_id", f"api_{datetime.utcnow().timestamp()}"),
        "platform":  data.get("platform", "API"),
        "text":      data["text"],
        "timestamp": datetime.utcnow().isoformat(),
        "language":  data.get("language", "en"),
        "username":  data.get("author", "api_user"),
        "engagement": {},
        "keyword":   data.get("keyword", ""),
    }

    engine = get_engine()
    result = engine.analyze(post)

    if data.get("save", True):
        db = get_db()
        db.insert_raw_post(post)
        db.insert_sentiment_result(result)

    return jsonify({
        "status": "success",
        "result": result.to_dict(),
    }), 200


@app.route("/analyze/batch", methods=["POST"])
@require_api_key
def analyze_batch():
    """
    Analyze multiple posts.
    Body (JSON):
        {
            "posts": [
                {"text": "Great!", "platform": "Twitter"},
                {"text": "Terrible.", "platform": "Reddit"}
            ],
            "save": true
        }
    Limit: 100 posts per request.
    """
    data = request.get_json(force=True, silent=True)
    if not data or "posts" not in data:
        return jsonify({"error": "Body must include 'posts' array."}), 400

    posts = data["posts"]
    if len(posts) > 100:
        return jsonify({"error": "Maximum 100 posts per batch request."}), 400

    # Normalize each post
    normalized = []
    for i, p in enumerate(posts):
        if "text" not in p:
            continue
        normalized.append({
            "post_id":   p.get("post_id", f"api_b{i}_{datetime.utcnow().timestamp()}"),
            "platform":  p.get("platform", "API"),
            "text":      p["text"],
            "timestamp": p.get("timestamp", datetime.utcnow().isoformat()),
            "language":  p.get("language", "en"),
            "username":  p.get("author", "api_user"),
            "engagement": {},
            "keyword":   p.get("keyword", ""),
        })

    if not normalized:
        return jsonify({"error": "No valid posts with 'text' field found."}), 400

    engine = get_engine()
    results = engine.analyze_batch(normalized, show_progress=False)

    if data.get("save", True):
        db = get_db()
        db.insert_raw_posts_batch(normalized)
        db.insert_results_batch(results)

    return jsonify({
        "status":  "success",
        "count":   len(results),
        "results": [r.to_dict() for r in results],
    }), 200


@app.route("/results", methods=["GET"])
@require_api_key
def get_results():
    """
    Fetch stored sentiment results.
    Query params:
        limit     (default 100)
        platform  (Twitter | Reddit | YouTube)
        sentiment (positive | negative | neutral)
    """
    limit     = int(request.args.get("limit", 100))
    platform  = request.args.get("platform")
    sentiment = request.args.get("sentiment")

    db = get_db()
    rows = db.get_all_results(limit=limit, platform=platform, sentiment=sentiment)
    return jsonify({"count": len(rows), "results": rows}), 200


@app.route("/summary", methods=["GET"])
@require_api_key
def summary():
    """Overall sentiment summary across all stored results."""
    db = get_db()
    data = db.get_sentiment_summary()
    return jsonify({"status": "success", "summary": data}), 200


@app.route("/platforms", methods=["GET"])
@require_api_key
def platforms():
    """Sentiment counts broken down by platform."""
    db = get_db()
    data = db.get_platform_breakdown()
    return jsonify({"status": "success", "platforms": data}), 200


@app.route("/trends", methods=["GET"])
@require_api_key
def trends():
    """
    Daily sentiment trend.
    Query param: days (default 7)
    """
    days = int(request.args.get("days", 7))
    db = get_db()
    data = db.get_trend(days=days)
    return jsonify({"status": "success", "days": days, "trend": data}), 200


@app.route("/export/csv", methods=["GET"])
@require_api_key
def export_csv():
    """Export all results to CSV and return file path."""
    db = get_db()
    exporter = get_exporter()
    path = exporter.export_from_db(db)
    return jsonify({"status": "success", "file": path}), 200


# ─────────────────────────────────────────────
#  Error Handlers
# ─────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found."}), 404


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "Method not allowed."}), 405


@app.errorhandler(500)
def server_error(e):
    logger.error(f"Internal server error: {e}")
    return jsonify({"error": "Internal server error."}), 500


# ─────────────────────────────────────────────
#  Run Server
# ─────────────────────────────────────────────
if __name__ == "__main__":
    logger.info(f"Starting Flask API on {config.FLASK_HOST}:{config.FLASK_PORT}")
    app.run(
        host=config.FLASK_HOST,
        port=config.FLASK_PORT,
        debug=config.FLASK_DEBUG,
    )
