from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your-secret-key'  # à changer en prod !
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'  # redirige si non connecté

    # Import et enregistrement blueprint auth
    from app.auth.routes import auth_bp
    app.register_blueprint(auth_bp)

    # Création tables si besoin
    with app.app_context():
        db.create_all()

    return app
