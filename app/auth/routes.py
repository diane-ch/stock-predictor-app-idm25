from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from app import db
from app.models.users import User
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
import secrets

# To have a separate file for everything authentification related
auth_bp = Blueprint('auth', __name__, template_folder='../templates')

def generate_csrf_token():
    """Generate CSRF token for forms"""
    return secrets.token_urlsafe(32)


@auth_bp.before_request
def before_request():
    """Add CSRF token to session if not present"""
    if 'csrf_token' not in session:
        session['csrf_token'] = generate_csrf_token()

def validate_csrf_token(token):
    """Validate CSRF token"""
    return token == session.get('csrf_token')

# Sets up the "storage containers" for the registration process if they dont exist yet
def init_registration_session():
    """Initialize registration session data"""
    if 'registration_data' not in session:
        session['registration_data'] = {}
    if 'registration_step' not in session:
        session['registration_step'] = 1

# Removes all registration-related data from the session (cleanup)
# "None" prevents errors if key missing
def clear_registration_session():
    """Clear registration session data"""
    session.pop('registration_data', None)
    session.pop('registration_step', None)

#########################
# STEP 1: Name Collection
#########################

@auth_bp.route('/register', methods=['GET', 'POST'])
@auth_bp.route('/register/step1', methods=['GET', 'POST'])
def register_step1():
    if current_user.is_authenticated:
        return redirect(url_for('main.discover'))
    
    init_registration_session()
    session['registration_step'] = 1

    if request.method == 'POST':
        csrf_token = request.form.get('csrf_token')
        if not validate_csrf_token(csrf_token):
            return redirect(url_for('auth.register_step1'))
        
        name = request.form.get('name', '').strip()
        
        # Split name into first and last
        name_parts = name.split()
        if len(name_parts) == 1:
            first_name = name_parts[0].title()
            last_name = ""
        else:
            first_name = name_parts[0].title()
            last_name = " ".join(name_parts[1:]).title()

        # Store in session
        session['registration_data']['name'] = name
        session['registration_data']['first_name'] = first_name
        session['registration_data']['last_name'] = last_name
        session['registration_step'] = 2
    
        return redirect(url_for('auth.register_step2'))
    
    # GET request - show form with any existing data
    existing_name = session.get('registration_data', {}).get('name', '')
    return render_template('auth/register_step1.html', name=existing_name, csrf_token=session['csrf_token'])

#####################################
# STEP 2: Email & Password Collection
#####################################
# Remplacez votre route register_step2 par celle-ci :

@auth_bp.route('/register/step2', methods=['GET', 'POST'])
def register_step2():
    if current_user.is_authenticated:
        return redirect(url_for('main.discover'))
    
    # Ensure user went through step 1
    if session.get('registration_step', 0) < 1:
        return redirect(url_for('auth.register_step1'))

    session['registration_step'] = 2

    if request.method == 'POST':
        csrf_token = request.form.get('csrf_token')
        if not validate_csrf_token(csrf_token):
            # Au lieu de rediriger, montrer une erreur
            return render_template('auth/register_step2.html', 
                                 email='', 
                                 csrf_token=session['csrf_token'], 
                                 error="Security token expired. Please try again.", 
                                 error_type="general")
        
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        # Email validation
        if not email:
            return render_template('auth/register_step2.html', 
                                 email=email, 
                                 csrf_token=session['csrf_token'], 
                                 error="Email is required", 
                                 error_type="email_invalid")
        
        is_valid_email, email_error = User.validate_email(email)
        if not is_valid_email:
            return render_template('auth/register_step2.html', 
                                 email=email, 
                                 csrf_token=session['csrf_token'], 
                                 error=email_error, 
                                 error_type="email_invalid")
        
        # Vérifier si l'email existe déjà
        if User.query.filter_by(email=email).first():
            return render_template('auth/register_step2.html', 
                                 email=email, 
                                 csrf_token=session['csrf_token'], 
                                 error="There's already an account with this email", 
                                 error_type="email_exists")

        # Password validation
        if not password:
            return render_template('auth/register_step2.html', 
                                 email=email, 
                                 csrf_token=session['csrf_token'], 
                                 error="Password is required", 
                                 error_type="password_invalid")
        
        is_valid_password, password_error = User.validate_password(password)
        if not is_valid_password:
            return render_template('auth/register_step2.html', 
                                 email=email, 
                                 csrf_token=session['csrf_token'], 
                                 error=password_error, 
                                 error_type="password_invalid")
        
        # Create the user account
        try:
            registration_data = session['registration_data']

            new_user = User(
                email=email,
                first_name=registration_data['first_name'],
                last_name=registration_data['last_name']
            )
            new_user.set_password(password)

            db.session.add(new_user)
            db.session.commit()

            clear_registration_session()

            login_user(new_user)
            return redirect(url_for('main.onboarding'))        
        
        except Exception as e:
            # Log l'erreur pour debug mais ne l'exposez pas à l'utilisateur
            print(f"Error creating user: {e}")
            db.session.rollback()
            return render_template('auth/register_step2.html', 
                                 email=email, 
                                 csrf_token=session['csrf_token'], 
                                 error="An error occurred while creating your account. Please try again.", 
                                 error_type="general")
    
    # GET request
    existing_email = session.get('registration_data', {}).get('email', '')
    return render_template('auth/register_step2.html', 
                         email=existing_email, 
                         csrf_token=session['csrf_token'])

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.discover'))

    if request.method == 'POST':
        csrf_token = request.form.get('csrf_token')
        if not validate_csrf_token(csrf_token):
            return redirect(url_for('auth.login'))
    
        
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        if not email or not password:
            return render_template('auth/login.html', email=email, csrf_token=session['csrf_token'], error="Incorrect email or password")
        
        user = User.query.filter_by(email=email).first()  

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('main.discover')) 

        else:
            # Login failed - show error message
            return render_template('auth/login.html', email=email, csrf_token=session['csrf_token'], error="Incorrect email or password")

    return render_template('auth/login.html', csrf_token=session['csrf_token'])

# Back navigation routes
@auth_bp.route('/register/back/<int:step>')
def register_back(step):
    """Allow users to go back to previous steps"""
    if current_user.is_authenticated:
        return redirect(url_for('main.discover'))
    
    if step == 1:
        if 'registration_data' in session:
            session['registration_step'] = 1
        return redirect(url_for('auth.register_step1'))
    else:
        return redirect(url_for('auth.register_step1'))


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    clear_registration_session()
    return redirect(url_for('auth.login'))


@auth_bp.route('/users')
def list_users():
    users = User.query.all()
    return '<br>'.join([f"{u.id}: {u.email}" for u in users])

