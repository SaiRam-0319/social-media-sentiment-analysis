# =============================================================================
#  models/sentiment_model.py — Full Ensemble Sentiment Analysis Engine
#  Combines VADER + TextBlob + HuggingFace Transformer
# =============================================================================

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import re
from dataclasses import dataclass, field
from typing import Optional

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from textblob import TextBlob
from utils.helpers import setup_logger, clean_text, truncate_text
import config

logger = setup_logger("SentimentModel", config.LOG_FILE, config.LOG_LEVEL)

# ─────────────────────────────────────────────
#  RESULT DATACLASS
# ─────────────────────────────────────────────
@dataclass
class SentimentResult:
    post_id:         str
    platform:        str
    text:            str
    cleaned_text:    str
    sentiment:       str          # "positive" | "negative" | "neutral"
    confidence:      float        # 0.0 – 1.0
    scores:          dict = field(default_factory=dict)   # {positive, negative, neutral}
    emotion:         str = "neutral"
    emotion_scores:  dict = field(default_factory=dict)
    keywords:        list = field(default_factory=list)
    vader_score:     float = 0.0
    textblob_score:  float = 0.0
    transformer_sentiment: str = "neutral"
    transformer_score:     float = 0.0
    model_version:   str = "ensemble-v1.0"
    timestamp:       str = ""
    language:        str = "en"
    author:          str = ""
    engagement:      dict = field(default_factory=dict)
    keyword:         str = ""

    def to_dict(self) -> dict:
        return {
            "post_id":          self.post_id,
            "platform":         self.platform,
            "text":             self.text,
            "cleaned_text":     self.cleaned_text,
            "sentiment":        self.sentiment,
            "confidence":       round(self.confidence, 4),
            "score_positive":   round(self.scores.get("positive", 0), 4),
            "score_negative":   round(self.scores.get("negative", 0), 4),
            "score_neutral":    round(self.scores.get("neutral", 0), 4),
            "emotion":          self.emotion,
            "vader_score":      round(self.vader_score, 4),
            "textblob_score":   round(self.textblob_score, 4),
            "transformer_sentiment": self.transformer_sentiment,
            "transformer_score":    round(self.transformer_score, 4),
            "keywords":         ", ".join(self.keywords),
            "model_version":    self.model_version,
            "timestamp":        self.timestamp,
            "language":         self.language,
            "author":           self.author,
            "keyword":          self.keyword,
            "likes":            self.engagement.get("likes", 0),
            "shares":           self.engagement.get("retweets", self.engagement.get("upvotes", 0)),
        }


# ─────────────────────────────────────────────
#  VADER ANALYZER
# ─────────────────────────────────────────────
class VADERAnalyzer:
    """Rule-based sentiment using VADER. Best for short social media text."""

    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()
        logger.info("VADER analyzer initialized.")

    def analyze(self, text: str) -> dict:
        """
        Returns: {compound, pos, neg, neu, sentiment, confidence}
        compound: -1.0 (most negative) to +1.0 (most positive)
        """
        scores = self.analyzer.polarity_scores(text)
        compound = scores["compound"]

        if compound >= 0.05:
            sentiment = "positive"
            confidence = (compound + 1) / 2   # Map to [0.5, 1.0]
        elif compound <= -0.05:
            sentiment = "negative"
            confidence = (-compound + 1) / 2
        else:
            sentiment = "neutral"
            confidence = 1 - abs(compound) * 2  # Higher near 0

        return {
            "compound":   compound,
            "positive":   scores["pos"],
            "negative":   scores["neg"],
            "neutral":    scores["neu"],
            "sentiment":  sentiment,
            "confidence": confidence,
        }


# ─────────────────────────────────────────────
#  TEXTBLOB ANALYZER
# ─────────────────────────────────────────────
class TextBlobAnalyzer:
    """
    TextBlob sentiment analysis.
    polarity: -1 (negative) to +1 (positive)
    subjectivity: 0 (objective) to 1 (subjective)
    """

    def __init__(self):
        logger.info("TextBlob analyzer initialized.")

    def analyze(self, text: str) -> dict:
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        subjectivity = blob.sentiment.subjectivity

        if polarity > 0.1:
            sentiment = "positive"
        elif polarity < -0.1:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        confidence = (abs(polarity) + 0.5) / 1.5  # Normalize to [0.33, 1.0]

        return {
            "polarity":     polarity,
            "subjectivity": subjectivity,
            "sentiment":    sentiment,
            "confidence":   confidence,
        }


