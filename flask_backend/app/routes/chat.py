import os
import logging
from flask import make_response
from flask_smorest import Blueprint, abort
from marshmallow import Schema, fields, ValidationError
from flask.views import MethodView

# Attempt to import google.generativeai; will be installed via requirements.txt
try:
    import google.generativeai as genai
except Exception:  # pragma: no cover - import error handled during runtime if missing
    genai = None

# Basic logger setup for this module
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


blp = Blueprint(
    "Chat",
    "chat",
    url_prefix="/api",
    description="Chatbot endpoint backed by Google Generative AI",
)


class ChatRequestSchema(Schema):
    # PUBLIC_INTERFACE
    def __init__(self, *args, **kwargs):
        """Schema for chat request containing a single 'message' string field."""
        super().__init__(*args, **kwargs)

    message = fields.String(required=True, allow_none=False, metadata={"description": "User message"})


class ChatResponseSchema(Schema):
    # PUBLIC_INTERFACE
    def __init__(self, *args, **kwargs):
        """Schema for chat response containing a single 'reply' string field."""
        super().__init__(*args, **kwargs)

    reply = fields.String(required=True, metadata={"description": "Model reply"})


def _ok_preflight_response():
    """Return a 204 empty response for successful CORS preflight."""
    resp = make_response("", 204)
    return resp


def _friendly_fallback(message: str) -> dict:
    """
    Return a deterministic friendly reply used when the model is unavailable or errors occur.
    This ensures the frontend always receives a 200 with a usable reply and never a raw 500.
    """
    # PUBLIC_INTERFACE
    reply = "Sorry, I'm having trouble responding right now. Please try again."
    return {"reply": reply}


def _fake_or_fallback(message: str, allow_fake: bool) -> dict:
    """
    Helper to return either the fake echo (when ALLOW_FAKE_GEMINI=true) or the friendly fallback.
    """
    # PUBLIC_INTERFACE
    if allow_fake:
        return {"reply": f"Echo: {message.strip()}"}
    return _friendly_fallback(message)


def _bool_env(name: str, default: bool = False) -> bool:
    val = os.getenv(name, str(default)).lower()
    return val in ("1", "true", "yes", "on")


def _safe_abort_bad_request(msg: str):
    # Consistent 400 shape
    abort(400, message={"error": msg})


def _handle_chat(message: str):
    """Core handler shared by both /chat and /message routes."""
    # Validate non-empty trimmed message
    if not isinstance(message, str) or not message.strip():
        _safe_abort_bad_request("message is required")

    api_key = os.getenv("GEMINI_API_KEY")
    allow_fake = _bool_env("ALLOW_FAKE_GEMINI", False)

    # Log API key presence (not the key), and package availability for diagnostics
    api_key_present = bool(api_key and api_key.strip())
    logger.info("Gemini setup: api_key_present=%s, genai_available=%s", api_key_present, genai is not None)

    # Initialization guard: if no key or package missing, return fake or friendly fallback
    if not api_key_present or genai is None:
        if not api_key_present:
            logger.warning("GEMINI_API_KEY is missing or empty. Using fallback (allow_fake=%s).", allow_fake)
        if genai is None:
            logger.error("google-generativeai package not available. Using fallback (allow_fake=%s).", allow_fake)
        return _fake_or_fallback(message, allow_fake)

    try:
        # Configure client
        genai.configure(api_key=api_key)

        # Prefer gemini-1.5-flash; fallback to gemini-pro if needed
        model_name_candidates = ["gemini-1.5-flash", "gemini-pro"]
        last_error = None

        for model_name in model_name_candidates:
            try:
                model = genai.GenerativeModel(model_name)
                # Generate concise reply with a conservative server-side timeout
                response = model.generate_content(
                    f"Provide a concise helpful reply to the user message:\n\n{message}",
                    request_options={"timeout": 15},
                )
                # google-generativeai responses may contain .text or candidates; prefer .text
                reply_text = getattr(response, "text", None)
                if not reply_text and hasattr(response, "candidates") and response.candidates:
                    # Fallback: attempt to read from first candidate content parts
                    cand = response.candidates[0]
                    try:
                        parts = cand.content.parts if hasattr(cand, "content") else []
                        reply_text = " ".join(
                            [getattr(p, "text", "") for p in parts if getattr(p, "text", "")]
                        ).strip()
                    except Exception as parse_err:
                        logger.debug("Candidate parse failed: %s", parse_err)
                        reply_text = None

                if not reply_text:
                    # If model returned nothing meaningful, raise to try next model or fallback
                    raise RuntimeError("Model returned empty response")

                # Keep responses concise
                reply_text = reply_text.strip()
                return {"reply": reply_text[:2000]}  # hard cap
            except Exception as e:  # try next model if available
                last_error = e
                # Include type for better diagnostics while avoiding sensitive data
                logger.warning("Model '%s' failed (%s): %s", model_name, type(e).__name__, str(e))
                continue

        # If all models failed, log and fallback
        logger.error("All model attempts failed: %s: %s", type(last_error).__name__ if last_error else "UnknownError", str(last_error))
        return _fake_or_fallback(message, allow_fake)
    except ValidationError as ve:
        _safe_abort_bad_request(str(ve))
    except Exception as e:
        # Any unexpected runtime errors: log and fallback, do not leak stack traces
        logger.exception("Unexpected error during chat handling: %s: %s", type(e).__name__, str(e))
        return _fake_or_fallback(message, allow_fake)


@blp.route("/chat")
class ChatResource(MethodView):
    # PUBLIC_INTERFACE
    @blp.arguments(ChatRequestSchema, as_kwargs=True)
    @blp.response(200, ChatResponseSchema)
    def post(self, message: str):
        """
        Handle chat requests and return a concise reply.

        Request body:
          - message: string (required) - the user's input.

        Returns:
          - 200: JSON { "reply": string } on success or friendly fallback when model is unavailable
          - 400: JSON { "error": string } on client errors (missing/empty message)
        """
        return _handle_chat(message)

    # Explicit OPTIONS to satisfy strict environments; Flask-CORS will add headers.
    def options(self):
        """
        Preflight request handler for /api/chat.

        Returns:
          - 204 No Content with appropriate CORS headers
        """
        return _ok_preflight_response()


@blp.route("/message")
class MessageResource(MethodView):
    # PUBLIC_INTERFACE
    @blp.arguments(ChatRequestSchema, as_kwargs=True)
    @blp.response(200, ChatResponseSchema)
    def post(self, message: str):
        """
        Alternate endpoint for posting messages (alias of /api/chat). Useful if
        client-side blockers interfere with the 'chat' keyword.

        Request body:
          - message: string (required)

        Returns:
          - 200: JSON { "reply": string } on success or friendly fallback when model is unavailable
          - 400: JSON { "error": string } on client errors
        """
        return _handle_chat(message)

    def options(self):
        """
        Preflight request handler for /api/message.

        Returns:
          - 204 No Content with appropriate CORS headers
        """
        return _ok_preflight_response()
