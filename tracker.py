import requests
from bs4 import BeautifulSoup
import re
import os
import json
import time

# ─── CONFIG ───────────────────────────────────────────────
KEYWORDS = ["india's got latent", "samay raina", "latent", "igl"]

CITIES = ["mumbai", "delhi", "bangalore", "pune", "hyderabad", "chennai"]

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

SEEN_FILE = "seen_events.json"
# ──────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    return set()


def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)


def scrape_city(city):
    url = f"https://www.district.in/events/{city}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        res.raise_for_status()
    except Exception as e:
        print(f"  ⚠️  Could not fetch {city}: {e}")
        return []

    soup = BeautifulSoup(res.text, "html.parser")

    # Grab all anchor tags that look like event pages
    links = soup.find_all("a", href=re.compile(r"/events/.+-buy-tickets"))

    found = []
    for link in links:
        title = link.get_text(" ", strip=True)
        href = link["href"]
        full_url = "https://www.district.in" + href

        if any(kw in title.lower() for kw in KEYWORDS):
            found.append({"title": title, "url": full_url, "city": city})

    return found


def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("  ℹ️  Telegram not configured, skipping notification.")
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
            },
            timeout=10,
        )
        print("  ✅  Telegram notification sent!")
    except Exception as e:
        print(f"  ⚠️  Telegram error: {e}")


def main():
    print(f"\n🔍 District Tracker started — {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Keywords : {', '.join(KEYWORDS)}")
    print(f"   Cities   : {', '.join(CITIES)}\n")

    seen = load_seen()
    new_events = []

    for city in CITIES:
        print(f"  Checking {city}...")
        matches = scrape_city(city)
        for event in matches:
            if event["url"] not in seen:
                seen.add(event["url"])
                new_events.append(event)
                print(f"  🚨 NEW: {event['title']}")
                print(f"         {event['url']}")
            else:
                print(f"  ✓  Already seen: {event['title']}")
        time.sleep(2)  # be polite between requests

    if new_events:
        for event in new_events:
            message = (
                f"🎭 <b>New India's Got Latent Event on District!</b>\n\n"
                f"📌 <b>{event['title']}</b>\n"
                f"📍 City: {event['city'].title()}\n"
                f"🎟️ <a href='{event['url']}'>Book on District →</a>"
            )
            send_telegram(message)
    else:
        print("\n  No new events found this run.")

    save_seen(seen)
    print(f"\n✅ Done — {len(seen)} total events tracked so far.")


if __name__ == "__main__":
    main()
