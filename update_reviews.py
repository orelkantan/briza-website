#!/usr/bin/env python3
import os
import re
import sys
import json
import hashlib
import requests
from datetime import datetime

HTML_FILE     = "index.html"
REVIEWS_CACHE = ".reviews_cache.json"

def relative_time_he(unix_ts: int) -> str:
    now  = datetime.utcnow().timestamp()
    diff = int(now - unix_ts)
    days = diff // 86400
    if days < 1:  return "היום"
    if days < 7:  return f"לפני {days} ימים" if days > 1 else "לפני יום"
    if days < 14: return "לפני שבוע"
    if days < 30:
        weeks = days // 7
        return f"לפני {weeks} שבועות"
    if days < 60:  return "לפני חודש"
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
    key = json.dumps(
        [{"id": r.get("author_name","") + str(r.get("time",0))} for r in reviews],
        ensure_ascii=False, sort_keys=True
    )
    return hashlib.md5(key.encode()).hexdigest()

def load_data():
    if os.path.exists(REVIEWS_CACHE):
        with open(REVIEWS_CACHE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"hash": "", "all_reviews": []}

def save_data(h: str, all_reviews: list):
    with open(REVIEWS_CACHE, "w", encoding="utf-8") as f:
        json.dump({
            "hash": h,
            "updated": datetime.utcnow().isoformat(),
            "all_reviews": all_reviews
        }, f, ensure_ascii=False, indent=2)

def update_html(html_path: str, reviews: list, place_data: dict):
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    # יצירת ה-HTML החדש של הכרטיסיות
    new_cards_html = build_carousel_html(reviews)
    
    # מנגנון החלפה בטוח: מחפש את הדיב ודואג להחליף את כל מה שבתוכו
    # המבנה: <div id="reviews-track"> ... תוכן ישן ... </div>
    pattern = r'(<div id="reviews-track"[^>]*>)(.*?)(</div>)'
    
    # החלפה תוך שמירה על התגיות הפותחות והסוגרות
    new_content = re.sub(pattern, r'\1\n' + new_cards_html + r'\n\3', content, flags=re.DOTALL)

    # עדכון נתוני דירוג כלליים (Rating)
    avg_rating = place_data.get("rating", 0)
    total_reviews = place_data.get("user_ratings_total", len(reviews))

    # עדכון המספר הגדול של הדירוג
    new_content = re.sub(
        r'(<div class="rating-num">)[^<]*(</div>)',
        r'\g<1>' + str(avg_rating) + r'\g<2>',
        new_content
    )
    
    # עדכון הטקסט של "מבוסס על X ביקורות"
    new_content = re.sub(
        r'מבוסס על \d+ ביקורות[^<]*',
        f'מבוסס על {total_reviews} ביקורות בגוגל',
        new_content
    )

    # כתיבה סופית לקובץ - דורס את הישן
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(new_content)

def main():
    api_key  = os.environ.get("GOOGLE_API_KEY", "").strip()
    place_id = os.environ.get("PLACE_ID", "").strip()

    if not api_key or not place_id:
        print("Missing env vars: GOOGLE_API_KEY / PLACE_ID")
        sys.exit(1)

    print("Fetching reviews from Google...")
    try:
        place_data = fetch_reviews(api_key, place_id)
        new_from_google = place_data.get("reviews", [])
    except Exception as e:
        print(f"Error fetching reviews: {e}")
        sys.exit(1)

    stored_data = load_data()
    all_reviews = stored_data.get("all_reviews", [])

    # מניעת כפילויות
    existing_ids = {f"{r.get('author_name')}_{r.get('time')}" for r in all_reviews}
    added_count = 0
    for r in new_from_google:
        r_id = f"{r.get('author_name')}_{r.get('time')}"
        if r_id not in existing_ids:
            all_reviews.append(r)
            added_count += 1

    # מיון לפי זמן (חדש ביותר למעלה)
    all_reviews.sort(key=lambda x: x.get("time", 0), reverse=True)

    # בדיקה אם יש שינוי בתוכן לפני שמעדכנים את ה-HTML
    new_hash = calculate_hash(all_reviews)
    if new_hash == stored_data.get("hash"):
        print("No change in reviews content. Skipping HTML update.")
        sys.exit(0)

    print(f"New reviews added: {added_count}. Total in carousel: {len(all_reviews)}")
    update_html(HTML_FILE, all_reviews, place_data)
    save_data(new_hash, all_reviews)
    print("Process completed successfully!")

if __name__ == "__main__":
    main()
