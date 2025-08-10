import os
import json
import random
from datetime import datetime, timezone

import tweepy

# ======= Settings you can tweak =======
POSTING_WINDOW = (9, 21)          # UTC hours [start, end] allowed to post
FORCE_POST = os.getenv("FORCE_POST", "0") == "1"   # set to "1" in workflow env to force a test post
QUOTES_FILE = "quotes.json"
# ======================================

# --- Twitter auth (OAuth 1.0a user context; required for posting) ---
API_KEY        = os.environ["X_API_KEY"]
API_SECRET     = os.environ["X_API_SECRET"]
ACCESS_TOKEN   = os.environ["X_ACCESS_TOKEN"]
ACCESS_SECRET  = os.environ["X_ACCESS_SECRET"]

client = tweepy.Client(
    consumer_key=API_KEY,
    consumer_secret=API_SECRET,
    access_token=ACCESS_TOKEN,
    access_token_secret=ACCESS_SECRET,
)

def utc_hour() -> int:
    return datetime.now(timezone.utc).hour

def within_window() -> bool:
    if FORCE_POST:
        return True
    start, end = POSTING_WINDOW
    h = utc_hour()
    return start <= h <= end

def load_quotes(path: str):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    quotes = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, str):
                quotes.append(item.strip())
            elif isinstance(item, dict):
                text = (item.get("text") or "").strip()
                author = (item.get("author") or "").strip()
                if text and author:
                    quotes.append(f"“{text}” — {author}")
                elif text:
                    quotes.append(text)
    return [q for q in quotes if q]

def pick_quote() -> str:
    quotes = load_quotes(QUOTES_FILE)
    if not quotes:
        raise RuntimeError("No quotes found in quotes.json")
    return random.choice(quotes)

def post_tweet(text: str):
    resp = client.create_tweet(text=text)
    tid = resp.data.get("id") if (resp and resp.data) else None
    print(f"Tweeted id={tid} text={text}")

def main():
    if not within_window():
        print(f"Outside posting window {POSTING_WINDOW}, skipping.")
        return

    quote = pick_quote()
    try:
        post_tweet(quote)
    except tweepy.TweepyException as e:
        # surface useful details in the Actions log
        status = getattr(e, "response", None)
        code = getattr(status, "status_code", None)
        text = getattr(status, "text", None)
        print(f"Post failed: {code} {e}\n{(text or '')}")
        raise

if __name__ == "__main__":
    main()
