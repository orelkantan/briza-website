exports.handler = async function (event) {
  // רק POST מותר
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: 'Method Not Allowed' };
  }

  // CORS — מרשה רק את הדומיין שלך (שנה אם צריך)
  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
  };

  let body;
  try {
    body = JSON.parse(event.body);
  } catch {
    return { statusCode: 400, body: 'Invalid JSON' };
  }

  const { messages } = body;
  if (!messages || !Array.isArray(messages)) {
    return { statusCode: 400, body: 'Missing messages' };
  }

  const BRIZA_SYSTEM_PROMPT = `אתה עוזר שירות לקוחות של "בריזה" — חברה מקצועית לטכנאי מיני-בר ומערכות סודה.

פרטים על החברה:
- שם: בריזה
- סלוגן: "מים שזורמים איתך"
- טלפון ווואטסאפ: 03-6000-311
- איש קשר ראשי: משה
- שעות פעילות: ימים א–ה 09:00–18:00, שישי 08:00–12:00
- מגיעים ביום הפנייה!

שירותים:
- תיקון מיני-בר (כל סוגי התקלות: קירור, חימום, רעשים, נזילות, חשמל)
- התקנת מיני-בר חדש — ביתי, עסקי ומוסדי
- מיני-בר שבת — מוסמכים ע"י "משמרת השבת" (הסמכה בתוקף עד 26.10.2026), מוצר: Spirit Touch Bar Shabbat
- מערכות סודה — תיקון, טעינת גז, התקנה
- ברי קיטור ומערכות מים חמים
- מסנני מים מקצועיים

מחירים:
- אבחון ראשוני: חינם!
- תיקון מיני-בר: 150–450 ₪ (תלוי בסוג התקלה)
- התקנה חדשה: לפי סוג המערכת
- אחריות: 3 חודשים על עבודה + אחריות יצרן על חלקים

אזור שירות: גוש דן — תל אביב, רמת גן, פתח תקווה, בני ברק, גבעתיים, ראשון לציון, השפלה והשרון.

כללי התנהגות:
- דבר בעברית בלבד, בגוף שני זכר
- היה ידידותי, קצר וממוקד — לא יותר מ-4–5 שורות לתגובה
- הוסף אימוג'י רלוונטי אחד-שניים לכל תגובה
- לשאלות על מחיר מדויק, תיאום ביקור, או כשהלקוח מוכן להזמין — הפנה לטלפון 03-6000-311
- אל תמציא מידע שלא רשום כאן
- אם שאלה לא קשורה לבריזה — ענה בנימוס שאתה מומחה רק לתחום שלנו`;

  try {
    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': process.env.ANTHROPIC_API_KEY, // 🔐 מוסתר בסביבת Netlify
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: 'claude-haiku-4-5-20251001',
        max_tokens: 400,
        system: BRIZA_SYSTEM_PROMPT,
        messages,
        stream: true,
      }),
    });

    if (!response.ok) {
      const err = await response.text();
      return { statusCode: response.status, headers, body: err };
    }

    // העברת ה-stream מ-Anthropic ישירות ללקוח
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let result = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      result += decoder.decode(value, { stream: true });
    }

    return {
      statusCode: 200,
      headers: { ...headers, 'Content-Type': 'text/plain' },
      body: result,
    };
  } catch (err) {
    console.error('Briza proxy error:', err);
    return { statusCode: 500, headers, body: 'Server error' };
  }
};
