from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from app import db
from app.models import User, Habit, HabitLog, Achievement, UserAchievement, DigitalTwin
from datetime import datetime, timedelta

gamification = Blueprint('gamification', __name__)

def check_achievements():
    """Check if user has earned any new achievements"""
    # Get all available achievements
    achievements = Achievement.query.all()
    
    # Get user's current achievements
    user_achievements = UserAchievement.query.filter_by(user_id=current_user.id).all()
    earned_achievement_ids = [ua.achievement_id for ua in user_achievements]
    
    newly_earned = []
    
    for achievement in achievements:
        # Skip if already earned
        if achievement.id in earned_achievement_ids:
            continue
        
        # Check criteria
        criteria_parts = achievement.criteria.split(':')
        criteria_type = criteria_parts[0]
        criteria_value = int(criteria_parts[1]) if len(criteria_parts) > 1 else 0
        
        # Get user data for checks
        habits = Habit.query.filter_by(user_id=current_user.id).all()
        habit_count = len(habits)
        logs = HabitLog.query.filter_by(user_id=current_user.id).all()
        
        # Achievement earned flag
        achievement_earned = False
        
        if criteria_type == 'streak':
            # Check if any habit has the required streak
            for habit in habits:
                if habit.current_streak() >= criteria_value:
                    achievement_earned = True
                    break
        
        elif criteria_type == 'habits':
            # Check if user has created enough habits
            if habit_count >= criteria_value:
                achievement_earned = True
        
        elif criteria_type == 'completion':
            # Check overall habit completion rate
            if logs:
                completion_rate = sum(1 for log in logs if log.completed) / len(logs) * 100
                if completion_rate >= criteria_value:
                    achievement_earned = True
        
        elif criteria_type == 'consistency':
            # Check if user has logged habits for consecutive days
            if logs:
                # Get unique dates from logs
                log_dates = sorted(set(log.date for log in logs))
                if log_dates:
                    # Check for consecutive days
                    consecutive_days = 1
                    max_consecutive = 1
                    for i in range(1, len(log_dates)):
                        if (log_dates[i] - log_dates[i-1]).days == 1:
                            consecutive_days += 1
                            max_consecutive = max(max_consecutive, consecutive_days)
                        else:
                            consecutive_days = 1
                    
                    if max_consecutive >= criteria_value:
                        achievement_earned = True
        
        elif criteria_type == 'detox':
            # Check if user has completed digital detox plans
            from app.models import DigitalDetoxPlan
            completed_detox = DigitalDetoxPlan.query.filter_by(
                user_id=current_user.id, 
                is_active=False
            ).count()
            
            if completed_detox >= criteria_value:
                achievement_earned = True
        
        elif criteria_type == 'screentime':
            # Check if user has reduced screen time below threshold
            from app.models import ScreenTimeLog
            from datetime import datetime, timedelta
            
            # Get recent screen time logs (last 7 days)
            today = datetime.utcnow().date()
            week_ago = today - timedelta(days=7)
            
            recent_logs = ScreenTimeLog.query.filter_by(user_id=current_user.id).\
                filter(ScreenTimeLog.date >= week_ago).all()
            
            if recent_logs:
                # Calculate average daily screen time
                daily_screen_time = {}
                for log in recent_logs:
                    date_str = log.date.strftime('%Y-%m-%d')
                    if date_str in daily_screen_time:
                        daily_screen_time[date_str] += log.usage_minutes
                    else:
                        daily_screen_time[date_str] = log.usage_minutes
                
                avg_screen_time = sum(daily_screen_time.values()) / len(daily_screen_time)
                
                # Check if average is below threshold (criteria_value is in minutes)
                if avg_screen_time <= criteria_value:
                    achievement_earned = True
        
        elif criteria_type == 'perfect_week':
            # Check if user has completed all habits for a full week
            from datetime import datetime, timedelta
            
            # Get logs from the last 7 days
            today = datetime.utcnow().date()
            week_ago = today - timedelta(days=7)
            
            recent_logs = HabitLog.query.filter_by(user_id=current_user.id).\
                filter(HabitLog.date >= week_ago).all()
            
            if recent_logs and habits:
                # Group logs by date
                logs_by_date = {}
                for log in recent_logs:
                    date_str = log.date.strftime('%Y-%m-%d')
                    if date_str not in logs_by_date:
                        logs_by_date[date_str] = []
                    logs_by_date[date_str].append(log)
                
                # Check if there are 7 days with all habits completed
                perfect_days = 0
                for date, date_logs in logs_by_date.items():
                    if len(date_logs) == habit_count and all(log.completed for log in date_logs):
                        perfect_days += 1
                
                if perfect_days >= criteria_value:  # criteria_value is number of perfect days needed
                    achievement_earned = True
        
        # Award achievement if earned
        if achievement_earned:
            user_achievement = UserAchievement(
                user_id=current_user.id,
                achievement_id=achievement.id
            )
            db.session.add(user_achievement)
            newly_earned.append(achievement)
    
    if newly_earned:
        db.session.commit()
        return newly_earned
    
    return []

