from flask import Blueprint, render_template, url_for, flash, redirect, request
from flask_login import login_required, current_user
from app import db
from app.models import Habit, HabitLog, DigitalTwin
from app.habits.forms import HabitForm, HabitLogForm
from datetime import datetime, timedelta
import random

habits = Blueprint('habits', __name__)

@habits.route('/habits')
@login_required
def view_habits():
    user_habits = Habit.query.filter_by(user_id=current_user.id).all()
    return render_template('habits/habits.html', title='My Habits', habits=user_habits)

@habits.route('/habits/new', methods=['GET', 'POST'])
@login_required
def new_habit():
    form = HabitForm()
    if form.validate_on_submit():
        habit = Habit(
            name=form.name.data,
            description=form.description.data,
            frequency=form.frequency.data,
            goal=form.goal.data,
            user_id=current_user.id
        )
        db.session.add(habit)
        db.session.commit()
        
        # Create a digital twin for this habit
        digital_twin = DigitalTwin(
            user_id=current_user.id,
            habit_id=habit.id,
            completion_rate=random.uniform(0.6, 0.9),  # Random initial completion rate
            streak=random.randint(0, 5)  # Random initial streak
        )
        db.session.add(digital_twin)
        db.session.commit()
        
        flash('Your habit has been created!', 'success')
        return redirect(url_for('habits.view_habits'))
    return render_template('habits/create_habit.html', title='New Habit', form=form, legend='New Habit')

@habits.route('/habits/<int:habit_id>')
@login_required
def habit(habit_id):
    habit = Habit.query.get_or_404(habit_id)
    if habit.user_id != current_user.id:
        flash('You do not have permission to view this habit.', 'danger')
        return redirect(url_for('habits.view_habits'))
    
    # Get habit logs for the past 30 days
    today = datetime.utcnow().date()
    thirty_days_ago = today - timedelta(days=30)
    logs = HabitLog.query.filter_by(
        habit_id=habit.id
    ).filter(
        HabitLog.date >= thirty_days_ago
    ).order_by(HabitLog.date.desc()).all()
    
    # Calculate streak
    streak = habit.current_streak()
    
    # Calculate completion rate
    completion_rate = habit.completion_rate()
    
    # Get digital twin data
    digital_twin = DigitalTwin.query.filter_by(habit_id=habit.id, user_id=current_user.id).first()
    
    # Pre-calculate dates for the template
    date_logs = {}
    for i in range(30):
        day_date = (today - timedelta(days=i)).strftime('%Y-%m-%d')
        day_log = next((log for log in logs if log.date.strftime('%Y-%m-%d') == day_date), None)
        date_logs[i] = {
            'date': day_date,
            'log': day_log
        }
    
    return render_template(
        'habits/habit.html', 
        title=habit.name, 
        habit=habit, 
        logs=logs, 
        streak=streak, 
        completion_rate=completion_rate,
        digital_twin=digital_twin,
        today=today,
        date_logs=date_logs
    )

@habits.route('/habits/<int:habit_id>/update', methods=['GET', 'POST'])
@login_required
def update_habit(habit_id):
    habit = Habit.query.get_or_404(habit_id)
    if habit.user_id != current_user.id:
        flash('You do not have permission to update this habit.', 'danger')
        return redirect(url_for('habits.view_habits'))
    
    form = HabitForm()
    if form.validate_on_submit():
        habit.name = form.name.data
        habit.description = form.description.data
        habit.frequency = form.frequency.data
        habit.goal = form.goal.data
        db.session.commit()
        flash('Your habit has been updated!', 'success')
        return redirect(url_for('habits.habit', habit_id=habit.id))
    elif request.method == 'GET':
        form.name.data = habit.name
        form.description.data = habit.description
        form.frequency.data = habit.frequency
        form.goal.data = habit.goal
    
    return render_template('habits/create_habit.html', title='Update Habit', form=form, legend='Update Habit')

