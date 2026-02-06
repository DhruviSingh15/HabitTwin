from flask import Blueprint, render_template, url_for, flash, redirect, request
from flask_login import login_user, current_user, logout_user, login_required
from app import db
from app.models import User
from app.auth.forms import RegistrationForm, LoginForm, RequestResetForm, ResetPasswordForm
from datetime import datetime

auth = Blueprint('auth', __name__)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            join_date=datetime.utcnow()
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', title='Register', form=form)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            
            # Check if this is a new user (no full_name or bio)
            if not user.full_name or not user.bio:
                flash('Welcome to HabitTwin! Please complete your profile.', 'info')
                return redirect(url_for('main.profile'))
                
            return redirect(next_page) if next_page else redirect(url_for('main.home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('auth/login.html', title='Login', form=form)

@auth.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.home'))

@auth.route('/reset_password', methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        # In a real app, you would send an email with a reset token
        # For this demo, we'll just flash a message
        flash('If an account with that email exists, a password reset email would be sent.', 'info')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_request.html', title='Reset Password', form=form)

@auth.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    # In a real app, you would verify the token and get the user
    # For this demo, we'll just redirect to login
    flash('Invalid or expired token', 'warning')
    return redirect(url_for('auth.reset_request'))
