from flask_smorest import Blueprint
from flask.views import MethodView

# Define health blueprint with proper metadata
blp = Blueprint("Health Check", "health", url_prefix="/", description="Health check route")

@blp.route("/")
class HealthCheck(MethodView):
    # PUBLIC_INTERFACE
    def get(self):
        """
        Health endpoint for service monitoring and frontend connectivity checks.

        Returns:
          - 200: JSON { "message": "Healthy" } and includes CORS headers for allowed origins.
        """
        return {"message": "Healthy"}

    def options(self):
        """
        Preflight handler for health check path '/' to ensure CORS preflight succeeds.

        Returns:
          - 204 No Content with appropriate CORS headers (added by Flask-CORS).
        """
        # Returning empty body and 204; Flask-CORS will attach the Access-Control-Allow-* headers.
        return ("", 204)