@gamification.route('/achievements')
@login_required
def achievements():
    # Check for new achievements
    new_achievements = check_achievements()
    
    # Flash messages for new achievements
    for achievement in new_achievements:
        flash(f'Congratulations! You earned the "{achievement.name}" achievement!', 'success')
    
    # Get all achievements
    all_achievements = Achievement.query.all()
    
    # Get user's earned achievements
    user_achievements = UserAchievement.query.filter_by(user_id=current_user.id).all()
    earned_achievement_ids = [ua.achievement_id for ua in user_achievements]
    
    # Get locked achievements with progress information
    locked_achievements = []
    for achievement in all_achievements:
        if achievement.id not in earned_achievement_ids:
            achievement_info = {
                'id': achievement.id,
                'name': achievement.name,
                'description': achievement.description,
                'icon': achievement.icon,
                'criteria': achievement.criteria,
                'requirement_text': get_achievement_requirement_text(achievement),
                'progress': calculate_achievement_progress(achievement)
            }
            locked_achievements.append(achievement_info)
    
    # Calculate achievement stats
    achievement_percentage = 0
    if all_achievements:
        achievement_percentage = int((len(user_achievements) / len(all_achievements)) * 100)
    
    # Get habit stats
    habits = Habit.query.filter_by(user_id=current_user.id).all()
    habit_logs = HabitLog.query.filter_by(user_id=current_user.id).all()
    habits_completed = sum(1 for log in habit_logs if log.completed)
    
    # Calculate longest streak
    longest_streak = 0
    for habit in habits:
        streak = habit.current_streak()
        if streak > longest_streak:
            longest_streak = streak
            
    # Calculate completion rate
    total_logs = len(habit_logs)
    completion_rate = int((habits_completed / total_logs) * 100) if total_logs > 0 else 0
    
    # Get active habits count (habits with logs in the past 7 days)
    from datetime import datetime, timedelta
    one_week_ago = datetime.utcnow().date() - timedelta(days=7)
    
    # A habit is considered active if it has at least one log in the past week
    active_habits_count = 0
    for habit in habits:
        recent_logs = HabitLog.query.filter(
            HabitLog.habit_id == habit.id,
            HabitLog.date >= one_week_ago
        ).first()
        if recent_logs:
            active_habits_count += 1
    
    # Get screen time data
    from app.models import ScreenTime
    screen_time = ScreenTime.query.filter_by(user_id=current_user.id).order_by(ScreenTime.date.desc()).first()
    
    # Default screen time values
    daily_screen_time = 0
    weekly_change = 0
    most_used_app = 'None'
    
    if screen_time:
        daily_screen_time = screen_time.daily_average
        weekly_change = screen_time.weekly_change
        most_used_app = screen_time.most_used_app
    
    # Get leaderboard data for sidebar
    # First get all users and their achievement counts
    all_users = User.query.all()
    leaderboard_data = []
    
    for user in all_users:
        achievement_count = UserAchievement.query.filter_by(user_id=user.id).count()
        leaderboard_data.append({
            'username': user.username,
            'profile_pic': user.profile_pic if hasattr(user, 'profile_pic') and user.profile_pic else 'default.jpg',
            'achievements_count': achievement_count
        })
    
    # Add sample users if there are fewer than 5 real users
    if len(leaderboard_data) < 5:
        sample_users = [
            {
                'username': 'HealthyHabit123',
                'profile_pic': 'default.jpg',
                'achievements_count': 8
            },
            {
                'username': 'WellnessWarrior',
                'profile_pic': 'default.jpg',
                'achievements_count': 6
            },
            {
                'username': 'DigitalDetoxer',
                'profile_pic': 'default.jpg',
                'achievements_count': 5
            },
            {
                'username': 'MindfulMaster',
                'profile_pic': 'default.jpg',
                'achievements_count': 4
            },
            {
                'username': 'BalanceSeeker',
                'profile_pic': 'default.jpg',
                'achievements_count': 3
            }
        ]
        
        # Only add enough sample users to reach 5 total
        needed_samples = 5 - len(leaderboard_data)
        leaderboard_data.extend(sample_users[:needed_samples])
    
    # Sort by achievements count
    leaderboard_data.sort(key=lambda x: x['achievements_count'], reverse=True)
    
    # Get top 5 for sidebar
    sidebar_leaderboard = leaderboard_data[:5]
    
    return render_template(
        'gamification/achievements.html',
        title='Achievements',
        user_achievements=user_achievements,
        locked_achievements=locked_achievements,
        achievement_percentage=achievement_percentage,
        habits_completed=habits_completed,
        longest_streak=longest_streak,
        completion_rate=completion_rate,
        active_habits=active_habits_count,
        daily_screen_time=daily_screen_time,
        weekly_change=weekly_change,
        most_used_app=most_used_app,
        sidebar_leaderboard=sidebar_leaderboard,
        current_user=current_user
    )