# ─────────────────────────────────────────────
#  TRANSFORMER ANALYZER
# ─────────────────────────────────────────────
class TransformerAnalyzer:
    """
    HuggingFace transformer-based sentiment classifier.
    Downloads the model on first run (~250–500 MB depending on model).
    """

    LABEL_MAP = {
        # cardiffnlp/twitter-roberta-base-sentiment-latest
        "LABEL_0": "negative",
        "LABEL_1": "neutral",
        "LABEL_2": "positive",
        # distilbert
        "NEGATIVE": "negative",
        "POSITIVE": "positive",
        # nlptown star ratings
        "1 star": "negative",
        "2 stars": "negative",
        "3 stars": "neutral",
        "4 stars": "positive",
        "5 stars": "positive",
    }

    def __init__(self):
        self.pipeline = None
        self._load_model()

    def _load_model(self):
        try:
            from transformers import pipeline as hf_pipeline
            logger.info(f"Loading transformer model: {config.TRANSFORMER_MODEL_NAME}")
            logger.info("(First run will download the model — this may take a few minutes)")
            self.pipeline = hf_pipeline(
                "text-classification",
                model=config.TRANSFORMER_MODEL_NAME,
                top_k=None,        # Return scores for ALL labels
                truncation=True,
                max_length=512,
            )
            logger.info("Transformer model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load transformer model: {e}")
            logger.warning("Transformer inference will be skipped. Using VADER+TextBlob only.")
            self.pipeline = None

    def analyze(self, text: str) -> dict:
        if not self.pipeline:
            return {"sentiment": "neutral", "confidence": 0.5,
                    "positive": 0.33, "negative": 0.33, "neutral": 0.34}

        try:
            # Truncate to 512 words to stay within token limits
            text = truncate_text(text, max_len=400)
            raw = self.pipeline(text)
            # raw is a list of lists: [[{label, score}, ...]]
            label_scores = raw[0] if raw else []

            # Normalize labels
            scores = {}
            for item in label_scores:
                label = self.LABEL_MAP.get(item["label"], item["label"].lower())
                scores[label] = scores.get(label, 0) + item["score"]

            # Ensure all three keys exist
            for key in ("positive", "negative", "neutral"):
                scores.setdefault(key, 0.0)

            best_label = max(scores, key=scores.get)
            confidence = scores[best_label]

            return {
                "sentiment":  best_label,
                "confidence": confidence,
                "positive":   scores["positive"],
                "negative":   scores["negative"],
                "neutral":    scores["neutral"],
            }
        except Exception as e:
            logger.error(f"Transformer inference error: {e}")
            return {"sentiment": "neutral", "confidence": 0.5,
                    "positive": 0.33, "negative": 0.33, "neutral": 0.34}


# ─────────────────────────────────────────────
#  EMOTION DETECTOR
# ─────────────────────────────────────────────
class EmotionDetector:
    """
    Lightweight lexicon-based emotion detection.
    Maps text to one of: joy, anger, fear, sadness, disgust, surprise, neutral.
    """

    EMOTION_LEXICON = {
        "joy":      ["happy", "joy", "love", "great", "wonderful", "amazing", "excited",
                     "fantastic", "awesome", "delighted", "thrilled", "elated", "cheerful",
                     "pleased", "glad", "celebrate", "yay", "woohoo", "brilliant", "excellent"],
        "anger":    ["angry", "furious", "hate", "rage", "mad", "annoyed", "frustrated",
                     "outraged", "disgusted", "infuriated", "livid", "irritated", "hostile",
                     "enraged", "bitter", "resentful", "awful", "terrible", "horrible"],
        "fear":     ["afraid", "scared", "fear", "terrified", "anxious", "worried", "nervous",
                     "panic", "dread", "horror", "frightened", "uneasy", "apprehensive",
                     "alarmed", "concerned", "threatened", "danger", "risk"],
        "sadness":  ["sad", "unhappy", "depressed", "miserable", "heartbroken", "grief",
                     "sorrow", "disappointed", "hopeless", "lonely", "cry", "tears",
                     "devastated", "gloomy", "melancholy", "upset", "hurt", "lost"],
        "disgust":  ["disgusting", "gross", "nasty", "revolting", "repulsive", "sick",
                     "yuck", "vile", "awful", "horrible", "despicable", "repugnant"],
        "surprise": ["surprised", "shocked", "astonished", "amazed", "unexpected",
                     "unbelievable", "wow", "whoa", "omg", "incredible", "stunned",
                     "startled", "astounded"],
    }

    def detect(self, text: str) -> tuple:
        """Returns (emotion_label, emotion_scores_dict)."""
        text_lower = text.lower()
        word_set = set(re.findall(r"\b\w+\b", text_lower))

        scores = {}
        for emotion, keywords in self.EMOTION_LEXICON.items():
            matches = word_set.intersection(set(keywords))
            scores[emotion] = len(matches)

        total = sum(scores.values())
        if total == 0:
            return "neutral", {e: 0.0 for e in self.EMOTION_LEXICON}

        # Normalize
        norm_scores = {e: round(s / total, 4) for e, s in scores.items()}
        best_emotion = max(scores, key=scores.get)
        return best_emotion, norm_scores


