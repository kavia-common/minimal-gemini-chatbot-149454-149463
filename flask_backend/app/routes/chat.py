import os
from flask_smorest import Blueprint, abort
from marshmallow import Schema, fields, ValidationError
from flask.views import MethodView

# Attempt to import google.generativeai; will be installed via requirements.txt
try:
    import google.generativeai as genai
except Exception:  # pragma: no cover - import error handled during runtime if missing
    genai = None


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
          - 200: JSON { "reply": string } on success
          - 400: JSON { "error": string } on client errors (missing/empty message)
          - 500: JSON { "error": string } on server errors (e.g., model/API failures)
        """
        # Validate non-empty trimmed message
        if not isinstance(message, str) or not message.strip():
            abort(400, message={"error": "The 'message' field must be a non-empty string."})

        api_key = os.getenv("GEMINI_API_KEY")
        allow_fake = os.getenv("ALLOW_FAKE_GEMINI", "false").lower() in ("1", "true", "yes", "on")

        # If no API key and fake mode allowed, return a deterministic stub to enable UI verification
        if not api_key and allow_fake:
            return {"reply": f"Echo: {message.strip()}"}

        if not api_key:
            abort(500, message={"error": "GEMINI_API_KEY environment variable is not set."})

        if genai is None:
            abort(500, message={"error": "google-generativeai package is not installed."})

        try:
            # Configure client
            genai.configure(api_key=api_key)

            # Prefer gemini-1.5-flash; fallback to gemini-pro if needed
            model_name_candidates = ["gemini-1.5-flash", "gemini-pro"]
            last_error = None

            for model_name in model_name_candidates:
                try:
                    model = genai.GenerativeModel(model_name)
                    # Generate concise reply
                    response = model.generate_content(
                        f"Provide a concise helpful reply to the user message:\n\n{message}"
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
                        except Exception:
                            reply_text = None

                    if not reply_text:
                        # If model returned nothing meaningful, raise to try next model or 500
                        raise RuntimeError("Model returned empty response")

                    # Keep responses concise
                    reply_text = reply_text.strip()
                    return {"reply": reply_text[:2000]}  # hard cap to avoid overly long responses
                except Exception as e:  # try next model if available
                    last_error = e
                    continue

            # If all models failed
            raise RuntimeError(f"All model attempts failed: {last_error}")
        except ValidationError as ve:
            abort(400, message={"error": str(ve)})
        except Exception as e:
            abort(500, message={"error": f"Failed to generate reply: {str(e)}"})
