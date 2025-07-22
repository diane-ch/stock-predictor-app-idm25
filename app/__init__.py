from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os
from datetime import timedelta


# Initialize Flask extensions
db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    """
    Application factory function that creates and configures the Flask app
    """
    app = Flask(__name__)

    # Application Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'dev-key-change-in-production'
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Disable SQLAlchemy's modification tracking system (saves memory)

    # Session and Security Configuration
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)  # Sessions expire after 24 hours (automatically logs users outO)
    app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access to session cookies
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection

    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)

    # Configure Flask-Login
    login_manager.login_view = 'auth.login'  # Redirect unauthorized users to login page
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    login_manager.session_protection = 'strong'  # Enhanced session security

    # User loader function for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        from app.models.users import User
        return User.query.get(int(user_id))
    
    # Import and register blueprints
    from app.auth.routes import auth_bp
    from app.education.routes import education_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(education_bp, url_prefix='/education')

    # Import models to ensure they're registered with SQLAlchemy
    from app.models.users import User

    # Create database tables if they don't exist
    with app.app_context():
        db.create_all()

    @app.route('/')
    def index():
        return '''
        <h1>Stock Predictor App</h1>
        <p><a href="/auth/login">Login</a> | <a href="/auth/register">Register</a></p>
        <p><em>Note: <a href="/education">Education</a> requires login</em></p>
        '''

    return app