def get_achievement_requirement_text(achievement):
    """Generate human-readable requirement text for an achievement"""
    criteria_parts = achievement.criteria.split(':')
    criteria_type = criteria_parts[0]
    criteria_value = int(criteria_parts[1]) if len(criteria_parts) > 1 else 0
    
    if criteria_type == 'streak':
        return f"Maintain a streak of {criteria_value} days for any habit"
    elif criteria_type == 'habits':
        return f"Create {criteria_value} habits"
    elif criteria_type == 'completion':
        return f"Achieve a {criteria_value}% completion rate across all habits"
    elif criteria_type == 'consistency':
        return f"Log habits for {criteria_value} consecutive days"
    elif criteria_type == 'detox':
        return f"Complete {criteria_value} digital detox plans"
    elif criteria_type == 'screentime':
        hours = criteria_value // 60
        minutes = criteria_value % 60
        time_str = f"{hours} hours" if hours > 0 else ""
        if minutes > 0:
            time_str += f" {minutes} minutes" if time_str else f"{minutes} minutes"
        return f"Maintain average daily screen time below {time_str}"
    elif criteria_type == 'perfect_week':
        return f"Complete all habits for {criteria_value} days in a week"
    else:
        return "Keep going to unlock this achievement"

def calculate_achievement_progress(achievement):
    """Calculate user's progress towards an achievement (0-100%)"""
    criteria_parts = achievement.criteria.split(':')
    criteria_type = criteria_parts[0]
    criteria_value = int(criteria_parts[1]) if len(criteria_parts) > 1 else 0
    
    # Default progress
    progress = 0
    
    if criteria_type == 'streak':
        # Find max streak across all habits
        habits = Habit.query.filter_by(user_id=current_user.id).all()
        max_streak = max([habit.current_streak() for habit in habits]) if habits else 0
        progress = min(100, int((max_streak / max(1, criteria_value)) * 100))
    
    elif criteria_type == 'habits':
        # Count habits
        habit_count = Habit.query.filter_by(user_id=current_user.id).count()
        progress = min(100, int((habit_count / max(1, criteria_value)) * 100))
    
    elif criteria_type == 'completion':
        # Calculate completion rate
        logs = HabitLog.query.filter_by(user_id=current_user.id).all()
        if logs:
            completion_rate = sum(1 for log in logs if log.completed) / len(logs) * 100
            progress = min(100, int((completion_rate / max(1, criteria_value)) * 100))
    
    elif criteria_type == 'consistency':
        # Calculate max consecutive days
        logs = HabitLog.query.filter_by(user_id=current_user.id).all()
        if logs:
            log_dates = sorted(set(log.date for log in logs))
            if log_dates:
                consecutive_days = 1
                max_consecutive = 1
                for i in range(1, len(log_dates)):
                    if (log_dates[i] - log_dates[i-1]).days == 1:
                        consecutive_days += 1
                        max_consecutive = max(max_consecutive, consecutive_days)
                    else:
                        consecutive_days = 1
                progress = min(100, int((max_consecutive / max(1, criteria_value)) * 100))
    
    elif criteria_type == 'detox':
        # Count completed detox plans
        from app.models import DigitalDetoxPlan
        completed_detox = DigitalDetoxPlan.query.filter_by(
            user_id=current_user.id, 
            is_active=False
        ).count()
        progress = min(100, int((completed_detox / max(1, criteria_value)) * 100))
    
    elif criteria_type == 'screentime':
        # Calculate average screen time
        from app.models import ScreenTimeLog
        from datetime import datetime, timedelta
        
        today = datetime.utcnow().date()
        week_ago = today - timedelta(days=7)
        
        recent_logs = ScreenTimeLog.query.filter_by(user_id=current_user.id).\
            filter(ScreenTimeLog.date >= week_ago).all()
        
        if recent_logs:
            daily_screen_time = {}
            for log in recent_logs:
                date_str = log.date.strftime('%Y-%m-%d')
                if date_str in daily_screen_time:
                    daily_screen_time[date_str] += log.usage_minutes
                else:
                    daily_screen_time[date_str] = log.usage_minutes
            
            avg_screen_time = sum(daily_screen_time.values()) / len(daily_screen_time)
            
            # For screen time, lower is better, so invert the progress calculation
            if avg_screen_time <= criteria_value:
                progress = 100
            else:
                # Allow for some flexibility - if they're within 50% over the target, show partial progress
                max_allowed = criteria_value * 1.5
                if avg_screen_time <= max_allowed:
                    progress = int(((max_allowed - avg_screen_time) / (max_allowed - criteria_value)) * 100)
    
    elif criteria_type == 'perfect_week':
        # Count perfect days in the last week
        from datetime import datetime, timedelta
        
        today = datetime.utcnow().date()
        week_ago = today - timedelta(days=7)
        
        habits = Habit.query.filter_by(user_id=current_user.id).all()
        habit_count = len(habits)
        recent_logs = HabitLog.query.filter_by(user_id=current_user.id).\
            filter(HabitLog.date >= week_ago).all()
        
        if recent_logs and habits:
            logs_by_date = {}
            for log in recent_logs:
                date_str = log.date.strftime('%Y-%m-%d')
                if date_str not in logs_by_date:
                    logs_by_date[date_str] = []
                logs_by_date[date_str].append(log)
            
            perfect_days = 0
            for date, date_logs in logs_by_date.items():
                if len(date_logs) == habit_count and all(log.completed for log in date_logs):
                    perfect_days += 1
            
            progress = min(100, int((perfect_days / max(1, criteria_value)) * 100))
    
    return progress

