import os
from flask import Flask, jsonify, render_template


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY", "development-secret"),
        DATABASE=os.getenv("DATABASE", "/tmp/aatrox-game.db"),
        FLAG=os.getenv("FLAG", "flag{development_only}"),
        RACE_WINDOW_MS=int(os.getenv("RACE_WINDOW_MS", "75")),
    )
    if test_config:
        app.config.update(test_config)

    from .db import init_db
    init_db(app)

    @app.get("/health")
    def health():
        return jsonify(ok=True)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.errorhandler(404)
    def missing(_):
        return jsonify(ok=False, error="not_found", message="资源不存在"), 404

    from .routes.game import bp as game_bp
    from .routes.rewards import bp as reward_bp
    from .routes.shop import bp as shop_bp
    from .routes.campfires import bp as campfire_bp
    app.register_blueprint(game_bp)
    app.register_blueprint(reward_bp)
    app.register_blueprint(shop_bp)
    app.register_blueprint(campfire_bp)
    return app
