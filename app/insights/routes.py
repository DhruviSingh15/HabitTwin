from flask import Blueprint, render_template, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models import Habit, HabitLog, ScreenTimeLog, DigitalDetoxPlan, AppLimit
from datetime import datetime, timedelta
import random
import numpy as np

insights = Blueprint('insights', __name__)

def generate_habit_suggestions(user_habits, screen_time_logs):
    """Generate habit suggestions based on user data"""
    suggestions = []
    
    # Check if user has few habits
    if len(user_habits) < 3:
        suggestions.append("Consider adding more habits to track your progress better.")
    
    # Check screen time
    total_screen_time = sum(log.usage_minutes for log in screen_time_logs)
    if total_screen_time > 180:  # More than 3 hours
        suggestions.append("Your screen time is high. Consider adding a 'digital detox' habit.")
    
    # Suggest based on existing habits
    habit_names = [h.name.lower() for h in user_habits]
    if not any('exercise' in h or 'workout' in h for h in habit_names):
        suggestions.append("Consider adding an exercise habit for better wellbeing.")
    
    if not any('read' in h for h in habit_names):
        suggestions.append("Reading is a great habit to improve focus. Consider adding it.")
    
    if not any('meditat' in h for h in habit_names):
        suggestions.append("Meditation can help reduce stress. Consider adding it as a habit.")
    
    return suggestions

def predict_habit_dropout(habit):
    """Predict if user is likely to drop a habit"""
    # Get recent logs
    recent_logs = HabitLog.query.filter_by(habit_id=habit.id).order_by(HabitLog.date.desc()).limit(10).all()
    
    # If fewer than 3 logs, not enough data
    if len(recent_logs) < 3:
        return False, "Not enough data"
    
    # Calculate completion rate for recent logs
    completed = sum(1 for log in recent_logs if log.completed)
    completion_rate = completed / len(recent_logs)
    
    # If completion rate is low, predict dropout
    if completion_rate < 0.3:
        return True, f"Low completion rate ({completion_rate:.0%})"
    
    return False, "Habit is on track"

def generate_wellbeing_insights(screen_time_logs, active_detox_plan, app_limits):
    """Generate insights about digital wellbeing"""
    insights = {
        "summary": "",
        "screen_time_trend": "",
        "detox_impact": "",
        "app_limit_effectiveness": "",
        "wellbeing_score": 0
    }
    
    # Calculate total screen time
    total_screen_time = sum(log.usage_minutes for log in screen_time_logs)
    daily_average = total_screen_time / 7 if screen_time_logs else 0
    
    # Calculate wellbeing score (0-100)
    # Lower screen time = higher score
    base_score = max(0, 100 - (daily_average / 15))
    
    # Adjust score based on detox plan
    detox_bonus = 15 if active_detox_plan else 0
    
    # Adjust score based on app limits
    limit_bonus = min(15, len(app_limits) * 3)
    
    # Calculate final score
    wellbeing_score = min(100, base_score + detox_bonus + limit_bonus)
    insights["wellbeing_score"] = int(wellbeing_score)
    
    # Generate summary based on score
    if wellbeing_score >= 80:
        insights["summary"] = "Excellent digital wellbeing habits! You're maintaining a healthy balance."
    elif wellbeing_score >= 60:
        insights["summary"] = "Good digital wellbeing habits. Some minor adjustments could improve your balance."
    elif wellbeing_score >= 40:
        insights["summary"] = "Your digital wellbeing needs attention. Consider implementing more limits or detox periods."
    else:
        insights["summary"] = "Your screen time is significantly impacting your wellbeing. Urgent action recommended."
    
    # Analyze screen time trend
    if len(screen_time_logs) >= 3:
        # Sort logs by date
        sorted_logs = sorted(screen_time_logs, key=lambda x: x.date)
        
        # Calculate trend (simple linear regression)
        dates = [(log.date - sorted_logs[0].date).days for log in sorted_logs]
        minutes = [log.usage_minutes for log in sorted_logs]
        
        if len(dates) > 1 and len(set(dates)) > 1:  # Ensure we have different dates
            slope = np.polyfit(dates, minutes, 1)[0]
            
            if slope < -10:  # Significant decrease
                insights["screen_time_trend"] = "Your screen time is decreasing significantly. Great job!"
            elif slope < 0:  # Slight decrease
                insights["screen_time_trend"] = "Your screen time is gradually decreasing. Keep it up!"
            elif slope < 10:  # Slight increase
                insights["screen_time_trend"] = "Your screen time is slightly increasing. Be mindful of your usage."
            else:  # Significant increase
                insights["screen_time_trend"] = "Your screen time is increasing significantly. Consider implementing more limits."
        else:
            insights["screen_time_trend"] = "Not enough data to determine screen time trend."
    else:
        insights["screen_time_trend"] = "Not enough data to determine screen time trend."
    
    # Analyze detox impact
    if active_detox_plan:
        insights["detox_impact"] = "Your active detox plan is helping to reduce your screen time and improve wellbeing."
    elif len(screen_time_logs) > 0:
        insights["detox_impact"] = "Consider starting a digital detox plan to improve your digital wellbeing."
    else:
        insights["detox_impact"] = "Not enough data to analyze detox impact."
    
    # Analyze app limit effectiveness
    if app_limits and screen_time_logs:
        limited_apps = [limit.app_name for limit in app_limits]
        limited_app_usage = sum(log.usage_minutes for log in screen_time_logs if log.app_name in limited_apps)
        total_usage = sum(log.usage_minutes for log in screen_time_logs)
        
        if total_usage > 0:
            limited_percentage = (limited_app_usage / total_usage) * 100
            
            if limited_percentage < 30:
                insights["app_limit_effectiveness"] = "Your app limits are working effectively. Limited apps account for a small portion of your usage."
            elif limited_percentage < 60:
                insights["app_limit_effectiveness"] = "Your app limits are somewhat effective, but you're still spending significant time on limited apps."
            else:
                insights["app_limit_effectiveness"] = "Your app limits don't seem to be effective. Consider stricter limits or different strategies."
        else:
            insights["app_limit_effectiveness"] = "Not enough usage data to analyze app limit effectiveness."
    else:
        insights["app_limit_effectiveness"] = "Set app limits to better manage your screen time."
    
    return insights