@gamification.route('/leaderboard')
@login_required
def leaderboard():
    # Get all users
    real_users = User.query.all()
    
    # Calculate stats for each real user
    user_stats = []
    for user in real_users:
        # Get habits completed
        completed_habits = HabitLog.query.filter_by(user_id=user.id, completed=True).count()
        
        # Get longest streak
        longest_streak = 0
        habits = Habit.query.filter_by(user_id=user.id).all()
        for habit in habits:
            streak = habit.current_streak()
            if streak > longest_streak:
                longest_streak = streak
        
        # Get achievement count
        achievement_count = UserAchievement.query.filter_by(user_id=user.id).count()
        
        user_stats.append({
            'username': user.username,
            'profile_pic': user.profile_pic if hasattr(user, 'profile_pic') and user.profile_pic else 'default.jpg',
            'completed_habits': completed_habits,
            'longest_streak': longest_streak,
            'achievements_count': achievement_count
        })
    
    # Add sample users if there are fewer than 10 real users
    if len(user_stats) < 10:
        sample_users = [
            {
                'username': 'HealthyHabit123',
                'profile_pic': 'default.jpg',
                'completed_habits': 87,
                'longest_streak': 21,
                'achievements_count': 8
            },
            {
                'username': 'WellnessWarrior',
                'profile_pic': 'default.jpg',
                'completed_habits': 65,
                'longest_streak': 14,
                'achievements_count': 6
            },
            {
                'username': 'DigitalDetoxer',
                'profile_pic': 'default.jpg',
                'completed_habits': 52,
                'longest_streak': 12,
                'achievements_count': 5
            },
            {
                'username': 'MindfulMaster',
                'profile_pic': 'default.jpg',
                'completed_habits': 43,
                'longest_streak': 9,
                'achievements_count': 4
            },
            {
                'username': 'BalanceSeeker',
                'profile_pic': 'default.jpg',
                'completed_habits': 38,
                'longest_streak': 7,
                'achievements_count': 3
            },
            {
                'username': 'TechTimeManager',
                'profile_pic': 'default.jpg',
                'completed_habits': 31,
                'longest_streak': 6,
                'achievements_count': 3
            },
            {
                'username': 'FocusedFriend',
                'profile_pic': 'default.jpg',
                'completed_habits': 25,
                'longest_streak': 5,
                'achievements_count': 2
            },
            {
                'username': 'ScreenTimeSlayer',
                'profile_pic': 'default.jpg',
                'completed_habits': 19,
                'longest_streak': 4,
                'achievements_count': 2
            },
            {
                'username': 'HabitHero',
                'profile_pic': 'default.jpg',
                'completed_habits': 15,
                'longest_streak': 3,
                'achievements_count': 1
            }
        ]
        
        # Only add enough sample users to reach 10 total
        needed_samples = 10 - len(user_stats)
        user_stats.extend(sample_users[:needed_samples])
    
    # Sort by achievements count (primary) and completed habits (secondary)
    user_stats.sort(key=lambda x: (x['achievements_count'], x['completed_habits']), reverse=True)
    
    # Get top 10 for leaderboard
    leaderboard_users = user_stats[:10]
    
    # Also pass a shorter list for the sidebar widget
    sidebar_leaderboard = user_stats[:5]
    
    return render_template(
        'gamification/leaderboard.html',
        title='Leaderboard',
        leaderboard=leaderboard_users,
        sidebar_leaderboard=sidebar_leaderboard,
        current_user=current_user
    )

