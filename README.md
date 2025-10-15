# minimal-gemini-chatbot-149454-149463

Backend (Flask) CORS and preflight are configured for http://localhost:3000 with allowed methods [GET, POST, OPTIONS] and headers [Content-Type, Authorization]. Two endpoints are available:
- POST http://localhost:3001/api/chat
- POST http://localhost:3001/api/message (alternate path to avoid ad-blockers)

Frontend fetch example (React):
```js
const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:3001';
const endpoint = `${API_BASE}/api/message`; // prefer /message to avoid ad-blockers

async function sendMessage(message) {
  const res = await fetch(endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
      // Do not set Authorization unless needed; avoid custom headers that trigger preflight failures.
    },
    body: JSON.stringify({ message })
  });
  const data = await res.json().catch(() => ({ error: 'Invalid JSON' }));
  return data;
}
```

If you see net::ERR_BLOCKED_BY_CLIENT, try:
- Use /api/message instead of /api/chat
- Disable ad-blocking extensions for localhost
- Ensure only 'Content-Type: application/json' is set in headers

Environment variables:
- GEMINI_API_KEY: required for real responses
- ALLOW_FAKE_GEMINI=true: returns a stubbed reply "Echo: <message>" for testing without an API key