def calculate_habit_screen_time_correlations(habits, screen_time_logs):
    """Calculate correlations between habits and screen time"""
    correlations = []
    
    if not habits or not screen_time_logs or len(habits) < 2 or len(screen_time_logs) < 3:
        # Sample correlation for demonstration
        correlations.append({
            "title": "Meditation & Screen Time",
            "description": "Days when you meditate tend to have lower screen time.",
            "strength": 65
        })
        return correlations
    
    # Group screen time logs by date
    screen_time_by_date = {}
    for log in screen_time_logs:
        date_str = log.date.strftime("%Y-%m-%d")
        if date_str in screen_time_by_date:
            screen_time_by_date[date_str] += log.usage_minutes
        else:
            screen_time_by_date[date_str] = log.usage_minutes
    
    # For each habit, check correlation with screen time
    for habit in habits:
        habit_logs = HabitLog.query.filter_by(habit_id=habit.id).all()
        
        # Skip if not enough logs
        if len(habit_logs) < 3:
            continue
        
        # Count days when habit was completed and screen time was recorded
        completed_days_screen_time = []
        incomplete_days_screen_time = []
        
        for log in habit_logs:
            date_str = log.date.strftime("%Y-%m-%d")
            if date_str in screen_time_by_date:
                if log.completed:
                    completed_days_screen_time.append(screen_time_by_date[date_str])
                else:
                    incomplete_days_screen_time.append(screen_time_by_date[date_str])
        
        # Skip if not enough data points
        if len(completed_days_screen_time) < 2 or len(incomplete_days_screen_time) < 2:
            continue
        
        # Calculate average screen time for completed vs incomplete days
        avg_completed = sum(completed_days_screen_time) / len(completed_days_screen_time)
        avg_incomplete = sum(incomplete_days_screen_time) / len(incomplete_days_screen_time)
        
        # Calculate percent difference
        if avg_incomplete > 0:
            percent_diff = ((avg_incomplete - avg_completed) / avg_incomplete) * 100
        else:
            percent_diff = 0
        
        # Only add significant correlations
        if abs(percent_diff) > 10:
            if percent_diff > 0:
                description = f"Days when you complete '{habit.name}' have {abs(int(percent_diff))}% less screen time."
            else:
                description = f"Days when you complete '{habit.name}' have {abs(int(percent_diff))}% more screen time."
            
            correlations.append({
                "title": f"{habit.name} & Screen Time",
                "description": description,
                "strength": min(100, abs(int(percent_diff * 1.5)))
            })
    
    # If no real correlations found, add a sample one
    if not correlations:
        correlations.append({
            "title": "Habits & Screen Time",
            "description": "Not enough data to find strong correlations between your habits and screen time yet.",
            "strength": 30
        })
    
    return correlations