@habits.route('/habits/<int:habit_id>/delete', methods=['POST'])
@login_required
def delete_habit(habit_id):
    habit = Habit.query.get_or_404(habit_id)
    if habit.user_id != current_user.id:
        flash('You do not have permission to delete this habit.', 'danger')
        return redirect(url_for('habits.view_habits'))
    
    # Delete associated logs
    HabitLog.query.filter_by(habit_id=habit.id).delete()
    
    # Delete digital twin
    DigitalTwin.query.filter_by(habit_id=habit.id, user_id=current_user.id).delete()
    
    # Delete habit
    db.session.delete(habit)
    db.session.commit()
    flash('Your habit has been deleted!', 'success')
    return redirect(url_for('habits.view_habits'))

@habits.route('/habits/<int:habit_id>/log', methods=['GET', 'POST'])
@login_required
def log_habit(habit_id):
    habit = Habit.query.get_or_404(habit_id)
    if habit.user_id != current_user.id:
        flash('You do not have permission to log this habit.', 'danger')
        return redirect(url_for('habits.view_habits'))
    
    form = HabitLogForm()
    today = datetime.utcnow().date()
    
    # Check if there's already a log for today
    existing_log = HabitLog.query.filter_by(
        habit_id=habit.id,
        user_id=current_user.id,
        date=today
    ).first()
    
    if form.validate_on_submit():
        if existing_log:
            existing_log.completed = form.completed.data
            existing_log.notes = form.notes.data
            db.session.commit()
            flash('Your habit log has been updated!', 'success')
        else:
            log = HabitLog(
                habit_id=habit.id,
                user_id=current_user.id,
                completed=form.completed.data,
                notes=form.notes.data,
                date=today
            )
            db.session.add(log)
            db.session.commit()
            flash('Your habit has been logged!', 'success')
            
            # Update digital twin (AI rival)
            digital_twin = DigitalTwin.query.filter_by(habit_id=habit.id, user_id=current_user.id).first()
            if digital_twin:
                # AI has a chance to complete the habit based on its completion rate
                ai_completed = random.random() < digital_twin.completion_rate
                if ai_completed:
                    digital_twin.streak += 1
                else:
                    digital_twin.streak = 0
                digital_twin.last_updated = datetime.utcnow()
                db.session.commit()
            
        return redirect(url_for('habits.habit', habit_id=habit.id))
    elif request.method == 'GET' and existing_log:
        form.completed.data = existing_log.completed
        form.notes.data = existing_log.notes
    
    # Get recent logs for this habit (last 5)  
    habit_logs = HabitLog.query.filter_by(
        habit_id=habit.id,
        user_id=current_user.id
    ).order_by(HabitLog.date.desc()).limit(5).all()
    
    # Get digital twin logs for the last 7 days
    twin_logs = {}
    digital_twin = DigitalTwin.query.filter_by(habit_id=habit.id, user_id=current_user.id).first()
    
    if digital_twin:
        # Calculate twin completion rate
        twin_completion_rate = int(digital_twin.completion_rate * 100)
        
        # Generate some fake logs for the last 7 days
        for i in range(7):
            log_date = today - timedelta(days=i)
            date_str = log_date.strftime('%Y-%m-%d')
            # Twin completes habit based on its completion rate
            twin_logs[date_str] = random.random() < digital_twin.completion_rate
    else:
        twin_completion_rate = 0
    
    return render_template('habits/log_habit.html', 
                           title='Log Habit', 
                           form=form, 
                           habit=habit, 
                           today=today,
                           log_exists=existing_log is not None,
                           existing_log=existing_log,
                           habit_logs=habit_logs,
                           twin_logs=twin_logs,
                           twin_completion_rate=twin_completion_rate,
                           timedelta=timedelta)

