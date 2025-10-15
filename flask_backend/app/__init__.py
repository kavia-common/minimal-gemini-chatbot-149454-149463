from flask import Flask
from flask_cors import CORS
from flask_smorest import Api

# Import blueprints
from .routes.health import blp as health_blp
from .routes.chat import blp as chat_blp

app = Flask(__name__)
app.url_map.strict_slashes = False

# Configure CORS explicitly to ensure preflight and error responses include headers.
# - Allow only the React dev origin on 3000
# - Allow common methods and headers
# - Do not use credentials for this simple app
CORS(
    app,
    resources={r"/*": {"origins": ["http://localhost:3000"]}},
    supports_credentials=False,
    methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["Content-Type"],
)

# OpenAPI / Swagger settings
app.config["API_TITLE"] = "My Flask API"
app.config["API_VERSION"] = "v1"
app.config["OPENAPI_VERSION"] = "3.0.3"
app.config["OPENAPI_SWAGGER_UI_PATH"] = ""
app.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"
app.config["OPENAPI_URL_PREFIX"] = "/docs"

api = Api(app)

# Register blueprints
api.register_blueprint(health_blp)
api.register_blueprint(chat_blp)