@gamification.route('/challenge/<int:challenge_id>')
@login_required
def challenge_details(challenge_id):
    """Display details for a specific challenge"""
    # In a real app, you would fetch challenge details from the database
    # For now, we'll use hardcoded sample challenges
    challenges = {
        1: {
            'id': 1,
            'name': '7-Day Digital Detox',
            'description': 'Complete a full week of digital detox plans',
            'long_description': 'Reduce your screen time and focus on real-world activities. Track your digital habits daily and maintain a healthy balance between online and offline activities.',
            'end_date': datetime.now() + timedelta(days=5),
            'progress': 2,
            'total': 7,
            'reward_points': 500,
            'reward_badge': 'Digital Wellness Badge',
            'color': 'indigo',
            'tips': [
                'Set specific screen-free hours each day',
                'Use app blockers during focus time',
                'Replace phone time with reading or outdoor activities',
                'Turn off notifications for non-essential apps'
            ]
        },
        2: {
            'id': 2,
            'name': 'Morning Routine Master',
            'description': 'Complete your morning habits before 9 AM for 14 days',
            'long_description': 'Establish a consistent morning routine to start your day with purpose and energy. Complete all your morning habits before 9 AM to build discipline and productivity.',
            'end_date': datetime.now() + timedelta(days=10),
            'progress': 5,
            'total': 14,
            'reward_points': 750,
            'reward_badge': 'Early Bird Badge',
            'color': 'amber',
            'tips': [
                'Prepare for your morning the night before',
                'Wake up at the same time every day',
                'Drink water first thing in the morning',
                'Avoid checking your phone for the first 30 minutes'
            ]
        },
        3: {
            'id': 3,
            'name': 'Weekend Warrior',
            'description': 'Complete all habits on both Saturday and Sunday for 3 weekends',
            'long_description': 'Don\'t let weekends derail your progress. Maintain your habit consistency through the weekend to build true lifestyle changes that last.',
            'end_date': datetime.now() + timedelta(days=3),
            'progress': 2,
            'total': 3,
            'reward_points': 600,
            'reward_badge': 'Weekend Warrior Badge',
            'color': 'green',
            'tips': [
                'Plan your weekend schedule in advance',
                'Set specific times for habits rather than leaving them open-ended',
                'Find an accountability partner for weekend check-ins',
                'Create a visual reminder of your weekend goals'
            ]
        }
    }
    
    challenge = challenges.get(challenge_id)
    if not challenge:
        flash('Challenge not found', 'error')
        return redirect(url_for('gamification.achievements'))
    
    return render_template(
        'gamification/challenge_details.html',
        title=f'Challenge: {challenge["name"]}',
        challenge=challenge
    )

@gamification.route('/challenge/<int:challenge_id>/update', methods=['POST'])
@login_required
def update_challenge_progress(challenge_id):
    """Update progress for a specific challenge"""
    # In a real app, you would update the database with the new progress
    # For now, we'll just redirect back to the challenge details page with a flash message
    
    # Get the progress value from the form
    progress = request.form.get('progress', type=int)
    notes = request.form.get('notes', '')
    
    # Validate the progress value
    if progress is None:
        flash('Invalid progress value', 'error')
        return redirect(url_for('gamification.challenge_details', challenge_id=challenge_id))
    
    # In a real app, you would update the database here
    # For now, just show a success message
    flash(f'Progress updated to {progress}! Your notes have been saved.', 'success')
    
    # Redirect back to the challenge details page
    return redirect(url_for('gamification.challenge_details', challenge_id=challenge_id))

