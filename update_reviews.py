#!/usr/bin/env python3
"""
update_reviews.py
-----------------
מושך ביקורות מ-Google Places API ומעדכן את קובץ ה-HTML של בריזה אוטומטית.
מריץ על-ידי GitHub Actions.

דרישות:
  pip install requests

משתני סביבה (GitHub Secrets):
  GOOGLE_API_KEY  — מפתח ה-API של גוגל
  PLACE_ID        — מזהה העסק בגוגל (מתחיל ב-ChIJ...)
"""

import os
import re
import sys
import json
import hashlib
import requests
from datetime import datetime

# ── הגדרות ──────────────────────────────────────────────────────────────────
HTML_FILE   = "index.html"          # שם קובץ האתר
REVIEWS_CACHE = ".reviews_cache.json"   # קאש לזיהוי שינויים

# ── עזרים ───────────────────────────────────────────────────────────────────
HEBREW_MONTHS = {
    1:"ינואר",2:"פברואר",3:"מרץ",4:"אפריל",5:"מאי",6:"יוני",
    7:"יולי",8:"אוגוסט",9:"ספטמבר",10:"אוקטובר",11:"נובמבר",12:"דצמבר"
}

def relative_time_he(unix_ts: int) -> str:
    """הופך timestamp לטקסט עברי יחסי: 'לפני 3 חודשים', 'לפני שבוע' וכו'"""
    now   = datetime.utcnow().timestamp()
    diff  = int(now - unix_ts)
    days  = diff // 86400
    if days < 1:
        return "היום"
    if days < 7:
        return f"לפני {days} ימים" if days > 1 else "לפני יום"
    if days < 14:
        return "לפני שבוע"
    if days < 30:
        weeks = days // 7
        return f"לפני {weeks} שבועות"
    if days < 60:
        return "לפני חודש"
    if days < 365:
        months = days // 30
        return f"לפני {months} חודשים"
    years = days // 365
    return f"לפני {years} שנה" if years == 1 else f"לפני {years} שנים"


def stars_html(rating: int) -> str:
    return "★" * rating + "☆" * (5 - rating)


def avatar_letter(name: str) -> str:
    """האות הראשונה של השם לאוואטר"""
    name = name.strip()
    return name[0].upper() if name else "?"


def fetch_reviews(api_key: str, place_id: str) -> dict:
    """מושך פרטי עסק + ביקורות מה-API"""
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "name,rating,user_ratings_total,reviews",
        "language": "iw",          # עברית
        "reviews_sort": "newest",
        "key": api_key,
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") != "OK":
        raise RuntimeError(f"Places API error: {data.get('status')} — {data.get('error_message','')}")

    return data["result"]


def build_review_card(review: dict, first: bool = False) -> str:
    """בונה HTML של קלף ביקורת בודד"""
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
    """בונה את כל כרטיסיות הביקורת"""
    cards = [build_review_card(r, i == 0) for i, r in enumerate(reviews)]
    return "\n".join(cards)


def reviews_hash(reviews: list) -> str:
    """חישוב hash לזיהוי שינויים"""
    key = json.dumps(
        [{"id": r.get("author_name","") + str(r.get("time",0)), "text": r.get("text","")}
         for r in reviews],
        ensure_ascii=False, sort_keys=True
    )
    return hashlib.md5(key.encode()).hexdigest()


def load_cache() -> str:
    if os.path.exists(REVIEWS_CACHE):
        with open(REVIEWS_CACHE) as f:
            return json.load(f).get("hash", "")
    return ""


def save_cache(h: str):
    with open(REVIEWS_CACHE, "w") as f:
        json.dump({"hash": h, "updated": datetime.utcnow().isoformat()}, f)


def update_html(html_path: str, reviews: list, place_data: dict):
    """
    מחליף את אזור הביקורות בתוך ה-HTML.
    מחפש את הסימנים:
        <!-- REVIEWS_START -->
        <!-- REVIEWS_END -->
    ומחליף את התוכן ביניהם.
    גם מעדכן את ציון הדירוג ומספר הביקורות בכותרת.
    """
    with open(html_path, encoding="utf-8") as f:
        content = f.read()

    # ── עדכון כרטיסיות הביקורת ──────────────────────────────────────────────
    new_cards = build_carousel_html(reviews)
    content = re.sub(
        r"<!-- REVIEWS_START -->.*?<!-- REVIEWS_END -->",
        f"<!-- REVIEWS_START -->\n{new_cards}\n        <!-- REVIEWS_END -->",
        content,
        flags=re.DOTALL
    )

    # ── עדכון ציון ומספר ביקורות ─────────────────────────────────────────────
    avg_rating   = place_data.get("rating", 0)
    total_reviews = place_data.get("user_ratings_total", len(reviews))

    # מחליף את מספר הדירוג (לדוגמה: >9.8<)
    content = re.sub(
        r'(<div class="rating-num">)[^<]+(</div>)',
        rf'\g<1>{avg_rating}\g<2>',
        content
    )
    # מחליף את שורת "מבוסס על X ביקורות"
    content = re.sub(
        r'מבוסס על \d+ ביקורות[^<]*',
        f'מבוסס על {total_reviews} ביקורות בגוגל',
        content
    )

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅  עודכן {html_path} — {len(reviews)} ביקורות, ציון {avg_rating}")


# ── main ─────────────────────────────────────────────────────────────────────
def main():
    api_key  = os.environ.get("GOOGLE_API_KEY", "").strip()
    place_id = os.environ.get("PLACE_ID", "").strip()

    if not api_key or not place_id:
        print("❌  חסרים משתני סביבה: GOOGLE_API_KEY ו-PLACE_ID")
        sys.exit(1)

    print(f"🔍  מושך ביקורות עבור place_id={place_id} ...")
    place_data = fetch_reviews(api_key, place_id)
    reviews    = place_data.get("reviews", [])

    if not reviews:
        print("⚠️   לא נמצאו ביקורות — מדלג על עדכון.")
        sys.exit(0)

    current_hash = reviews_hash(reviews)
    cached_hash  = load_cache()

    if current_hash == cached_hash:
        print("ℹ️   אין שינוי בביקורות — לא צריך עדכון.")
        sys.exit(0)

    print(f"🆕  נמצאו שינויים ({len(reviews)} ביקורות). מעדכן את {HTML_FILE} ...")
    update_html(HTML_FILE, reviews, place_data)
    save_cache(current_hash)
    print("🎉  סיום!")


if __name__ == "__main__":
    main()
