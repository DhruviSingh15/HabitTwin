from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from app import db
from app.models import Habit, HabitLog, ScreenTimeLog, Achievement, UserAchievement
from datetime import datetime, timedelta
import os
import secrets
from PIL import Image

main = Blueprint('main', __name__)

def save_picture(form_picture):
    """Save profile picture with a random name and resize it"""
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(os.path.abspath(os.path.dirname('__file__')), 'app/static/img/profile', picture_fn)
    
    # Resize image to save space and load faster
    output_size = (300, 300)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(picture_path), exist_ok=True)
    
    # Save the picture
    i.save(picture_path)
    
    return picture_fn

@main.route('/')
@main.route('/home')
def home():
    if current_user.is_authenticated:
        # Get user's habits
        habits = Habit.query.filter_by(user_id=current_user.id).all()
        
        # Get recent habit logs
        today = datetime.utcnow().date()
        recent_logs = HabitLog.query.filter_by(
            user_id=current_user.id
        ).filter(
            HabitLog.date >= today - timedelta(days=7)
        ).order_by(HabitLog.date.desc()).all()
        
        # Calculate total streak (sum of all habits' current streaks)
        total_streak = sum(habit.current_streak() for habit in habits) if habits else 0
        
        # Calculate completion rate for the past 7 days
        past_week_logs = HabitLog.query.filter_by(
            user_id=current_user.id
        ).filter(
            HabitLog.date >= today - timedelta(days=7),
            HabitLog.date <= today
        ).all()
        
        completion_rate = 0
        if past_week_logs:
            completed_logs = sum(1 for log in past_week_logs if log.completed)
            completion_rate = round((completed_logs / len(past_week_logs)) * 100) if past_week_logs else 0
        
        # Get screen time summary
        screen_time = ScreenTimeLog.query.filter_by(
            user_id=current_user.id
        ).filter(
            ScreenTimeLog.date >= today - timedelta(days=7)
        ).all()
        
        # Get total screen time
        total_screen_time = sum(log.usage_minutes for log in screen_time)
        
        # Get top apps
        app_usage = {}
        for log in screen_time:
            if log.app_name in app_usage:
                app_usage[log.app_name] += log.usage_minutes
            else:
                app_usage[log.app_name] = log.usage_minutes
        
        top_apps = sorted(app_usage.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Get recent achievements
        achievements = UserAchievement.query.filter_by(
            user_id=current_user.id
        ).order_by(UserAchievement.earned_date.desc()).limit(5).all()
        
        return render_template(
            'main/dashboard.html',
            title='Dashboard',
            habits=habits,
            recent_logs=recent_logs,
            total_screen_time=total_screen_time,
            top_apps=top_apps,
            achievements=achievements,
            total_streak=total_streak,
            completion_rate=completion_rate,
            now=datetime.utcnow()
        )
    else:
        return render_template('main/index.html', title='Welcome to HabitTwin')

@main.route('/about')
def about():
    return render_template('main/about.html', title='About HabitTwin')

@main.route('/features')
def features():
    return render_template('main/features.html', title='Features')

@main.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        # Update user profile information
        current_user.full_name = request.form.get('full_name')
        current_user.age = request.form.get('age')
        current_user.hobbies = request.form.get('hobbies')
        current_user.bio = request.form.get('bio')
        
        # Handle profile picture upload
        if 'profile_pic' in request.files and request.files['profile_pic'].filename:
            picture_file = save_picture(request.files['profile_pic'])
            current_user.profile_pic = picture_file
        
        db.session.commit()
        flash('Your profile has been updated!', 'success')
        return redirect(url_for('main.profile'))
    
    return render_template('main/profile.html', title='My Profile')