@gamification.route('/challenges')
@login_required
def browse_challenges():
    """Browse all available challenges"""
    # In a real app, you would fetch all challenges from the database
    # For now, we'll use hardcoded sample challenges plus additional ones
    challenges = [
        {
            'id': 1,
            'name': '7-Day Digital Detox',
            'description': 'Complete a full week of digital detox plans',
            'end_date': datetime.now() + timedelta(days=5),
            'progress': 2,
            'total': 7,
            'reward_points': 500,
            'reward_badge': 'Digital Wellness Badge',
            'color': 'indigo'
        },
        {
            'id': 2,
            'name': 'Morning Routine Master',
            'description': 'Complete your morning habits before 9 AM for 14 days',
            'end_date': datetime.now() + timedelta(days=10),
            'progress': 5,
            'total': 14,
            'reward_points': 750,
            'reward_badge': 'Early Bird Badge',
            'color': 'amber'
        },
        {
            'id': 3,
            'name': 'Weekend Warrior',
            'description': 'Complete all habits on both Saturday and Sunday for 3 weekends',
            'end_date': datetime.now() + timedelta(days=3),
            'progress': 2,
            'total': 3,
            'reward_points': 600,
            'reward_badge': 'Weekend Warrior Badge',
            'color': 'green'
        },
        {
            'id': 4,
            'name': 'Mindfulness Marathon',
            'description': 'Complete 21 consecutive days of meditation practice',
            'end_date': datetime.now() + timedelta(days=18),
            'progress': 3,
            'total': 21,
            'reward_points': 800,
            'reward_badge': 'Zen Master Badge',
            'color': 'blue'
        },
        {
            'id': 5,
            'name': 'Hydration Hero',
            'description': 'Track your water intake for 30 days straight',
            'end_date': datetime.now() + timedelta(days=25),
            'progress': 5,
            'total': 30,
            'reward_points': 650,
            'reward_badge': 'Hydration Hero Badge',
            'color': 'cyan'
        },
        {
            'id': 6,
            'name': 'Sleep Cycle Reset',
            'description': 'Go to bed before 11 PM for 14 consecutive nights',
            'end_date': datetime.now() + timedelta(days=12),
            'progress': 2,
            'total': 14,
            'reward_points': 700,
            'reward_badge': 'Sleep Champion Badge',
            'color': 'purple'
        }
    ]
    
    return render_template(
        'gamification/browse_challenges.html',
        title='Browse Challenges',
        challenges=challenges
    )

@gamification.route('/digital-twin')
@login_required
def digital_twin():
    # Get user's habits and their digital twins
    habits = Habit.query.filter_by(user_id=current_user.id).all()
    
    habit_comparisons = []
    for habit in habits:
        # Get user's stats
        user_streak = habit.current_streak()
        user_completion = habit.completion_rate()
        
        # Get digital twin's stats
        twin = DigitalTwin.query.filter_by(habit_id=habit.id, user_id=current_user.id).first()
        
        if twin:
            twin_streak = twin.streak
            twin_completion = twin.completion_rate * 100
            
            # Determine who's winning
            streak_winner = "user" if user_streak > twin_streak else "twin" if twin_streak > user_streak else "tie"
            completion_winner = "user" if user_completion > twin_completion else "twin" if twin_completion > user_completion else "tie"
            
            habit_comparisons.append({
                'habit': habit,
                'user_streak': user_streak,
                'twin_streak': twin_streak,
                'user_completion': user_completion,
                'twin_completion': twin_completion,
                'streak_winner': streak_winner,
                'completion_winner': completion_winner
            })
    
    # Generate a challenge
    challenges = [
        f"Beat your twin's streak for {habits[0].name if habits else 'your habit'}",
        "Complete all your habits for 3 days straight",
        "Improve your completion rate by 10%",
        "Add a new habit and maintain it for a week"
    ]
    
    challenge = challenges[0] if habits else challenges[3]
    
    return render_template(
        'gamification/digital_twin.html',
        title='Digital Twin',
        habit_comparisons=habit_comparisons,
        challenge=challenge
    )
