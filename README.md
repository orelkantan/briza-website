# 🔄 אוטומציית ביקורות גוגל — בריזה

עדכון אוטומטי של ביקורות Google לאתר, בחינם לגמרי.

---

## איך זה עובד?

```
כל יום בשעה 09:00 (ישראל)
        ↓
GitHub Actions מריץ את update_reviews.py
        ↓
הסקריפט שולח בקשה ל-Google Places API
        ↓
אם יש ביקורת חדשה — מעדכן את index.html
        ↓
GitHub Pages מפרסם את האתר המעודכן אוטומטית
```

---

## הגדרה ראשונית (פעם אחת בלבד)

### שלב 1 — קבל Google API Key

1. נכנסים ל-[Google Cloud Console](https://console.cloud.google.com)
2. יוצרים פרויקט חדש (כפתור למעלה)
3. בתפריט → **APIs & Services** → **Enable APIs**
4. מחפשים **"Places API"** ומפעילים
5. הולכים ל-**Credentials** → **Create Credentials** → **API Key**
6. שומרים את המפתח (נראה כך: `AIzaSy...`)

> ⚠️ כדי למנוע שימוש לרעה: ב-API Key → **Restrict Key** → בחרו **Places API** בלבד.

---

### שלב 2 — מצא את Place ID של בריזה

1. נכנסים ל: https://developers.google.com/maps/documentation/javascript/examples/places-placeid-finder
2. מחפשים "בריזה" + רמת גן
3. מעתיקים את ה-**Place ID** (מתחיל ב-`ChIJ...`)

---

### שלב 3 — העלאה ל-GitHub

1. **יוצרים רפוזיטורי חדש** ב-[github.com](https://github.com/new)
   - שם: `briza-website` (או כל שם אחר)
   - ✅ Public (נדרש עבור GitHub Pages חינמי)

2. **מעלים את הקבצים** (גוררים ל-GitHub או דרך terminal):
   ```
   index.html              ← קובץ האתר (המעודכן עם הסימנים)
   update_reviews.py       ← הסקריפט
   .github/
     workflows/
       update-reviews.yml  ← קובץ האוטומציה
   ```

---

### שלב 4 — שמירת Secrets ב-GitHub

1. בדף הרפוזיטורי → **Settings** → **Secrets and variables** → **Actions**
2. לוחצים **New repository secret** ומוסיפים:

   | שם | ערך |
   |----|-----|
   | `GOOGLE_API_KEY` | המפתח מ-שלב 1 |
   | `PLACE_ID` | המזהה מ-שלב 2 |

---

### שלב 5 — הפעלת GitHub Pages

1. **Settings** → **Pages**
2. תחת **Source** → בחרו `Deploy from a branch`
3. Branch: `main` / `root`
4. שמרו — האתר יהיה זמין בכתובת:
   `https://[USERNAME].github.io/[REPO-NAME]/`

---

### שלב 6 — הרצה ידנית ראשונה (לבדיקה)

1. לשונית **Actions** ברפוזיטורי
2. בחרו **"עדכון ביקורות גוגל אוטומטי"**
3. לחצו **Run workflow**
4. בדקו שהריצה הצליחה (✅ ירוק)
5. בדקו שה-`index.html` התעדכן עם ביקורות חדשות

---

## מבנה הקבצים

```
briza-website/
├── index.html                    ← האתר (עם סימני REVIEWS_START/END)
├── update_reviews.py             ← הסקריפט
├── .reviews_cache.json           ← נוצר אוטומטית, לא לגעת
└── .github/
    └── workflows/
        └── update-reviews.yml    ← לוח הזמנים של האוטומציה
```

---

## שאלות נפוצות

**כמה ביקורות יוצגו?**
Google Places API מחזיר עד 5 ביקורות חינם. כדי לקבל יותר, צריך את ה-Places API (New) בתשלום.

**מה אם גוגל לא מחזיר ביקורות בעברית?**
הסקריפט שולח `language=iw` — גוגל יחזיר ביקורות בעברית אם יש כאלו.

**האם זה עולה כסף?**
לא. Google Places API נותן $200 קרדיט חינמי בחודש — לשימוש זה (בקשה אחת ביום) לא תגיע אליו.

**איך משנים את שעת הריצה?**
בקובץ `update-reviews.yml`, שנו את שורת `cron`:
```yaml
- cron: "0 6 * * *"   # 06:00 UTC = 09:00 ישראל
```
[מחולל cron](https://crontab.guru) — לבחור שעה אחרת.

**איך מריצים ידנית?**
GitHub → Actions → בחרו ה-Workflow → "Run workflow"
