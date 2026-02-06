import os
import secrets
import pandas as pd
from datetime import datetime
from flask import Blueprint, render_template, url_for, flash, redirect, request, current_app
from flask_login import login_required, current_user
from app import db
from app.models import ScreenTimeLog, AppLimit
from app.wellbeing.forms import UploadScreenTimeForm, DigitalDetoxForm, AppLimitForm

wellbeing = Blueprint('wellbeing', __name__)

def save_excel_file(form_excel):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_excel.filename)
    excel_fn = random_hex + f_ext
    excel_path = os.path.join(current_app.root_path, 'static/uploads/excel_files', excel_fn)
    form_excel.save(excel_path)
    return excel_fn, excel_path

def parse_excel_file(file_path):
    try:
        # Read the Excel file
        df = pd.read_excel(file_path)
        
        # Check if the required columns exist
        required_columns = ['Date', 'App Name', 'Usage (Minutes)']
        for col in required_columns:
            if col not in df.columns:
                return False, f"Missing required column: {col}"
        
        # Validate data types
        try:
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            df['Usage (Minutes)'] = df['Usage (Minutes)'].astype(int)
        except Exception as e:
            return False, f"Data type error: {str(e)}"
        
        # Return the validated dataframe
        return True, df
    except Exception as e:
        return False, f"Error parsing Excel file: {str(e)}"

@wellbeing.route('/wellbeing')
@login_required
def digital_wellbeing():
    # Get current date for the dashboard
    from datetime import datetime
    today = datetime.now()
    
    # Get screen time logs for the past 30 days
    screen_time_logs = ScreenTimeLog.query.filter_by(user_id=current_user.id).order_by(ScreenTimeLog.date.desc()).all()
    
    # Calculate total screen time
    total_screen_time = sum(log.usage_minutes for log in screen_time_logs)
    
    # Get app usage by app
    app_usage = {}
    for log in screen_time_logs:
        if log.app_name in app_usage:
            app_usage[log.app_name] += log.usage_minutes
        else:
            app_usage[log.app_name] = log.usage_minutes
    
    # Sort apps by usage
    top_apps = sorted(app_usage.items(), key=lambda x: x[1], reverse=True)
    
    # Calculate daily average
    dates = set(log.date for log in screen_time_logs)
    daily_average = total_screen_time / len(dates) if dates else 0
    daily_average = daily_average / 60  # Convert to hours
    
    # Get existing app limits
    app_limits = AppLimit.query.filter_by(user_id=current_user.id).all()
    
    return render_template(
        'wellbeing/dashboard.html',
        title='Digital Wellbeing',
        screen_time_logs=screen_time_logs,
        total_screen_time=total_screen_time,
        top_apps=top_apps,
        daily_average=daily_average,
        today=today,
        app_limits=app_limits
    )

@wellbeing.route('/wellbeing/app-limits', methods=['GET', 'POST'])
@login_required
def app_limits():
    form = AppLimitForm()
    
    # Get user's existing app limits
    existing_limits = AppLimit.query.filter_by(user_id=current_user.id).all()
    
    # Get app usage data for suggestions
    screen_time_logs = ScreenTimeLog.query.filter_by(user_id=current_user.id).all()
    app_usage = {}
    for log in screen_time_logs:
        if log.app_name in app_usage:
            app_usage[log.app_name] += log.usage_minutes
        else:
            app_usage[log.app_name] = log.usage_minutes
    
    # Sort apps by usage for suggestions
    top_apps = sorted(app_usage.items(), key=lambda x: x[1], reverse=True)
    
    if form.validate_on_submit():
        # Check if limit already exists for this app
        existing_limit = AppLimit.query.filter_by(
            user_id=current_user.id,
            app_name=form.app_name.data
        ).first()
        
        if existing_limit:
            # Update existing limit
            existing_limit.daily_limit_minutes = form.daily_limit_minutes.data
            existing_limit.is_active = True
            db.session.commit()
            flash(f'App limit updated for {form.app_name.data}', 'success')
        else:
            # Create new limit
            app_limit = AppLimit(
                app_name=form.app_name.data,
                daily_limit_minutes=form.daily_limit_minutes.data,
                user_id=current_user.id
            )
            db.session.add(app_limit)
            db.session.commit()
            flash(f'App limit set for {form.app_name.data}', 'success')
        
        return redirect(url_for('wellbeing.app_limits'))
    
    return render_template(
        'wellbeing/app_limits.html',
        title='App Usage Limits',
        form=form,
        existing_limits=existing_limits,
        top_apps=top_apps[:10]  # Show top 10 apps for suggestions
    )