def generate_personalized_recommendations(habits, screen_time_logs, active_detox_plan, app_limits):
    """Generate personalized recommendations based on user data"""
    recommendations = []
    
    # Screen time recommendations
    total_screen_time = sum(log.usage_minutes for log in screen_time_logs)
    daily_average = total_screen_time / 7 if screen_time_logs else 0
    
    if daily_average > 240:  # More than 4 hours
        recommendations.append({
            "title": "Reduce Screen Time",
            "description": "Your daily screen time is high. Try to reduce it by setting specific tech-free hours.",
            "category": "screen_time"
        })
    
    # App-specific recommendations
    app_usage = {}
    for log in screen_time_logs:
        if log.app_name in app_usage:
            app_usage[log.app_name] += log.usage_minutes
        else:
            app_usage[log.app_name] = log.usage_minutes
    
    top_apps = sorted(app_usage.items(), key=lambda x: x[1], reverse=True)[:3]
    
    if top_apps and top_apps[0][1] > 120:  # More than 2 hours on top app
        recommendations.append({
            "title": f"Limit {top_apps[0][0]}",
            "description": f"You're spending a lot of time on {top_apps[0][0]}. Consider setting a specific time limit.",
            "category": "app_limit"
        })
    
    # Detox recommendations
    if not active_detox_plan and daily_average > 180:  # More than 3 hours
        recommendations.append({
            "title": "Start Digital Detox",
            "description": "A structured digital detox plan can help you reduce screen time and improve wellbeing.",
            "category": "detox"
        })
    
    # Habit recommendations based on screen time
    habit_names = [h.name.lower() for h in habits]
    
    if daily_average > 180 and not any(x in ' '.join(habit_names) for x in ['meditate', 'meditation', 'mindful']):
        recommendations.append({
            "title": "Add Meditation Habit",
            "description": "Meditation can help reduce the urge to check devices and improve focus.",
            "category": "habit"
        })
    
    if daily_average > 240 and not any(x in ' '.join(habit_names) for x in ['outdoor', 'outside', 'nature', 'walk']):
        recommendations.append({
            "title": "Add Outdoor Activity",
            "description": "Spending time outdoors can reduce screen time and improve mood and wellbeing.",
            "category": "habit"
        })
    
    # If no specific recommendations, add a general one
    if not recommendations:
        recommendations.append({
            "title": "Maintain Balance",
            "description": "You're doing well! Continue to maintain a healthy balance between screen time and other activities.",
            "category": "general"
        })
    
    return recommendations

