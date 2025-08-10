import os
import json
import random
from datetime import datetime, timezone
import tweepy

# ======= Settings =======
POSTING_WINDOW = (9, 21)                      # UTC hours [start, end]
FORCE_POST = os.getenv("FORCE_POST", "0") == "1"
QUOTES_FILE = "quotes.json"
# ========================

# --- OAuth 1.0a (v1.1) — most reliable for posting ---
API_KEY       = os.environ["X_API_KEY"]
API_SECRET    = os.environ["X_API_SECRET"]
ACCESS_TOKEN  = os.environ["X_ACCESS_TOKEN"]
ACCESS_SECRET = os.environ["X_ACCESS_SECRET"]

auth = tweepy.OAuth1UserHandler(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET)
api = tweepy.API(auth)

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
                q = item.strip()
                if q: quotes.append(q)
            elif isinstance(item, dict):
                text = (item.get("text") or "").strip()
                author = (item.get("author") or "").strip()
                if text and author:
                    quotes.append(f"“{text}” — {author}")
                elif text:
                    quotes.append(text)
    return [q for q in quotes if q]

def pick_quote() -> str:
    qs = load_quotes(QUOTES_FILE)
    if not qs:
        raise RuntimeError("No quotes found in quotes.json")
    return random.choice(qs)

def verify_auth():
    """Log which account we're posting as; helpful for debugging."""
    me = api.verify_credentials()
    if me:
        print(f"Authenticated as @{me.screen_name} (id={me.id})")
    else:
        print("Warning: could not verify credentials")

def post_tweet(text: str):
    status = api.update_status(status=text)
    print(f"Tweeted id={status.id} text={text}")

def main():
    verify_auth()

    if not within_window():
        print(f"Outside posting window {POSTING_WINDOW}, skipping.")
        return

    quote = pick_quote()
    try:
        post_tweet(quote)
    except tweepy.TweepError as e:
        # Show server response if available
        resp = getattr(e, "response", None)
        code = getattr(resp, "status_code", None)
        body = getattr(resp, "text", None)
        print(f"Post failed: {code} {e}\n{body or ''}")
        raise

if __name__ == "__main__":
    main()
