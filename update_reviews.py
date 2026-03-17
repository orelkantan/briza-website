#!/usr/bin/env python3
"""
update_reviews.py (Accumulative Version)
----------------------------------------
מושך ביקורות מ-Google Places API, ממזג אותן עם ביקורות קיימות (כדי לא לאבד מידע),
ומעדכן את קובץ ה-HTML אוטומטית.
"""

import os
import re
import sys
import json
import hashlib
import requests
from datetime import datetime

# ── הגדרות ──────────────────────────────────────────────────────────────────
HTML_FILE     = "index.html"           # שם קובץ האתר
REVIEWS_CACHE = ".reviews_cache.json"    # קאש ששומר את כל הביקורות אי פעם

# ── עזרים ───────────────────────────────────────────────────────────────────
def relative_time_he(unix_ts: int) -> str:
    now   = datetime.utcnow().timestamp()
    diff  = int(now - unix_ts)
    days  = diff // 86400
    if days < 1: return "היום"
    if days < 7: return f"לפני {days} ימים" if days > 1 else "לפני יום"
    if days < 14: return "לפני שבוע"
    if days < 30:
        weeks = days // 7
        return f"לפני {weeks} שבועות"
    if days < 60: return "לפני חודש"
    if days < 365:
        months = days // 30
        return f"לפני {months} חודשים"
    years = days // 365
    return f"לפני {years} שנה" if years == 1 else f"לפני {years} שנים"

def stars_html(rating: int) -> str:
    return "★" * rating + "☆" * (5 - rating)

def avatar_letter(name: str) -> str:
    name = name.strip()
    return name[0].upper() if name else "?"

def fetch_reviews(api_key: str, place_id: str) -> dict:
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "name,rating,user_ratings_total,reviews",
        "language": "iw",
        "reviews_sort": "newest",
        "key": api_key,
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != "OK":
        raise RuntimeError(f"Places API error: {data.get('status')}")
    return data["result"]

def build_review_card(review: dict, first: bool = False) -> str:
    rating   = int(review.get("rating", 5))
    text     = review.get("text", "").replace("<", "&lt;").replace(">", "&gt;")
    author   = review.get("author_name", "לקוח")
    ts       = review.get("time", 0)
    rel_time = relative_time_he(ts)
    avatar   = avatar_letter(author)
    stars    = stars_html(rating)
    active   = ' active-slide' if first else ''

    return f"""        <div class="review-card{active}">
          <div class="review-stars">{stars}</div>
          <p class="review-text">{text}</p>
          <div class="reviewer">
            <div class="reviewer-avatar">{avatar}</div>
            <div><div class="reviewer-name">{author}</div><div class="reviewer-loc">Google ⭐ {rel_time}</div></div>
          </div>
        </div>"""

def build_carousel_html(reviews: list) -> str:
    cards = [build_review_card(r, i == 0) for i, r in enumerate(reviews)]
    return "\n".join(cards)

def calculate_hash(reviews: list) -> str:
    """יוצר מזהה ייחודי למצב הנוכחי של כל הביקורות"""
    key = json.dumps(
        [{"id": r.get("author_name","") + str(r.get("time",0))} for r in reviews],
        ensure_ascii=False, sort_keys=True
    )
    return hashlib.md5(key.encode()).hexdigest()

def load_data():
    """טוען את כל ההיסטוריה מהקובץ"""
    if os.path.exists(REVIEWS_CACHE):
        with open(REVIEWS_CACHE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"hash": "", "all_reviews": []}

def save_data(h: str, all_reviews: list):
    """שומר את המאגר המעודכן"""
    with open(REVIEWS_CACHE, "w", encoding="utf-8") as f:
        json.dump({
            "hash": h, 
            "updated": datetime.utcnow().isoformat(),
            "all_reviews": all_reviews
        }, f, ensure_ascii=False, indent=2)

def update_html(html_path: str, reviews: list, place_data: dict):
    with open(html_path, encoding="utf-8") as f:
        content = f.read()

    # עדכון הביקורות
    new_cards = build_carousel_html(reviews)
    content = re.sub(
        r".*?",
        f"\n{new_cards}\n        ",
        content, flags=re.DOTALL
    )

    # עדכון ציון ומספר ביקורות
    avg_rating = place_data.get("rating", 0)
    total_reviews = place_data.get("user_ratings_total", len(reviews))
    
    content = re.sub(r'(<div class="rating-num">)[^<]+(</div>)', rf'\1{avg_rating}\2', content)
    content = re.sub(r'מבוסס על \d+ ביקורות[^<]*', f'מבוסס על {total_reviews} ביקורות בגוגל', content)

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(content)

# ── Main Logic ──────────────────────────────────────────────────────────────
def main():
    api_key = os.environ.get("GOOGLE_API_KEY", "").strip()
    place_id = os.environ.get("PLACE_ID", "").strip()

    if not api_key or not place_id:
        print("❌ חסרים משתני סביבה.")
        sys.exit(1)

    # 1. משיכת נתונים חדשים מגוגל
    print(f"🔍 מושך ביקורות אחרונות מגוגל...")
    place_data = fetch_reviews(api_key, place_id)
    new_from_google = place_data.get("reviews", [])

    # 2. טעינת המאגר הקיים (הארכיון)
    stored_data = load_data()
    all_reviews = stored_data.get("all_reviews", [])

    # 3. מיזוג - הוספת רק כאלו שלא קיימות
    existing_ids = {f"{r.get('author_name')}_{r.get('time')}" for r in all_reviews}
    added_count = 0
    for r in new_from_google:
        r_id = f"{r.get('author_name')}_{r.get('time')}"
        if r_id not in existing_ids:
            all_reviews.append(r)
            added_count += 1

    # 4. מיון מהחדש לישן
    all_reviews.sort(key=lambda x: x.get("time", 0), reverse=True)

    # 5. בדיקה אם יש צורך בעדכון
    new_hash = calculate_hash(all_reviews)
    if new_hash == stored_data.get("hash"):
        print("ℹ️ אין ביקורות חדשות להוסיף.")
        sys.exit(0)

    # 6. שמירה ועדכון
    print(f"🆕 נוספו {added_count} ביקורות חדשות. סה"כ בארכיון: {len(all_reviews)}")
    update_html(HTML_FILE, all_reviews, place_data)
    save_data(new_hash, all_reviews)
    print("🎉 העדכון הושלם בהצלחה!")

if __name__ == "__main__":
    main()