@wellbeing.route('/wellbeing/app-limits/delete/<int:limit_id>', methods=['POST'])
@login_required
def delete_app_limit(limit_id):
    app_limit = AppLimit.query.get_or_404(limit_id)
    
    # Ensure the limit belongs to the current user
    if app_limit.user_id != current_user.id:
        flash('You do not have permission to delete this limit', 'danger')
        return redirect(url_for('wellbeing.app_limits'))
    
    app_name = app_limit.app_name
    db.session.delete(app_limit)
    db.session.commit()
    
    flash(f'App limit for {app_name} has been removed', 'success')
    return redirect(url_for('wellbeing.app_limits'))

@wellbeing.route('/wellbeing/app-limits/toggle/<int:limit_id>', methods=['POST'])
@login_required
def toggle_app_limit(limit_id):
    app_limit = AppLimit.query.get_or_404(limit_id)
    
    # Ensure the limit belongs to the current user
    if app_limit.user_id != current_user.id:
        flash('You do not have permission to modify this limit', 'danger')
        return redirect(url_for('wellbeing.app_limits'))
    
    # Toggle the active status
    app_limit.is_active = not app_limit.is_active
    db.session.commit()
    
    status = 'activated' if app_limit.is_active else 'deactivated'
    flash(f'App limit for {app_limit.app_name} has been {status}', 'success')
    return redirect(url_for('wellbeing.app_limits'))

@wellbeing.route('/wellbeing/upload', methods=['GET', 'POST'])
@login_required
def upload_screen_time():
    form = UploadScreenTimeForm()
    if form.validate_on_submit():
        excel_fn, excel_path = save_excel_file(form.excel_file.data)
        
        # Parse the Excel file
        success, result = parse_excel_file(excel_path)
        
        if success:
            df = result
            
            # Save data to database
            for _, row in df.iterrows():
                log = ScreenTimeLog(
                    date=row['Date'],
                    app_name=row['App Name'],
                    usage_minutes=row['Usage (Minutes)'],
                    upload_file=excel_fn,
                    user_id=current_user.id
                )
                db.session.add(log)
            
            db.session.commit()
            flash('Your screen time data has been uploaded successfully!', 'success')
            return redirect(url_for('wellbeing.digital_wellbeing'))
        else:
            flash(f'Error: {result}', 'danger')
    
    return render_template('wellbeing/upload.html', title='Upload Screen Time', form=form)

@wellbeing.route('/wellbeing/detox', methods=['GET', 'POST'])
@login_required
def digital_detox():
    from app.models import DigitalDetoxPlan
    
    # Check if user already has an active detox plan
    active_plan = DigitalDetoxPlan.query.filter_by(user_id=current_user.id, is_active=True).first()
    
    # Pre-populate form with active plan data if it exists
    form = DigitalDetoxForm()
    if active_plan and request.method == 'GET':
        form.daily_limit.data = active_plan.daily_limit_minutes
        form.enable_app_blocking.data = active_plan.enable_app_blocking
        form.enable_notifications.data = active_plan.enable_notifications
        form.enable_break_reminders.data = active_plan.enable_break_reminders
        form.break_interval_minutes.data = active_plan.break_interval_minutes
    
    # Get current screen time data
    screen_time_logs = ScreenTimeLog.query.filter_by(user_id=current_user.id).order_by(ScreenTimeLog.date.desc()).all()
    
    # Calculate total screen time
    total_screen_time = sum(log.usage_minutes for log in screen_time_logs)
    
    # Get app usage by app
    app_usage = {}
    for log in screen_time_logs:
        if log.app_name in app_usage:
            app_usage[log.app_name] += log.usage_minutes
        else:
            app_usage[log.app_name] = log.usage_minutes
    
    # Sort apps by usage
    top_apps = sorted(app_usage.items(), key=lambda x: x[1], reverse=True)
    
    # Generate detox suggestions
    detox_suggestions = []
    for app, minutes in top_apps[:3]:
        if minutes > 60:
            detox_suggestions.append(f"Reduce {app} usage by {int(minutes * 0.3)} minutes")
    
    if form.validate_on_submit():
        if active_plan:
            # Update existing plan
            active_plan.daily_limit_minutes = form.daily_limit.data
            active_plan.enable_app_blocking = form.enable_app_blocking.data
            active_plan.enable_notifications = form.enable_notifications.data
            active_plan.enable_break_reminders = form.enable_break_reminders.data
            active_plan.break_interval_minutes = form.break_interval_minutes.data
            db.session.commit()
            flash('Your Digital Detox plan has been updated!', 'success')
        else:
            # Create new detox plan
            new_plan = DigitalDetoxPlan(
                daily_limit_minutes=form.daily_limit.data,
                enable_app_blocking=form.enable_app_blocking.data,
                enable_notifications=form.enable_notifications.data,
                enable_break_reminders=form.enable_break_reminders.data,
                break_interval_minutes=form.break_interval_minutes.data,
                user_id=current_user.id
            )
            db.session.add(new_plan)
            db.session.commit()
            flash('Your Digital Detox plan has been created!', 'success')
        
        return redirect(url_for('wellbeing.digital_detox'))
    
    return render_template(
        'wellbeing/detox.html',
        title='Digital Detox',
        form=form,
        top_apps=top_apps,
        total_screen_time=total_screen_time,
        detox_suggestions=detox_suggestions,
        active_plan=active_plan
    )

