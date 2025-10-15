# minimal-gemini-chatbot-149454-149463

Backend (Flask) CORS and preflight are configured for:
- http://localhost:3000
- https://vscode-internal-23153-beta.beta01.cloud.kavia.ai:3000

Allowed methods: [GET, POST, OPTIONS]
Allowed headers: [Content-Type, Authorization]

Three endpoints are available (backend base http://localhost:3001 or https://vscode-internal-23153-beta.beta01.cloud.kavia.ai:3001):
- POST /api/chat
- POST /api/message (alternate path to avoid ad-blockers)
- POST /api/send (final alias if other paths are blocked)

Frontend fetch example (React):
```js
const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:3001';

// Prefer /message; retry with /send if blocked by extensions
async function sendMessage(message) {
  const tryFetch = async (path) => {
    const res = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
        // Do not set Authorization unless needed; avoid custom headers that trigger preflight failures.
      },
      body: JSON.stringify({ message })
    });
    return res;
  };

  let res;
  try {
    res = await tryFetch('/api/message');
  } catch (e) {
    // network-level failure (e.g., ad-block)
    try {
      res = await tryFetch('/api/send');
    } catch (e2) {
      return { error: 'Network error' };
    }
  }

  const data = await res.json().catch(() => ({ error: 'Invalid JSON' }));
  return data;
}
```

If you see net::ERR_BLOCKED_BY_CLIENT, try:
- Use /api/message instead of /api/chat
- If still blocked, use /api/send
- Disable ad-blocking extensions for localhost
- Ensure only 'Content-Type: application/json' is set in headers

Environment variables:
- GEMINI_API_KEY: required for real responses
- GEMINI_MODEL: optional, override model (e.g., gemini-1.5-flash, gemini-pro)
- ALLOW_FAKE_GEMINI=true: returns a stubbed reply "Echo: <message>" for testing without an API key

Behavior:
- If GEMINI_API_KEY is missing/invalid:
  - When ALLOW_FAKE_GEMINI=true, endpoints return 200 with {"reply":"Echo: <message>"}.
  - Otherwise endpoints return 200 with a friendly fallback {"reply":"Sorry, I'm having trouble responding right now. Please try again."}.
- Invalid input (missing/empty "message") returns 400 with {"error":"message is required"}.
- No raw 500s are exposed to the client for typical failures; errors are logged server-side.

Quick verification:

1) Health
curl -i https://vscode-internal-23153-beta.beta01.cloud.kavia.ai:3001/

2) Real call (requires GEMINI_API_KEY set in backend env)
curl -i -X POST https://vscode-internal-23153-beta.beta01.cloud.kavia.ai:3001/api/message \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello from curl"}'
# If blocked by client, try:
curl -i -X POST https://vscode-internal-23153-beta.beta01.cloud.kavia.ai:3001/api/send \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello from curl"}'

Expected: HTTP/1.1 200 OK with JSON body {"reply":"..."}.

3) Invalid input (expect 400 with normalized error)
curl -i -X POST https://vscode-internal-23153-beta.beta01.cloud.kavia.ai:3001/api/message \
  -H "Content-Type: application/json" \
  -d '{"message":""}'