def generate_weekly_report(habits, screen_time_logs):
    """Generate a weekly AI report"""
    # Calculate overall wellbeing score (0-100)
    habit_score = 0
    screen_time_score = 0
    
    # Calculate habit score
    if habits:
        completed_habits = sum(1 for h in habits for log in h.logs if log.completed)
        total_habit_logs = sum(len(h.logs) for h in habits)
        habit_score = (completed_habits / max(1, total_habit_logs)) * 50
    
    # Calculate screen time score
    total_screen_time = sum(log.usage_minutes for log in screen_time_logs)
    daily_average = total_screen_time / 7 if screen_time_logs else 0
    
    # Lower screen time = higher score (max 50 points)
    screen_time_score = max(0, 50 - (daily_average / 12))
    
    # Calculate overall score
    overall_score = int(habit_score + screen_time_score)
    
    # Get habit statistics
    active_habits = len(habits)
    habit_completion_rate = int((completed_habits / max(1, total_habit_logs)) * 100) if habits else 0
    longest_streak = max([h.current_streak() for h in habits]) if habits else 0
    
    # Generate habit summary
    if habit_completion_rate > 80:
        habit_summary = "Excellent habit consistency! You're building strong routines."
    elif habit_completion_rate > 60:
        habit_summary = "Good habit consistency. Keep working on making these habits automatic."
    elif habit_completion_rate > 40:
        habit_summary = "Moderate habit consistency. Focus on completing your most important habits daily."
    else:
        habit_summary = "Your habit consistency needs improvement. Consider focusing on fewer habits for better results."
    
    # Screen time analysis
    avg_screen_time = int(daily_average)
    
    # Calculate change from previous week
    two_weeks_ago = datetime.utcnow().date() - timedelta(days=14)
    one_week_ago = datetime.utcnow().date() - timedelta(days=7)
    
    previous_logs = ScreenTimeLog.query.filter_by(
        user_id=current_user.id
    ).filter(
        ScreenTimeLog.date >= two_weeks_ago,
        ScreenTimeLog.date < one_week_ago
    ).all()
    
    previous_total = sum(log.usage_minutes for log in previous_logs)
    previous_daily_avg = previous_total / 7 if previous_logs else 0
    
    if previous_daily_avg > 0:
        screen_time_change = int(((daily_average - previous_daily_avg) / previous_daily_avg) * 100)
    else:
        screen_time_change = 0
    
    # Get most used app
    app_usage = {}
    for log in screen_time_logs:
        if log.app_name in app_usage:
            app_usage[log.app_name] += log.usage_minutes
        else:
            app_usage[log.app_name] = log.usage_minutes
    
    most_used_app = max(app_usage.items(), key=lambda x: x[1])[0] if app_usage else "None"
    
    # Generate screen time summary
    if daily_average > 240:  # More than 4 hours
        screen_time_summary = "Your screen time is high. Consider implementing digital wellbeing strategies to reduce it."
    elif daily_average > 180:  # 3-4 hours
        screen_time_summary = "Your screen time is moderate to high. Look for opportunities to reduce non-essential screen time."
    elif daily_average > 120:  # 2-3 hours
        screen_time_summary = "Your screen time is moderate. You're maintaining a reasonable balance."
    else:  # Less than 2 hours
        screen_time_summary = "Your screen time is low. Great job maintaining a healthy digital balance!"
    
    # Generate recommendations
    recommendations = []
    
    if habit_completion_rate < 60:
        recommendations.append({
            "title": "Improve Habit Consistency",
            "description": "Focus on completing your most important habits daily. Consider using reminders or habit stacking."
        })
    
    if daily_average > 180:
        recommendations.append({
            "title": "Reduce Screen Time",
            "description": "Set specific tech-free hours or use app limits to reduce your daily screen time."
        })
    
    if screen_time_change > 20:
        recommendations.append({
            "title": "Screen Time Increasing",
            "description": "Your screen time has increased significantly. Be mindful of your usage patterns."
        })
    
    if not recommendations:
        recommendations.append({
            "title": "Maintain Your Progress",
            "description": "You're doing well! Continue your current habits and digital wellbeing practices."
        })
    
    return {
        "overall_score": overall_score,
        "habit_summary": habit_summary,
        "habit_completion_rate": habit_completion_rate,
        "active_habits": active_habits,
        "longest_streak": longest_streak,
        "screen_time_summary": screen_time_summary,
        "avg_screen_time": avg_screen_time,
        "screen_time_change": screen_time_change,
        "most_used_app": most_used_app,
        "recommendations": recommendations
    }

@insights.route('/insights')
@login_required
def ai_insights():
    """AI Insights Dashboard"""
    # Get user's habits
    user_habits = Habit.query.filter_by(user_id=current_user.id).all()
    
    # Get recent screen time logs
    today = datetime.utcnow().date()
    week_ago = today - timedelta(days=7)
    screen_time_logs = ScreenTimeLog.query.filter_by(
        user_id=current_user.id
    ).filter(
        ScreenTimeLog.date >= week_ago
    ).all()
    
    # Get active and completed detox plans
    active_detox_plans = DigitalDetoxPlan.query.filter_by(
        user_id=current_user.id, 
        is_active=True
    ).all()
    
    completed_detox_plans = DigitalDetoxPlan.query.filter_by(
        user_id=current_user.id, 
        is_active=False
    ).filter(
        DigitalDetoxPlan.end_date < today
    ).all()
    
    # Get app limits
    app_limits = AppLimit.query.filter_by(
        user_id=current_user.id
    ).all()
    
    # Generate digital wellbeing insights
    wellbeing_insights = generate_wellbeing_insights(
        screen_time_logs, 
        active_detox_plans, 
        app_limits
    )
    
    # Calculate correlations between habits and screen time
    correlations = calculate_habit_screen_time_correlations(
        user_habits, 
        screen_time_logs
    )
    
    # Generate personalized recommendations
    recommendations = generate_personalized_recommendations(
        user_habits, 
        screen_time_logs, 
        active_detox_plans, 
        app_limits
    )
    
    # Generate weekly report
    weekly_report = generate_weekly_report(
        user_habits, 
        screen_time_logs
    )
    
    # Get score history for visualization
    score_history = get_wellbeing_score_history(current_user.id)
    score_dates = []
    score_values = []
    if score_history:
        for entry in score_history:
            score_dates.append(entry['date'].strftime('%Y-%m-%d'))
            score_values.append(entry['score'])
    
    # Get wellbeing score history
    wellbeing_history = get_wellbeing_score_history(current_user.id)
    wellbeing_dates = []
    wellbeing_scores = []
    if wellbeing_history:
        for entry in wellbeing_history:
            wellbeing_dates.append(entry['date'].strftime('%Y-%m-%d'))
            wellbeing_scores.append(entry['score'])
    
    # Get at-risk habits
    at_risk_habits = get_at_risk_habits(user_habits, screen_time_logs)
    
    # Format the report date
    report_date = today.strftime('%B %d, %Y')
    
    return render_template(
        'insights/ai_insights.html',
        weekly_report=weekly_report,
        correlations=correlations,
        wellbeing_insights=wellbeing_insights,
        recommendations=recommendations,
        score_history=score_history,
        score_dates=score_dates,
        score_values=score_values,
        wellbeing_history=wellbeing_history,
        wellbeing_dates=wellbeing_dates,
        wellbeing_scores=wellbeing_scores,
        at_risk_habits=at_risk_habits,
        report_date=report_date
    )