# ─────────────────────────────────────────────
#  KEYWORD EXTRACTOR
# ─────────────────────────────────────────────
class KeywordExtractor:
    """Simple TF-based keyword extractor (no stopwords, high frequency words)."""

    def extract(self, text: str, top_n: int = 5) -> list:
        from collections import Counter
        words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())
        # Filter basic stopwords inline
        ignore = {"this", "that", "with", "have", "from", "they", "will",
                  "been", "were", "what", "when", "your", "more", "also",
                  "user", "just", "about", "their", "there", "would"}
        words = [w for w in words if w not in ignore]
        counter = Counter(words)
        return [w for w, _ in counter.most_common(top_n)]


# ─────────────────────────────────────────────
#  ENSEMBLE SENTIMENT ENGINE
# ─────────────────────────────────────────────
class SentimentEngine:
    """
    Main sentiment engine. Runs VADER, TextBlob, and Transformer in parallel
    (sequentially for simplicity) and combines results using weighted voting.
    """

    def __init__(self, mode: str = None):
        self.mode = mode or config.SENTIMENT_MODEL
        self.weights = config.ENSEMBLE_WEIGHTS

        logger.info(f"Initializing SentimentEngine in '{self.mode}' mode...")

        self.vader       = VADERAnalyzer()
        self.textblob    = TextBlobAnalyzer()
        self.emotion_det = EmotionDetector()
        self.kw_extractor = KeywordExtractor()

        self.transformer = None
        if self.mode in ("transformer", "ensemble"):
            self.transformer = TransformerAnalyzer()

        logger.info("SentimentEngine ready.")

    def _ensemble_vote(self, vader_result: dict, tb_result: dict,
                       tr_result: dict) -> tuple:
        """
        Weighted average of sentiment probabilities across all three models.
        Returns (sentiment_label, confidence, scores_dict).
        """
        w_v = self.weights["vader"]
        w_t = self.weights["textblob"]
        w_r = self.weights["transformer"] if self.transformer else 0.0

        # Normalize weights if transformer is absent
        if not self.transformer:
            total = w_v + w_t
            w_v /= total
            w_t /= total

        def to_probs(result: dict) -> dict:
            """Convert a model result to {positive, negative, neutral} probabilities."""
            if "positive" in result:
                return {
                    "positive": result["positive"],
                    "negative": result["negative"],
                    "neutral":  result.get("neutral", 0),
                }
            # VADER style — use compound to infer
            c = result.get("compound", result.get("polarity", 0))
            pos = max(0, c)
            neg = max(0, -c)
            neu = 1 - abs(c)
            total = pos + neg + neu or 1
            return {"positive": pos / total, "negative": neg / total, "neutral": neu / total}

        vp = to_probs(vader_result)
        tp = to_probs(tb_result)
        rp = to_probs(tr_result) if tr_result else {"positive": 0, "negative": 0, "neutral": 0}

        combined = {}
        for label in ("positive", "negative", "neutral"):
            combined[label] = (
                w_v * vp[label] +
                w_t * tp[label] +
                w_r * rp.get(label, 0)
            )

        # Normalize so scores sum to 1.0
        total = sum(combined.values()) or 1
        combined = {k: v / total for k, v in combined.items()}

        best = max(combined, key=combined.get)
        return best, combined[best], combined

    def analyze(self, post: dict) -> SentimentResult:
        """
        Analyze a single post dictionary.
        post must have at least: post_id, platform, text, timestamp
        """
        raw_text = post.get("text", "")
        if not raw_text.strip():
            return SentimentResult(
                post_id=post.get("post_id", ""),
                platform=post.get("platform", ""),
                text=raw_text,
                cleaned_text="",
                sentiment="neutral",
                confidence=0.5,
            )

        # Preprocess
        cleaned = clean_text(raw_text, keep_stopwords=True)

        # Run models
        vader_res = self.vader.analyze(raw_text)      # VADER works best on raw text
        tb_res    = self.textblob.analyze(cleaned)
        tr_res    = self.transformer.analyze(cleaned) if self.transformer else None

        # Choose output based on mode
        if self.mode == "vader":
            sentiment  = vader_res["sentiment"]
            confidence = vader_res["confidence"]
            scores = {"positive": vader_res["positive"],
                      "negative": vader_res["negative"],
                      "neutral":  vader_res["neutral"]}

        elif self.mode == "textblob":
            sentiment  = tb_res["sentiment"]
            confidence = tb_res["confidence"]
            p = max(0, tb_res["polarity"])
            n = max(0, -tb_res["polarity"])
            scores = {"positive": p, "negative": n, "neutral": 1 - abs(tb_res["polarity"])}

        elif self.mode == "transformer" and tr_res:
            sentiment  = tr_res["sentiment"]
            confidence = tr_res["confidence"]
            scores = {"positive": tr_res["positive"],
                      "negative": tr_res["negative"],
                      "neutral":  tr_res["neutral"]}

        else:  # ensemble
            sentiment, confidence, scores = self._ensemble_vote(vader_res, tb_res, tr_res)

        # Emotion + keywords
        emotion, emotion_scores = self.emotion_det.detect(raw_text)
        keywords = self.kw_extractor.extract(cleaned)

        return SentimentResult(
            post_id=post.get("post_id", ""),
            platform=post.get("platform", ""),
            text=raw_text,
            cleaned_text=cleaned,
            sentiment=sentiment,
            confidence=confidence,
            scores=scores,
            emotion=emotion,
            emotion_scores=emotion_scores,
            keywords=keywords,
            vader_score=vader_res["compound"],
            textblob_score=tb_res["polarity"],
            transformer_sentiment=tr_res["sentiment"] if tr_res else "n/a",
            transformer_score=tr_res["confidence"] if tr_res else 0.0,
            timestamp=post.get("timestamp", ""),
            language=post.get("language", "en"),
            author=post.get("username", ""),
            engagement=post.get("engagement", {}),
            keyword=post.get("keyword", ""),
        )

    def analyze_batch(self, posts: list, show_progress: bool = True) -> list:
        """Analyze a list of posts. Returns list of SentimentResult objects."""
        results = []
        total = len(posts)

        try:
            from tqdm import tqdm
            iterator = tqdm(posts, desc="Analyzing", unit="post") if show_progress else posts
        except ImportError:
            iterator = posts

        for i, post in enumerate(iterator):
            result = self.analyze(post)
            results.append(result)

            if show_progress and not hasattr(iterator, "update"):
                if (i + 1) % 10 == 0 or (i + 1) == total:
                    logger.info(f"Progress: {i + 1}/{total} posts analyzed")

        logger.info(f"Batch analysis complete: {len(results)} posts")
        return results


# ─────────────────────────────────────────────
#  Quick standalone test
# ─────────────────────────────────────────────
if __name__ == "__main__":
    engine = SentimentEngine(mode="vader")  # Use "vader" for fast test without transformer

    test_posts = [
        {"post_id": "t1", "platform": "Twitter", "text": "I absolutely love this product! Best purchase ever! 😍", "timestamp": "", "language": "en"},
        {"post_id": "t2", "platform": "Reddit", "text": "This is the worst experience I have ever had. Complete waste of money.", "timestamp": "", "language": "en"},
        {"post_id": "t3", "platform": "YouTube", "text": "It's okay I guess, nothing special.", "timestamp": "", "language": "en"},
    ]

    results = engine.analyze_batch(test_posts)
    for r in results:
        print(f"[{r.platform}] {r.sentiment.upper()} ({r.confidence:.2f}) | {r.emotion} | {r.text[:60]}")
