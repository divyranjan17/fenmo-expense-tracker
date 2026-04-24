from pathlib import Path

from flask import Flask, jsonify, send_from_directory

from backend.db import init_db
from backend.routes.expenses import expenses_bp


def create_app(test_config=None):
    base_dir = Path(__file__).resolve().parent.parent
    frontend_dir = base_dir / "frontend"

    app = Flask(
        __name__,
        static_folder=str(frontend_dir),
        static_url_path=""
    )

    app.config.from_mapping(
        DATABASE=str(base_dir / "expenses.sqlite3"),
    )

    if test_config:
        app.config.update(test_config)

    init_db(app)
    app.register_blueprint(expenses_bp)

    @app.get("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    # ✅ CRITICAL: serve other frontend routes/files
    @app.get("/<path:path>")
    def serve_static(path):
        return send_from_directory(app.static_folder, path)

    @app.errorhandler(500)
    def internal_server_error(_error):
        return jsonify(
            {
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
            }
        ), 500

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5000, debug=False)