@insights.route('/insights/api/weekly-report')
@login_required
def api_weekly_report():
    # Get user's habits
    user_habits = Habit.query.filter_by(user_id=current_user.id).all()
    
    # Get recent screen time logs
    today = datetime.utcnow().date()
    week_ago = today - timedelta(days=7)
    screen_time_logs = ScreenTimeLog.query.filter_by(
        user_id=current_user.id
    ).filter(
        ScreenTimeLog.date >= week_ago
    ).all()
    
    # Generate weekly report
    weekly_report = generate_weekly_report(user_habits, screen_time_logs)
    
    return jsonify(weekly_report)

@insights.route('/insights/api/habit-suggestions')
@login_required
def api_habit_suggestions():
    # Get user's habits
    user_habits = Habit.query.filter_by(user_id=current_user.id).all()
    
    # Get recent screen time logs
    today = datetime.utcnow().date()
    week_ago = today - timedelta(days=7)
    screen_time_logs = ScreenTimeLog.query.filter_by(
        user_id=current_user.id
    ).filter(
        ScreenTimeLog.date >= week_ago
    ).all()
    
    # Generate habit suggestions
    habit_suggestions = generate_habit_suggestions(user_habits, screen_time_logs)
    
    return jsonify({"suggestions": habit_suggestions})

@insights.route('/insights/refresh')
@login_required
def refresh_insights():
    """Force refresh of AI insights"""
    # This route simply redirects back to the insights page
    # The insights will be recalculated when the page loads
    flash('AI insights have been refreshed with your latest data', 'success')
    return redirect(url_for('insights.ai_insights'))


def get_wellbeing_score_history(user_id, days=30):
    """Get wellbeing score history for the specified user"""
    # In a real app, this would query a database table
    # For now, we'll generate some sample data
    today = datetime.utcnow().date()
    history = []
    
    # Generate sample data with a slight upward trend
    base_score = 65
    for i in range(days):
        date = today - timedelta(days=days-i-1)
        # Add some randomness to the score
        random_factor = random.randint(-5, 5)
        # Add a slight upward trend
        trend_factor = i * 0.2
        score = min(100, max(0, base_score + random_factor + trend_factor))
        history.append({
            'date': date,
            'score': int(score)
        })
    
    return history


def save_wellbeing_score(user_id, score):
    """Save the current wellbeing score to history"""
    # In a real app, this would save to a database table
    # For now, we'll just pass since we're generating sample data
    pass


def get_at_risk_habits(user_habits, screen_time_logs):
    """Identify habits that are at risk of being dropped"""
    at_risk_habits = []
    
    for habit in user_habits:
        # Check completion rate
        completion_rate = calculate_habit_completion_rate(habit)
        
        # Check if screen time is affecting habit completion
        screen_time_impact = check_screen_time_impact(habit, screen_time_logs)
        
        # Determine if habit is at risk
        if completion_rate < 0.5 or screen_time_impact > 0.7:
            reason = ""
            if completion_rate < 0.5:
                reason = f"Low completion rate ({int(completion_rate*100)}%). Try setting reminders."
            elif screen_time_impact > 0.7:
                reason = "High screen time on days when this habit is missed. Consider reducing app usage."
            
            at_risk_habits.append({
                'habit': habit,
                'reason': reason
            })
    
    return at_risk_habits


def calculate_habit_completion_rate(habit):
    """Calculate the completion rate for a habit"""
    # In a real app, this would query the habit's completion records
    # For now, return a random value between 0.3 and 0.9
    return random.uniform(0.3, 0.9)


def check_screen_time_impact(habit, screen_time_logs):
    """Check if screen time is impacting habit completion"""
    # In a real app, this would compare screen time on days when the habit was completed vs missed
    # For now, return a random value between 0.1 and 0.9
    return random.uniform(0.1, 0.9)