@habits.route('/habits/calendar')
@habits.route('/habits/calendar/<int:year>/<int:month>')
@login_required
def habit_calendar(year=None, month=None):
    # Get all habits
    user_habits = Habit.query.filter_by(user_id=current_user.id).all()
    
    # Get current date for reference
    today = datetime.utcnow().date()
    
    # Determine which month to display
    if year is None or month is None:
        # Default to current month if no parameters
        year = today.year
        month = today.month
    
    # Create date objects for the start and end of the selected month
    start_of_month = datetime(year, month, 1).date()
    
    # Calculate the end of the month
    if month == 12:
        end_of_month = datetime(year + 1, 1, 1).date() - timedelta(days=1)
    else:
        end_of_month = datetime(year, month + 1, 1).date() - timedelta(days=1)
    
    # Calculate previous and next month for navigation
    if month == 1:
        prev_month = 12
        prev_year = year - 1
    else:
        prev_month = month - 1
        prev_year = year
        
    if month == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month + 1
        next_year = year
    
    # Get logs for the selected month
    logs = HabitLog.query.filter_by(
        user_id=current_user.id
    ).filter(
        HabitLog.date >= start_of_month,
        HabitLog.date <= end_of_month
    ).all()
    
    # Organize logs by date and habit
    calendar_data = {}
    for log in logs:
        date_str = log.date.strftime('%Y-%m-%d')
        if date_str not in calendar_data:
            calendar_data[date_str] = {}
        calendar_data[date_str][log.habit_id] = log.completed
    
    # Calculate the number of days in the month
    num_days = (end_of_month - start_of_month).days + 1
    
    # Pre-calculate date range for the template
    date_range = []
    for i in range(num_days):
        day = start_of_month + timedelta(days=i)
        date_range.append({
            'date': day,
            'date_str': day.strftime('%Y-%m-%d'),
            'day': day.strftime('%d'),
            'weekday': day.strftime('%a')[:1]
        })
    
    # Calculate completion statistics for the selected month
    total_logs = len(logs)
    completed_logs = sum(1 for log in logs if log.completed)
    completion_rate = round((completed_logs / total_logs) * 100) if total_logs > 0 else 0
    
    # Calculate completion rate change (compared to previous month)
    prev_month_start = start_of_month - timedelta(days=1)
    if prev_month_start.month == 12:
        prev_month_start_full = datetime(prev_month_start.year - 1, prev_month_start.month, 1).date()
    else:
        prev_month_start_full = datetime(prev_month_start.year, prev_month_start.month, 1).date()
    
    prev_month_logs = HabitLog.query.filter_by(
        user_id=current_user.id
    ).filter(
        HabitLog.date >= prev_month_start_full,
        HabitLog.date < start_of_month
    ).all()
    
    prev_total_logs = len(prev_month_logs)
    prev_completed_logs = sum(1 for log in prev_month_logs if log.completed)
    prev_completion_rate = round((prev_completed_logs / prev_total_logs) * 100) if prev_total_logs > 0 else 0
    
    # Calculate the change
    completion_rate_change = completion_rate - prev_completion_rate
    
    # Find the best streak in the selected month
    best_streak = 0
    for habit in user_habits:
        habit_logs = [log for log in logs if log.habit_id == habit.id]
        habit_logs.sort(key=lambda x: x.date)
        
        current_streak = 0
        for log in habit_logs:
            if log.completed:
                current_streak += 1
                best_streak = max(best_streak, current_streak)
            else:
                current_streak = 0
    
    # Find the most consistent habit in the selected month
    most_consistent = {'name': 'None', 'rate': 0}
    for habit in user_habits:
        habit_logs = [log for log in logs if log.habit_id == habit.id]
        if habit_logs:
            completed = sum(1 for log in habit_logs if log.completed)
            rate = round((completed / len(habit_logs)) * 100) if habit_logs else 0
            if rate > most_consistent['rate']:
                most_consistent = {'name': habit.name, 'rate': rate}
    
    # Format the selected month for display
    selected_month = datetime(year, month, 1).strftime('%B %Y')
    
    return render_template(
        'habits/habit_calendar.html', 
        title='Habit Calendar', 
        habits=user_habits, 
        logs=logs,
        calendar_data=calendar_data,
        today=today,
        start_of_month=start_of_month,
        end_of_month=end_of_month,
        date_range=date_range,
        selected_month=selected_month,
        year=year,
        month=month,
        prev_month=prev_month,
        prev_year=prev_year,
        next_month=next_month,
        next_year=next_year,
        completion_rate=completion_rate,
        completion_rate_change=completion_rate_change,
        best_streak=best_streak,
        most_consistent=most_consistent
    )
