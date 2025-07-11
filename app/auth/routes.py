from flask import Blueprint, render_template, redirect, url_for, request, flash
from app import db
from app.models.users import User
from flask_login import login_user, logout_user, login_required, current_user

# To have a separate file for everything authentification related
auth_bp = Blueprint('auth', __name__, template_folder='../templates')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('auth.profile'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Passwords do not match.')
            return redirect(url_for('auth.register'))

        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered.')
            return redirect(url_for('auth.register'))

        new_user = User(email=email)
        new_user.set_password(password)     # To hash the password
        db.session.add(new_user)
        db.session.commit()

        flash('Account created successfully! Please log in.')
        return redirect(url_for('auth.login'))

    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('auth.profile'))

    if request.method == 'POST':
        email = request.form.get('email')  
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()  
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully.')
            return redirect(url_for('auth.profile'))
        else:
            flash('Invalid email or password.')

    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile')
@login_required
def profile():
    return f"Hello, {current_user.email}! This is your profile."

@auth_bp.route('/users')
def list_users():
    users = User.query.all()
    return '<br>'.join([f"{u.id}: {u.email}" for u in users])
