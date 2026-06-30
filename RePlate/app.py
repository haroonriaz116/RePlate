from flask import Flask, jsonify, send_from_directory

from config import Config
from extensions import db, login_manager
from models import User


def create_app(config_class=Config):
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        # The frontend is a JavaScript single page app, so a redirect to a
        # server-rendered login page would make no sense here. Returning
        # JSON lets app.js decide how to route the person instead.
        return jsonify({"errors": ["Please log in to continue."]}), 401

    import main
    import auth
    import listings
    import dashboard

    app.register_blueprint(main.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(listings.bp)
    app.register_blueprint(dashboard.bp)

    @app.route("/")
    @app.route("/<path:path>")
    def spa(path=""):
        # Every non-API, non-asset route falls through to the single page
        # app shell. app.js reads the URL itself and renders the right
        # view, the same way client side routing works in any JavaScript
        # frontend, so the server only ever needs to hand back index.html.
        return send_from_directory(app.static_folder, "index.html")

    @app.cli.command("init-db")
    def init_db():
        """Create all tables. Run with: flask --app app init-db"""
        with app.app_context():
            db.create_all()
        print("Database tables created.")

    return app


app = create_app()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
