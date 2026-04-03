exports.handler = async function (event) {
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: 'Method Not Allowed' };
  }

  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Content-Type': 'application/json',
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
- טלפון ווואטסאפ: 03-6000-311
- שעות פעילות: ימים א–ה 09:00–18:00, שישי 08:00–12:00
- מגיעים ביום הפנייה!
שירותים: תיקון מיני-בר, התקנה חדשה, מיני-בר שבת (מוסמך משמרת השבת), מערכות סודה, ברי קיטור, מסנני מים.
מחירים: אבחון חינם, תיקון 150-450 ₪, אחריות 3 חודשים.
אזור שירות: גוש דן — תל אביב, רמת גן, פתח תקווה, בני ברק, גבעתיים, ראשון לציון.
כללי: דבר עברית, היה קצר (4-5 שורות), הוסף אימוג'י, הפנה לטלפון לתיאום.`;

  const geminiMessages = messages.map(m => ({
    role: m.role === 'assistant' ? 'model' : 'user',
    parts: [{ text: m.content }]
  }));

  try {
    const apiKey = process.env.GEMINI_API_KEY;
    const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${apiKey}`;

    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        system_instruction: { parts: [{ text: BRIZA_SYSTEM_PROMPT }] },
        contents: geminiMessages,
        generationConfig: { maxOutputTokens: 400, temperature: 0.7 }
      }),
    });

    if (!response.ok) {
      const err = await response.text();
      return { statusCode: response.status, headers, body: err };
    }

    const data = await response.json();
    const reply = data.candidates?.[0]?.content?.parts?.[0]?.text || 'מצטער, נסה שוב או התקשר: 03-6000-311';

    return { statusCode: 200, headers, body: JSON.stringify({ reply }) };
  } catch (err) {
    console.error('Briza proxy error:', err);
    return { statusCode: 500, headers, body: 'Server error' };
  }
};
