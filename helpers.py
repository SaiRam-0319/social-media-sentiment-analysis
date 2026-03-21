# =============================================================================
#  utils/helpers.py — Logging, Text Preprocessing, Shared Utilities
# =============================================================================

import re
import os
import sys
import logging
import unicodedata
from datetime import datetime

import nltk
import emoji
import contractions
from colorama import init, Fore, Style

init(autoreset=True)  # Colorama init

# Download NLTK data once
def download_nltk_data():
    packages = ["stopwords", "punkt", "wordnet", "averaged_perceptron_tagger"]
    for pkg in packages:
        try:
            nltk.data.find(f"tokenizers/{pkg}")
        except LookupError:
            nltk.download(pkg, quiet=True)

download_nltk_data()
from nltk.corpus import stopwords

STOP_WORDS = set(stopwords.words("english"))
# Keep negations — they flip sentiment
NEGATIONS = {"no", "not", "never", "none", "neither", "nor", "nobody",
             "nothing", "nowhere", "hardly", "barely", "scarcely"}
STOP_WORDS -= NEGATIONS

# Internet slang dictionary
SLANG_MAP = {
    "lol": "laughing out loud", "omg": "oh my god", "wtf": "what the",
    "smh": "shaking my head", "imo": "in my opinion", "tbh": "to be honest",
    "ngl": "not gonna lie", "irl": "in real life", "fyi": "for your information",
    "brb": "be right back", "afk": "away from keyboard", "rn": "right now",
    "idk": "i do not know", "imo": "in my opinion", "imho": "in my humble opinion",
    "gr8": "great", "luv": "love", "thx": "thanks", "pls": "please",
    "u": "you", "ur": "your", "r": "are", "b4": "before", "2": "to",
    "4": "for", "cya": "see you", "wyd": "what are you doing",
    "slay": "excellent", "lowkey": "somewhat", "highkey": "very much",
    "lit": "exciting", "fire": "excellent", "goat": "greatest of all time",
}


# ─────────────────────────────────────────────
#  LOGGER
# ─────────────────────────────────────────────
def setup_logger(name: str, log_file: str = None, level: str = "INFO") -> logging.Logger:
    """Set up a colored console + optional file logger."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if logger.handlers:
        return logger  # Already configured

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # File handler
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    return logger


# ─────────────────────────────────────────────
#  TEXT PREPROCESSING
# ─────────────────────────────────────────────
def clean_text(text: str, keep_stopwords: bool = False) -> str:
    """
    Full preprocessing pipeline for social media text.
    Steps: decode → URLs → mentions → hashtags → HTML → emojis →
           contractions → slang → lowercase → punctuation → stopwords → collapse
    """
    if not text or not isinstance(text, str):
        return ""

    # 1. Unicode normalization
    text = unicodedata.normalize("NFKC", text)

    # 2. Remove URLs
    text = re.sub(r"http\S+|www\.\S+", "[URL]", text, flags=re.IGNORECASE)

    # 3. Replace @mentions
    text = re.sub(r"@\w+", "[USER]", text)

    # 4. Handle hashtags — keep the word, remove the #
    text = re.sub(r"#(\w+)", r"\1", text)

    # 5. Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # 6. Convert emojis to text tokens
    text = emoji.demojize(text, delimiters=(" ", " "))
    text = re.sub(r"_", " ", text)  # e.g., :smiling_face: → smiling face

    # 7. Expand contractions  (don't → do not)
    try:
        text = contractions.fix(text)
    except Exception:
        pass

    # 8. Expand slang
    words = text.split()
    words = [SLANG_MAP.get(w.lower(), w) for w in words]
    text = " ".join(words)

    # 9. Lowercase
    text = text.lower()

    # 10. Remove special characters (keep letters, numbers, spaces, basic punctuation)
    text = re.sub(r"[^a-z0-9\s\.,!?']", " ", text)

    # 11. Collapse multiple spaces
    text = re.sub(r"\s+", " ", text).strip()

    # 12. Remove stopwords (optional)
    if not keep_stopwords:
        tokens = text.split()
        tokens = [t for t in tokens if t not in STOP_WORDS or t in NEGATIONS]
        text = " ".join(tokens)

    return text


def detect_language(text: str) -> str:
    """Detect language of text. Returns ISO code (e.g., 'en')."""
    try:
        from langdetect import detect
        return detect(text)
    except Exception:
        return "unknown"


def truncate_text(text: str, max_len: int = 512) -> str:
    """Truncate text for transformer models with token limits."""
    words = text.split()
    if len(words) > max_len:
        return " ".join(words[:max_len])
    return text


def format_timestamp(ts=None) -> str:
    """Return ISO-formatted UTC timestamp."""
    if ts is None:
        return datetime.utcnow().isoformat()
    if isinstance(ts, (int, float)):
        return datetime.utcfromtimestamp(ts).isoformat()
    if isinstance(ts, datetime):
        return ts.isoformat()
    return str(ts)


def print_banner():
    """Print a styled startup banner."""
    banner = f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════╗
║   {Fore.YELLOW}Social Media Sentiment Analysis System{Fore.CYAN}             ║
║   {Fore.WHITE}Version 1.0  |  Multi-Platform  |  Ensemble NLP{Fore.CYAN}     ║
╚══════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
    print(banner)


def print_result_table(results: list):
    """Pretty-print results to terminal."""
    from tabulate import tabulate
    if not results:
        print(Fore.RED + "No results to display.")
        return

    rows = []
    for r in results:
        sentiment = r.get("sentiment", "neutral")
        color = Fore.GREEN if sentiment == "positive" else (Fore.RED if sentiment == "negative" else Fore.YELLOW)
        rows.append([
            r.get("platform", ""),
            (r.get("text", "")[:60] + "...") if len(r.get("text", "")) > 60 else r.get("text", ""),
            color + sentiment.upper() + Style.RESET_ALL,
            f"{r.get('confidence', 0):.2f}",
            r.get("emotion", ""),
            r.get("timestamp", ""),
        ])

    headers = ["Platform", "Text", "Sentiment", "Confidence", "Emotion", "Timestamp"]
    print(tabulate(rows, headers=headers, tablefmt="rounded_outline"))
