import os, json, random, datetime as dt
from pathlib import Path
import tweepy

MAX_PER_DAY = 5
STATE = Path("state.json")
QUOTES = Path("quotes.json")
MAX_TWEET = 280
POSTING_WINDOW = (9, 21)  # UTC hours [9:00, 21:59]

def now_utc():
    return dt.datetime.utcnow()

def local_hour_from_offset(offset_minutes=0):
    return now_utc().hour

def load_quotes():
    data = json.loads(QUOTES.read_text(encoding="utf-8"))
    data = [q.strip() for q in data if q and len(q.strip()) <= MAX_TWEET]
    if not data:
        raise RuntimeError("quotes.json is empty or all entries >280 chars.")
    return data

def load_state():
    if STATE.exists():
        try:
            return json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"date": None, "used_indices": [], "count_today": 0}

def save_state(s):
    STATE.write_text(json.dumps(s), encoding="utf-8")

def rotate_quote(quotes, used):
    if len(used) >= len(quotes):
        used.clear()
    remaining = [i for i in range(len(quotes)) if i not in used]
    idx = random.choice(remaining)
    used.add(idx)
    return idx, quotes[idx]

def within_window():
    h = local_hour_from_offset()
    return POSTING_WINDOW[0] <= h <= POSTING_WINDOW[1]

def should_post_this_run(count_today, runs_left_today):
    needed = MAX_PER_DAY - count_today
    if needed <= 0 or runs_left_today <= 0:
        return False
    p = needed / runs_left_today
    p = min(0.85, max(0.05, p))
    return random.random() < p

def runs_left_today():
    h = local_hour_from_offset()
    start, end = POSTING_WINDOW
    if h < start: return (end - start + 1)
    if h > end:   return 0
    return end - h + 1

def post(text):
    client = tweepy.Client(
        bearer_token=os.environ["X_BEARER_TOKEN"],
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_SECRET"],
    )
    return client.create_tweet(text=text)

def maybe_humanize(text):
    tags = ["", " ✨", " 🌟", " — a reminder", " — wise words", " • keep going"]
    suffix = random.choice(tags) if random.random() < 0.3 else ""
    out = (text + suffix).strip()
    return out if len(out) <= MAX_TWEET else text

def main():
    today = now_utc().date().isoformat()
    quotes = load_quotes()
    state = load_state()

    if state.get("date") != today:
        state = {"date": today, "used_indices": [], "count_today": 0}

    if not within_window():
        print("Outside posting window; skipping.")
        save_state(state)
        return

    left = runs_left_today()
    if not should_post_this_run(state["count_today"], left):
        print(f"Skipping this run. Posted so far: {state['count_today']}/{MAX_PER_DAY}.")
        save_state(state)
        return

    used_set = set(state["used_indices"])
    idx, q = rotate_quote(quotes, used_set)
    q = maybe_humanize(q)

    try:
        resp = post(q)
        used_set.add(idx)
        state["used_indices"] = list(used_set)
        state["count_today"] += 1
        print(f"Tweeted ({state['count_today']}/{MAX_PER_DAY}): {q}")
    except Exception as e:
        print(f"Post failed: {e}")
    finally:
        save_state(state)

if __name__ == "__main__":
    main()
