# =============================================================================
#  main.py — Main Pipeline Orchestrator
#  Runs the full collection → analysis → storage → reporting pipeline.
#
#  Usage:
#    python main.py                   # Full pipeline (all platforms)
#    python main.py --mode twitter    # Twitter only
#    python main.py --mode reddit     # Reddit only
#    python main.py --mode youtube    # YouTube only
#    python main.py --mode analyze    # Analyze custom text (interactive)
#    python main.py --mode api        # Start Flask REST API server
#    python main.py --mode report     # Print report from DB (no collection)
# =============================================================================

import sys
import os
import argparse
from datetime import datetime

# Add project root to Python path
sys.path.insert(0, os.path.dirname(__file__))

import config
from utils.helpers import setup_logger, print_banner, print_result_table
from collectors.twitter_collector import TwitterCollector
from collectors.reddit_collector   import RedditCollector
from collectors.youtube_collector  import YouTubeCollector
from models.sentiment_model        import SentimentEngine
from storage.database              import DatabaseManager, CSVExporter

logger = setup_logger("Main", config.LOG_FILE, config.LOG_LEVEL)


# ─────────────────────────────────────────────
#  COLLECTION
# ─────────────────────────────────────────────
def collect_data(mode: str = "all") -> list:
    """Collect posts from selected platforms. Returns combined post list."""
    all_posts = []

    if mode in ("all", "twitter"):
        logger.info("=== Collecting from Twitter ===")
        tc = TwitterCollector()
        posts = tc.collect_all()
        logger.info(f"Twitter: {len(posts)} posts")
        all_posts.extend(posts)

    if mode in ("all", "reddit"):
        logger.info("=== Collecting from Reddit ===")
        rc = RedditCollector()
        posts = rc.collect_all()
        logger.info(f"Reddit: {len(posts)} posts")
        all_posts.extend(posts)

    if mode in ("all", "youtube"):
        logger.info("=== Collecting from YouTube ===")
        yc = YouTubeCollector()
        posts = yc.collect_all()
        logger.info(f"YouTube: {len(posts)} posts")
        all_posts.extend(posts)

    logger.info(f"Total collected: {len(all_posts)} posts")
    return all_posts


# ─────────────────────────────────────────────
#  ANALYSIS
# ─────────────────────────────────────────────
def analyze_posts(posts: list, engine: SentimentEngine) -> list:
    """Run sentiment analysis on all collected posts."""
    logger.info(f"=== Analyzing {len(posts)} posts ===")
    results = engine.analyze_batch(posts, show_progress=True)
    logger.info(f"Analysis complete: {len(results)} results")
    return results


# ─────────────────────────────────────────────
#  STORAGE
# ─────────────────────────────────────────────
def save_results(posts: list, results: list, db: DatabaseManager, exporter: CSVExporter):
    """Save raw posts and results to SQLite and CSV."""
    logger.info("=== Saving to database ===")
    db.insert_raw_posts_batch(posts)
    db.insert_results_batch(results)
    db.update_daily_stats()

    logger.info("=== Exporting to CSV ===")
    exporter.export(results)


# ─────────────────────────────────────────────
#  REPORT
# ─────────────────────────────────────────────
def print_report(db: DatabaseManager, results: list = None):
    """Print a summary report to the console."""
    from colorama import Fore, Style

    print(f"\n{Fore.CYAN}{'═'*60}")
    print(f"  SENTIMENT ANALYSIS REPORT  |  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'═'*60}{Style.RESET_ALL}\n")

    # Overall summary
    summary = db.get_sentiment_summary()
    if summary:
        total = summary["total"]
        print(f"{Fore.WHITE}Overall Summary ({total} total posts){Style.RESET_ALL}")
        print(f"  {Fore.GREEN}Positive: {summary['positive']:>5}  ({summary['positive_pct']}%){Style.RESET_ALL}")
        print(f"  {Fore.RED}Negative: {summary['negative']:>5}  ({summary['negative_pct']}%){Style.RESET_ALL}")
        print(f"  {Fore.YELLOW}Neutral:  {summary['neutral']:>5}  ({summary['neutral_pct']}%){Style.RESET_ALL}")
        print(f"  Avg Confidence: {summary['avg_confidence']:.2%}")
        print(f"  Avg VADER:      {summary['avg_vader']:+.3f}\n")

    # Platform breakdown
    platforms = db.get_platform_breakdown()
    if platforms:
        print(f"{Fore.WHITE}By Platform:{Style.RESET_ALL}")
        for p in platforms:
            print(f"  {p['platform']:<12} Total={p['total']:<5} "
                  f"[+{p['positive']} / -{p['negative']} / ~{p['neutral']}]")
        print()

    # Recent results table
    if results:
        print(f"{Fore.WHITE}Sample Results:{Style.RESET_ALL}")
        sample = [r.to_dict() for r in results[:10]]
        display = []
        for r in sample:
            display.append({
                "post_id":   r["post_id"],
                "platform":  r["platform"],
                "text":      r["text"],
                "sentiment": r["sentiment"],
                "confidence": r["confidence"],
                "emotion":   r["emotion"],
                "timestamp": r["timestamp"],
            })
        print_result_table(display)

    print(f"\n{Fore.CYAN}Results saved to:{Style.RESET_ALL}")
    print(f"  Database: {config.SQLITE_DB_PATH}")
    print(f"  CSV:      {config.CSV_OUTPUT_PATH}")
    print(f"  Log:      {config.LOG_FILE}\n")