@wellbeing.route('/wellbeing/detox/deactivate/<int:plan_id>', methods=['POST'])
@login_required
def deactivate_detox_plan(plan_id):
    from app.models import DigitalDetoxPlan
    
    detox_plan = DigitalDetoxPlan.query.get_or_404(plan_id)
    
    # Ensure the plan belongs to the current user
    if detox_plan.user_id != current_user.id:
        flash('You do not have permission to modify this detox plan', 'danger')
        return redirect(url_for('wellbeing.digital_detox'))
    
    detox_plan.is_active = False
    detox_plan.end_date = datetime.now().date()
    db.session.commit()
    
    flash('Your Digital Detox plan has been deactivated', 'success')
    return redirect(url_for('wellbeing.digital_detox'))

@wellbeing.route('/wellbeing/detox/challenge', methods=['GET', 'POST'])
@login_required
def start_detox_challenge():
    from app.models import DigitalDetoxPlan
    from datetime import datetime, timedelta
    
    # Check if user has an active detox plan with app blocking enabled
    active_plan = DigitalDetoxPlan.query.filter_by(
        user_id=current_user.id, 
        is_active=True, 
        enable_app_blocking=True
    ).first()
    
    if not active_plan:
        flash('You need an active detox plan with app blocking enabled to start the challenge', 'warning')
        return redirect(url_for('wellbeing.digital_detox'))
    
    # Get screen time data for personalized challenge suggestions
    screen_time_logs = ScreenTimeLog.query.filter_by(user_id=current_user.id).order_by(ScreenTimeLog.date.desc()).all()
    
    # Calculate total screen time
    total_screen_time = sum(log.usage_minutes for log in screen_time_logs)
    
    # Get app usage by app
    app_usage = {}
    for log in screen_time_logs:
        if log.app_name in app_usage:
            app_usage[log.app_name] += log.usage_minutes
        else:
            app_usage[log.app_name] = log.usage_minutes
    
    # Sort apps by usage
    top_apps = sorted(app_usage.items(), key=lambda x: x[1], reverse=True)[:5]  # Top 5 apps
    
    # Set challenge end time (24 hours from now)
    challenge_start = datetime.now()
    challenge_end = challenge_start + timedelta(hours=24)
    
    return render_template(
        'wellbeing/challenge.html',
        title='Digital Detox Challenge',
        active_plan=active_plan,
        top_apps=top_apps,
        challenge_start=challenge_start,
        challenge_end=challenge_end,
        total_screen_time=total_screen_time
    )

@wellbeing.route('/wellbeing/history')
@login_required
def screen_time_history():
    # Get all screen time uploads
    uploads = ScreenTimeLog.query.filter_by(user_id=current_user.id).with_entities(
        ScreenTimeLog.upload_file, ScreenTimeLog.uploaded_at
    ).distinct().order_by(ScreenTimeLog.uploaded_at.desc()).all()
    
    return render_template(
        'wellbeing/history.html',
        title='Upload History',
        uploads=uploads
    )
