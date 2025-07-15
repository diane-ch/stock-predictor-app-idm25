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
        return redirect(url_for('auth.profile'))
    
    init_registration_session()
    session['registration_step'] = 1

    if request.method == 'POST':
        csrf_token = request.form.get('csrf_token')
        if not validate_csrf_token(csrf_token):
            flash('Security token invalid. Please try again.', 'error')
            return redirect(url_for('auth.register_step1'))
        
        name = request.form.get('name', '').strip()

        # Validation
        if not name or len(name) < 2:
            flash('Please enter your full name (at least 2 characters)', 'error')
            return render_template('auth/register_step1.html', name=name, csrf_token=session['csrf_token'])
        
        if len(name) > 100:
            flash('Name is too long (maximum 100 characters)', 'error')
            return render_template('auth/register_step1.html', name=name, csrf_token=session['csrf_token'])
        
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
@auth_bp.route('/register/step2', methods=['GET', 'POST'])
def register_step2():
    if current_user.is_authenticated:
        return redirect(url_for('auth.profile'))
    
    # Ensure user went through step 1
    if session.get('registration_step', 0) < 1:
        return redirect(url_for('auth.register_step1'))

    session['registration_step'] = 2

    if request.method == 'POST':
        csrf_token = request.form.get('csrf_token')
        if not validate_csrf_token(csrf_token):
            flash('Security token invalid. Please try again.', 'error')
            return redirect(url_for('auth.register_step2'))
        
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        errors = []

        # Email validation
        if not email:
            errors.append("Email is required")
        else:
            is_valid_email, email_error = User.validate_email(email)
            if not is_valid_email:
                errors.append(email_error)
            elif User.query.filter_by(email=email).first():
                errors.append("Email already registered")

        # Password validation
        if not password:
            errors.append("Password is required")
        else:
            is_valid_password, password_error = User.validate_password(password)
            if not is_valid_password:
                errors.append(password_error)

        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('auth/register_step2.html', email=email, csrf_token=session['csrf_token'])
        
        # Store in session
        session['registration_data']['email'] = email
        session['registration_data']['password'] = password
        session['registration_step'] = 3

        return redirect(url_for('auth.register_step3'))
    
    # GET request
    existing_email = session.get('registration_data', {}).get('email', '')
    return render_template('auth/register_step2.html', email=existing_email, csrf_token=session['csrf_token'])


#####################################
# STEP 3: Investment Knowledge Level
#####################################
@auth_bp.route('/register/step3', methods=['GET', 'POST'])
def register_step3():
    if current_user.is_authenticated:
        return redirect(url_for('auth.profile'))
    
    # Ensure user went through previous steps
    if session.get('registration_step', 0) < 2:
        return redirect(url_for('auth.register_step1'))
    
    session['registration_step'] = 3

    if request.method == 'POST':
        csrf_token = request.form.get('csrf_token')
        if not validate_csrf_token(csrf_token):
            flash('Security token invalid. Please try again.', 'error')
            return redirect(url_for('auth.register_step3'))
        
        investment_level = request.form.get('investment_level')

        valid_levels = ['pro_investor', 'intermediate', 'basic', 'first_contact']
        if not investment_level or investment_level not in valid_levels:
            #flash('Please select your investment knowledge level', 'error')
            return render_template('auth/register_step3.html', csrf_token=session['csrf_token'])
        
        # Store in session
        session['registration_data']['investment_level'] = investment_level

        # Create the user account
        try:
            registration_data = session['registration_data']

            new_user = User(
                email=registration_data['email'],
                first_name=registration_data['first_name'],
                last_name=registration_data['last_name'],
                investment_level=investment_level
            )
            new_user.set_password(registration_data['password'])

            db.session.add(new_user)
            db.session.commit()

            clear_registration_session()

            flash(f'Welcome {new_user.first_name}! Your account has been created successfully.', 'success')
            return redirect(url_for('auth.login'))
        
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while creating your account. Please try again.', 'error')
            return render_template('auth/register_step3.html', csrf_token=session['csrf_token'])


    # GET request
    existing_level = session.get('registration_data', {}).get('investment_level', '')
    return render_template('auth/register_step3.html', investment_level=existing_level, csrf_token=session['csrf_token'])


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('auth.profile'))

    if request.method == 'POST':
        csrf_token = request.form.get('csrf_token')
        if not validate_csrf_token(csrf_token):
            flash('Security token invalid. Please try again.', 'error')
            return redirect(url_for('auth.login'))
        
        email = request.form.get('email', '')  
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('Email and password are required.', 'error')
            return render_template('auth/login.html', email=email, csrf_token=session['csrf_token'])
        
        user = User.query.filter_by(email=email).first()  

        if user and user.check_password(password):
            if user.is_account_locked():
                flash('Account temporarily locked. Please try again later.', 'error')
                return render_template('auth/login.html', csrf_token=session['csrf_token'])
            
            user.record_successful_login()
            db.session.commit()

            login_user(user)
            flash(f'Welcome back, {user.first_name}!', 'success')
            return redirect(url_for('auth.profile'))
        else:
            if user:
                user.record_failed_login()
                db.session.commit()
            flash('Invalid email or password.', 'error')

    return render_template('auth/login.html', csrf_token=session['csrf_token'])

# Back navigation routes
@auth_bp.route('/register/back/<int:step>')
def register_back(step):
    """Allow users to go back to previous steps"""
    if current_user.is_authenticated:
        return redirect(url_for('auth.profile'))
    
    if step == 1:
        if 'registration_data' in session:
            session['registration_step'] = 1
        return redirect(url_for('auth.register_step1'))
    elif step == 2:
        if 'registration_data' in session:
            session['registration_step'] = 2
        return redirect(url_for('auth.register_step2'))
    else:
        return redirect(url_for('auth.register_step1'))


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    clear_registration_session()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile')
@login_required
def profile():
    return f"Hello, {current_user.email}! This is your profile."
# return render_template('auth/profile.html', user=current_user)

@auth_bp.route('/users')
def list_users():
    users = User.query.all()
    return '<br>'.join([f"{u.id}: {u.email}" for u in users])