# ─────────────────────────────────────────────
#  INTERACTIVE ANALYZER
# ─────────────────────────────────────────────
def interactive_mode(engine: SentimentEngine, db: DatabaseManager):
    """Interactive prompt — type text, get sentiment."""
    from colorama import Fore, Style
    print(f"\n{Fore.CYAN}Interactive Sentiment Analyzer{Style.RESET_ALL}")
    print("Type your text and press Enter to analyze. Type 'quit' to exit.\n")

    while True:
        try:
            text = input(f"{Fore.WHITE}Enter text > {Style.RESET_ALL}").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting interactive mode.")
            break

        if text.lower() in ("quit", "exit", "q"):
            break
        if not text:
            continue

        platform = input("Platform (Twitter/Reddit/YouTube/Other) [Other]: ").strip() or "Other"

        post = {
            "post_id":   f"interactive_{datetime.utcnow().timestamp()}",
            "platform":  platform,
            "text":      text,
            "timestamp": datetime.utcnow().isoformat(),
            "language":  "en",
            "username":  "interactive_user",
            "engagement": {},
            "keyword":   "interactive",
        }

        result = engine.analyze(post)
        db.insert_raw_post(post)
        db.insert_sentiment_result(result)

        color = Fore.GREEN if result.sentiment == "positive" else (
                Fore.RED   if result.sentiment == "negative" else Fore.YELLOW)

        print(f"\n  Sentiment:   {color}{result.sentiment.upper()}{Style.RESET_ALL}")
        print(f"  Confidence:  {result.confidence:.2%}")
        print(f"  Emotion:     {result.emotion}")
        print(f"  VADER score: {result.vader_score:+.3f}")
        print(f"  TextBlob:    {result.textblob_score:+.3f}")
        if result.transformer_sentiment != "n/a":
            print(f"  Transformer: {result.transformer_sentiment} ({result.transformer_score:.2%})")
        print(f"  Keywords:    {', '.join(result.keywords)}")
        print()


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Social Media Sentiment Analysis Pipeline"
    )
    parser.add_argument(
        "--mode",
        choices=["all", "twitter", "reddit", "youtube", "analyze", "api", "report"],
        default="all",
        help=(
            "all=full pipeline | twitter/reddit/youtube=single platform | "
            "analyze=interactive | api=start REST API | report=print DB report"
        ),
    )
    parser.add_argument("--keywords", nargs="+", help="Override keywords from config")
    parser.add_argument("--no-save",  action="store_true", help="Don't save results to DB/CSV")
    args = parser.parse_args()

    print_banner()

    if args.keywords:
        config.SEARCH_KEYWORDS = args.keywords
        logger.info(f"Keywords overridden: {config.SEARCH_KEYWORDS}")

    # Initialize storage
    os.makedirs("output", exist_ok=True)
    db       = DatabaseManager()
    exporter = CSVExporter()

    # ── API mode ──────────────────────────────
    if args.mode == "api":
        from api.app import app
        logger.info(f"Starting REST API on http://{config.FLASK_HOST}:{config.FLASK_PORT}")
        logger.info(f"API Key: {config.API_SECRET_KEY}")
        logger.info("Example call: curl -X POST http://localhost:5000/analyze "
                    "-H 'X-API-Key: your-key' -H 'Content-Type: application/json' "
                    "-d '{\"text\": \"I love this!\"}'")
        app.run(host=config.FLASK_HOST, port=config.FLASK_PORT, debug=config.FLASK_DEBUG)
        return

    # ── Report mode ───────────────────────────
    if args.mode == "report":
        print_report(db)
        db.close()
        return

    # ── Interactive mode ──────────────────────
    if args.mode == "analyze":
        engine = SentimentEngine()
        interactive_mode(engine, db)
        db.close()
        return

    # ── Full pipeline ─────────────────────────
    logger.info(f"Running pipeline in '{args.mode}' mode")
    logger.info(f"Keywords: {config.SEARCH_KEYWORDS}")

    # Step 1: Collect
    posts = collect_data(mode=args.mode)
    if not posts:
        logger.warning("No posts collected. Check your API credentials in config.py.")
        db.close()
        return

    # Step 2: Analyze
    engine  = SentimentEngine()
    results = analyze_posts(posts, engine)

    # Step 3: Save
    if not args.no_save:
        save_results(posts, results, db, exporter)
    else:
        logger.info("--no-save flag set: skipping database/CSV storage")

    # Step 4: Report
    print_report(db, results)

    db.close()
    logger.info("Pipeline complete.")


if __name__ == "__main__":
    main()
