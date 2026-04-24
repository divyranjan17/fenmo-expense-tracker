from pathlib import Path

from flask import Flask, jsonify

from backend.db import init_db
from backend.routes.expenses import expenses_bp


def create_app(test_config=None):
    frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
    app = Flask(__name__, static_folder=str(frontend_dir), static_url_path="")
    app.config.from_mapping(
        DATABASE="expenses.sqlite3",
    )

    if test_config:
        app.config.update(test_config)

    init_db(app)
    app.register_blueprint(expenses_bp)

    @app.get("/")
    def index():
        return app.send_static_file("index.html")

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
    create_app().run(debug=True)
