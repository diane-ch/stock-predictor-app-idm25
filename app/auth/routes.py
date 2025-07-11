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
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        finance_level = request.form.get('finance_level')

        # Verify if user exists
        user = User.query.filter((User.username == username) | (User.email == email)).first()
        if user:
            flash('Username or email already exists.')
            return redirect(url_for('auth.register'))

        new_user = User(username=username, email=email, finance_level=finance_level)
        new_user.set_password(password) # To hash the password

        db.session.add(new_user)    # Adds the user to the database
        db.session.commit()
        flash('Account created! Please log in.')
        return redirect(url_for('auth.login'))

    # If method is "GET", simply return the form.
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('auth.profile'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully.')
            return redirect(url_for('auth.profile'))
        else:
            flash('Invalid username or password.')

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
    return f"Hello, {current_user.username}! This is your profile."

@auth_bp.route('/users')
def list_users():
    users = User.query.all()
    return '<br>'.join([f"{u.id}: {u.username} ({u.email})" for u in users])
