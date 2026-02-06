from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.models import Habit, HabitLog, ScreenTimeLog, ScreenTime, UserAchievement, Achievement
from datetime import datetime, timedelta
import random

chatbot = Blueprint('chatbot', __name__)

def process_message(message):
    """Process user message and return appropriate response with more intelligence and context"""
    message = message.lower().strip()
    
    # Get user context for more personalized responses
    habits = Habit.query.filter_by(user_id=current_user.id).all()
    habit_names = [habit.name.lower() for habit in habits]
    
    # Check for greetings
    if any(greeting in message for greeting in ["hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening"]):
        current_hour = datetime.now().hour
        greeting = "Good morning" if 5 <= current_hour < 12 else "Good afternoon" if 12 <= current_hour < 18 else "Good evening"
        return f"{greeting}, {current_user.username}! How can I help with your habits today? You can ask about your progress, get suggestions, or request a challenge."
    
    # Check for specific habit questions
    for habit_name in habit_names:
        if habit_name in message:
            habit = next((h for h in habits if h.name.lower() == habit_name), None)
            if habit:
                return get_habit_specific_advice(habit)
    
    # Check for weekly summary request
    if any(phrase in message for phrase in ["how did i do", "this week", "my progress", "summary", "how am i doing"]):
        return get_weekly_summary()
    
    # Check for habit focus question
    if any(phrase in message for phrase in ["what habit", "focus on", "prioritize", "which habit", "what should i focus"]):
        return get_habit_focus()
    
    # Check for challenge request
    if any(phrase in message for phrase in ["challenge", "give me a challenge", "challenge for today", "task"]):
        return get_daily_challenge()
    
    # Check for habit tracking summary
    if any(phrase in message for phrase in ["show my", "last 7 days", "habit tracking", "progress", "how am i doing"]):
        return get_habit_tracking_summary()
    
    # Check for screen time question
    if any(phrase in message for phrase in ["screen time", "digital usage", "app usage", "phone usage", "screen addiction"]):
        return get_screen_time_summary()
    
    # Check for achievement question
    if any(phrase in message for phrase in ["achievement", "badge", "trophy", "earned", "rewards", "points"]):
        return get_achievement_summary()
    
    # Check for habit suggestion
    if any(phrase in message for phrase in ["suggest", "recommend", "new habit", "habit idea", "what should i try"]):
        return get_habit_suggestion()
    
    # Check for motivation request
    if any(phrase in message for phrase in ["motivate", "motivation", "inspire", "feeling lazy", "don't feel like", "procrastinating"]):
        return get_motivation()
    
    # Check for streak questions
    if any(phrase in message for phrase in ["streak", "consecutive", "in a row", "chain"]):
        return get_streak_information()
    
    # Check for help request
    if any(phrase in message for phrase in ["help", "how to use", "what can you do", "capabilities", "features"]):
        return get_help_info()
    
    # Check for thank you messages
    if any(phrase in message for phrase in ["thank", "thanks", "appreciate", "grateful"]):
        return "You're welcome! I'm always here to help you build better habits and improve your digital wellbeing. Is there anything else you'd like to know?"
    
    # Default responses - more personalized
    habits_count = len(habits)
    if habits_count == 0:
        return "I notice you haven't set up any habits yet. Would you like me to suggest some habits to get started with?"
    else:
        # More contextual default responses
        default_responses = [
            f"I'm here to help with your {habits_count} habits and overall wellbeing. You can ask me about your progress, challenges, or suggestions.",
            f"Need help with your habits? Ask me about your weekly summary, achievements, or for a new challenge tailored to your goals.",
            f"I can help you track your habits and screen time. What specific aspect of your wellbeing would you like to focus on today?",
            f"Ask me about your habit progress, screen time, or for a personalized daily challenge based on your current habits."
        ]
        
        return random.choice(default_responses)

def get_weekly_summary():
    """Generate a summary of the user's week"""
    # Get habits and their completion status
    habits = Habit.query.filter_by(user_id=current_user.id).all()
    
    if not habits:
        return "You haven't created any habits yet. Start by adding some habits to track!"
    
    # Get logs from the past week
    today = datetime.utcnow().date()
    week_ago = today - timedelta(days=7)
    logs = HabitLog.query.filter_by(
        user_id=current_user.id
    ).filter(
        HabitLog.date >= week_ago
    ).all()
    
    completed_count = sum(1 for log in logs if log.completed)
    total_count = len(logs)
    
    if total_count == 0:
        return "You haven't logged any habits this week. Start tracking to see your progress!"
    
    completion_rate = (completed_count / total_count) * 100
    
    # Get longest streak
    longest_streak = 0
    streak_habit = None
    for habit in habits:
        streak = habit.current_streak()
        if streak > longest_streak:
            longest_streak = streak
            streak_habit = habit
    
    # Generate response
    if completion_rate >= 80:
        quality = "excellent"
    elif completion_rate >= 60:
        quality = "good"
    elif completion_rate >= 40:
        quality = "fair"
    else:
        quality = "challenging"
    
    response = f"You had a {quality} week! You completed {completed_count} out of {total_count} habit entries ({completion_rate:.0f}%)."
    
    if streak_habit and longest_streak > 0:
        response += f" Your longest streak is {longest_streak} days for '{streak_habit.name}'."
    
    return response

def get_habit_focus():
    """Suggest which habit to focus on"""
    habits = Habit.query.filter_by(user_id=current_user.id).all()
    
    if not habits:
        return "You haven't created any habits yet. Start by adding some habits to track!"
    
    # Find habits with low completion rates
    habit_stats = []
    for habit in habits:
        logs = HabitLog.query.filter_by(habit_id=habit.id).all()
        if logs:
            completion_rate = sum(1 for log in logs if log.completed) / len(logs)
            habit_stats.append((habit, completion_rate))
    
    if not habit_stats:
        return f"I suggest focusing on '{random.choice(habits).name}' today. You haven't logged it yet."
    
    # Sort by completion rate (lowest first)
    habit_stats.sort(key=lambda x: x[1])
    
    # Suggest the habit with lowest completion rate
    habit, rate = habit_stats[0]
    
    return f"I suggest focusing on '{habit.name}' today. Your completion rate is {rate:.0%}, which could use some improvement."

def get_daily_challenge():
    """Generate a random daily challenge"""
    habits = Habit.query.filter_by(user_id=current_user.id).all()
    
    challenges = [
        "Complete all your habits today without delay!",
        "Try to beat your longest streak for any habit!",
        "Add one new habit that will improve your wellbeing.",
        "Reduce your screen time by 30 minutes today.",
        "Complete your habits earlier in the day than usual."
    ]
    
    if habits:
        habit_challenges = [
            f"Focus on '{random.choice(habits).name}' and write detailed notes about it.",
            f"Try to improve your streak for '{random.choice(habits).name}'."
        ]
        challenges.extend(habit_challenges)
    
    return f"Your challenge for today: {random.choice(challenges)}"

def get_habit_tracking_summary():
    """Get a summary of habit tracking for the last 7 days"""
    today = datetime.utcnow().date()
    week_ago = today - timedelta(days=7)
    
    logs = HabitLog.query.filter_by(
        user_id=current_user.id
    ).filter(
        HabitLog.date >= week_ago
    ).all()
    
    if not logs:
        return "You haven't tracked any habits in the last 7 days."
    
    # Group by date
    logs_by_date = {}
    for log in logs:
        date_str = log.date.strftime('%Y-%m-%d')
        if date_str not in logs_by_date:
            logs_by_date[date_str] = []
        logs_by_date[date_str].append(log)
    
    # Generate summary
    summary = f"Here's your habit tracking for the last {len(logs_by_date)} days:\n"
    
    for date_str, day_logs in sorted(logs_by_date.items()):
        completed = sum(1 for log in day_logs if log.completed)
        total = len(day_logs)
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        day_name = date_obj.strftime('%A')
        summary += f"- {day_name}: Completed {completed}/{total} habits\n"
    
    return summary

def get_screen_time_summary():
    """Get a summary of screen time"""
    today = datetime.utcnow().date()
    week_ago = today - timedelta(days=7)
    
    logs = ScreenTimeLog.query.filter_by(
        user_id=current_user.id
    ).filter(
        ScreenTimeLog.date >= week_ago
    ).all()
    
    if not logs:
        return "You haven't uploaded any screen time data recently."
    
    # Calculate total screen time
    total_minutes = sum(log.usage_minutes for log in logs)
    hours = total_minutes // 60
    minutes = total_minutes % 60
    
    # Get top apps
    app_usage = {}
    for log in logs:
        if log.app_name in app_usage:
            app_usage[log.app_name] += log.usage_minutes
        else:
            app_usage[log.app_name] = log.usage_minutes
    
    top_apps = sorted(app_usage.items(), key=lambda x: x[1], reverse=True)[:3]
    
    response = f"In the last week, you spent {hours} hours and {minutes} minutes on your devices."
    
    if top_apps:
        response += " Your top apps were:"
        for app, minutes in top_apps:
            hours = minutes // 60
            mins = minutes % 60
            if hours > 0:
                response += f" {app} ({hours}h {mins}m),"
            else:
                response += f" {app} ({mins}m),"
        response = response[:-1]  # Remove trailing comma
    
    return response

def get_achievement_summary():
    """Get a summary of user achievements"""
    achievements = UserAchievement.query.filter_by(user_id=current_user.id).all()
    
    if not achievements:
        return "You haven't earned any achievements yet. Keep working on your habits to unlock them!"
    
    # Get achievement details
    achievement_details = []
    for user_achievement in achievements:
        achievement = Achievement.query.get(user_achievement.achievement_id)
        if achievement:
            achievement_details.append(achievement)
    
    response = f"You've earned {len(achievement_details)} achievements:"
    
    for achievement in achievement_details:
        response += f" {achievement.name},"
    
    response = response[:-1]  # Remove trailing comma
    
    # Check for available achievements
    available_count = Achievement.query.count() - len(achievement_details)
    if available_count > 0:
        response += f" There are {available_count} more achievements to unlock!"
    
    return response

def get_habit_suggestion():
    """Suggest a new habit based on user profile"""
    # Get existing habits
    existing_habits = Habit.query.filter_by(user_id=current_user.id).all()
    existing_habit_names = [h.name.lower() for h in existing_habits]
    
    # Common habits by category
    health_habits = ["Daily exercise", "Drink 8 glasses of water", "Take vitamins", "Meditate for 10 minutes"]
    productivity_habits = ["Read for 30 minutes", "Learn something new", "Plan your day", "No phone first hour"]
    wellbeing_habits = ["Gratitude journaling", "Call a friend", "Spend time outdoors", "Practice mindfulness"]
    
    # Filter out existing habits
    all_habits = health_habits + productivity_habits + wellbeing_habits
    available_habits = [h for h in all_habits if h.lower() not in existing_habit_names]
    
    if not available_habits:
        return "You're already tracking many great habits! Consider focusing on improving your existing habits."
    
    # Personalize based on user profile if available
    if current_user.hobbies:
        hobby_keywords = {
            "read": ["Read for 30 minutes", "Read before bed"],
            "exercise": ["Daily exercise", "Morning workout", "10,000 steps"],
            "music": ["Practice instrument", "Listen to new music"],
            "art": ["Draw or sketch", "Visit art gallery monthly"],
            "nature": ["Spend time outdoors", "Gardening", "Hiking"]
        }
        
        for keyword, related_habits in hobby_keywords.items():
            if keyword in current_user.hobbies.lower():
                matching_habits = [h for h in related_habits if h.lower() not in existing_habit_names]
                if matching_habits:
                    habit = random.choice(matching_habits)
                    return f"Based on your interests, I suggest adding '{habit}' as a new habit to track."
    
    # Default suggestion
    habit = random.choice(available_habits)
    return f"I suggest adding '{habit}' as a new habit to track."

@chatbot.route('/chatbot')
@login_required
def chatbot_page():
    # Get user's habit statistics for the sidebar
    habits = Habit.query.filter_by(user_id=current_user.id).all()
    active_habits = len(habits)
    
    # Calculate completion rate
    total_logs = 0
    completed_logs = 0
    longest_streak = 0
    
    for habit in habits:
        habit_logs = HabitLog.query.filter_by(habit_id=habit.id).all()
        total_logs += len(habit_logs)
        completed_logs += sum(1 for log in habit_logs if log.completed)
        
        # Update longest streak if this habit has a longer one
        current_streak = habit.current_streak()
        if current_streak > longest_streak:
            longest_streak = current_streak
    
    # Calculate completion rate (avoid division by zero)
    completion_rate = round((completed_logs / total_logs) * 100) if total_logs > 0 else 0
    
    # Create habit stats dictionary
    habit_stats = {
        'active_habits': active_habits,
        'completion_rate': completion_rate,
        'longest_streak': longest_streak
    }
    
    # Get recent habits data (last 5 completed or missed habits)
    recent_habits = []
    habit_logs = HabitLog.query.join(Habit).filter(Habit.user_id == current_user.id)\
                .order_by(HabitLog.date.desc()).limit(5).all()
    
    for log in habit_logs:
        habit = Habit.query.get(log.habit_id)
        recent_habits.append({
            'name': habit.name,
            'completed': log.completed,
            'last_logged': log.date.strftime('%b %d')
        })
    
    # Get screen time data if available
    from datetime import datetime, timedelta
    from app.models import ScreenTime, ScreenTimeLog
    
    # Try to get the latest screen time data
    screen_time_data = ScreenTime.query.filter_by(user_id=current_user.id).order_by(ScreenTime.date.desc()).first()
    
    # If no data exists, try to generate it from logs
    if not screen_time_data:
        # Check if we have any screen time logs
        has_logs = ScreenTimeLog.query.filter_by(user_id=current_user.id).first() is not None
        
        if has_logs:
            # Generate screen time data from logs
            screen_time_data = ScreenTime.generate_from_logs(current_user.id)
    
    if screen_time_data:
        # Use actual data from database
        screen_time = {
            'daily_avg': f"{screen_time_data.daily_average // 60}h {screen_time_data.daily_average % 60}m",
            'most_used_app': screen_time_data.most_used_app,
            'weekly_change_pct': screen_time_data.weekly_change
        }
    else:
        # If no screen time data exists and couldn't be generated, use demo data
        import random
        screen_time = {
            'daily_avg': f"{random.randint(2, 5)}h {random.randint(0, 59)}m",
            'most_used_app': random.choice(['Instagram', 'YouTube', 'Twitter', 'TikTok', 'Productivity App']),
            'weekly_change_pct': random.randint(-20, 20)
        }
    
    return render_template('chatbot/chat.html', title='Digital Twin: Your AI Twin Everywhere', 
                           habit_stats=habit_stats, 
                           recent_habits=recent_habits,
                           screen_time=screen_time)

def get_habit_specific_advice(habit):
    """Generate specific advice for a given habit"""
    # Get habit logs for the past 30 days
    thirty_days_ago = datetime.now().date() - timedelta(days=30)
    habit_logs = HabitLog.query.filter_by(habit_id=habit.id).filter(HabitLog.date >= thirty_days_ago).all()
    
    # Calculate completion rate
    total_logs = len(habit_logs)
    completed_logs = sum(1 for log in habit_logs if log.completed)
    completion_rate = round((completed_logs / total_logs) * 100) if total_logs > 0 else 0
    
    # Get current streak
    current_streak = habit.current_streak()
    
    # Generate advice based on completion rate
    if completion_rate >= 80:
        advice = f"You're doing great with your '{habit.name}' habit! You've completed it {completion_rate}% of the time in the last 30 days."
        if current_streak > 7:
            advice += f" Your current streak is {current_streak} days - that's impressive! Keep it up!"
        else:
            advice += f" Your current streak is {current_streak} days. Try to build on this consistency."
    elif completion_rate >= 50:
        advice = f"You're making good progress with your '{habit.name}' habit with a {completion_rate}% completion rate in the last 30 days."
        if current_streak > 3:
            advice += f" Your current streak is {current_streak} days - you're building momentum!"
        else:
            advice += f" Your current streak is {current_streak} days. Focus on consistency to build a longer streak."
    else:
        advice = f"It looks like you're having some challenges with your '{habit.name}' habit. Your completion rate is {completion_rate}% in the last 30 days."
        if current_streak > 0:
            advice += f" Your current streak is {current_streak} days - that's a good start! Try to maintain this momentum."
        else:
            advice += " You don't have an active streak right now. Let's focus on getting started again - even small steps count!"
    
    # Add a tip based on habit type
    if "exercise" in habit.name.lower() or "workout" in habit.name.lower() or "run" in habit.name.lower():
        advice += "\n\nTip: Try scheduling your exercise at the same time each day to build a stronger routine."
    elif "read" in habit.name.lower() or "book" in habit.name.lower():
        advice += "\n\nTip: Even just 10 minutes of reading before bed can help you maintain this habit consistently."
    elif "meditate" in habit.name.lower() or "mindfulness" in habit.name.lower():
        advice += "\n\nTip: Start with just 5 minutes of meditation if you're finding it challenging to maintain consistency."
    elif "water" in habit.name.lower() or "hydrate" in habit.name.lower():
        advice += "\n\nTip: Try keeping a water bottle visible on your desk as a reminder to stay hydrated throughout the day."
    else:
        advice += "\n\nTip: Try linking this habit to an existing daily routine to make it easier to remember and complete."
    
    return advice

def get_motivation():
    """Provide motivational messages based on user's habit data"""
    # Get user habits and their completion status
    habits = Habit.query.filter_by(user_id=current_user.id).all()
    
    if not habits:
        return "The journey of a thousand miles begins with a single step. Start by creating your first habit today!"
    
    # Check if user has any active streaks
    has_streaks = False
    longest_streak = 0
    streak_habit = None
    
    for habit in habits:
        current = habit.current_streak()
        if current > 0:
            has_streaks = True
        if current > longest_streak:
            longest_streak = current
            streak_habit = habit
    
    # Motivational messages based on user's situation
    if has_streaks and longest_streak > 7:
        return f"You're on fire with your '{streak_habit.name}' habit! A {longest_streak}-day streak is impressive. Remember, consistency is the key to lasting change. Keep up the great work!"
    
    elif has_streaks:
        return f"You're building momentum with your habits! Your current streak for '{streak_habit.name}' is {longest_streak} days. Each day you complete your habits is a victory - celebrate these small wins!"
    
    else:
        # Get most recently completed habit
        recent_logs = HabitLog.query.join(Habit).filter(Habit.user_id == current_user.id, HabitLog.completed == True).order_by(HabitLog.date.desc()).first()
        
        if recent_logs:
            habit = Habit.query.get(recent_logs.habit_id)
            days_ago = (datetime.now().date() - recent_logs.date).days
            
            if days_ago == 0:
                return f"Great job completing '{habit.name}' today! Remember, progress isn't always linear. Focus on consistency rather than perfection."
            elif days_ago < 3:
                return f"You completed '{habit.name}' just {days_ago} days ago. Don't break the chain! Every time you complete a habit, you're rewiring your brain for success."
            else:
                return f"It's been {days_ago} days since you completed '{habit.name}'. That's okay! Today is a new opportunity to get back on track. What small step can you take right now?"
        
        else:
            return "Every habit journey has ups and downs. The most important thing is to keep showing up. Start small, be consistent, and trust the process. You've got this!"

def get_streak_information():
    """Provide information about the user's habit streaks"""
    habits = Habit.query.filter_by(user_id=current_user.id).all()
    
    if not habits:
        return "You don't have any habits set up yet. Would you like me to suggest some habits to get started with?"
    
    # Get streak information for each habit
    streak_info = []
    for habit in habits:
        current_streak = habit.current_streak()
        streak_info.append((habit.name, current_streak))
    
    # Sort by streak length (descending)
    streak_info.sort(key=lambda x: x[1], reverse=True)
    
    # Generate response
    response = "Here's your current streak information:\n\n"
    
    for habit_name, streak in streak_info:
        if streak == 0:
            response += f"• {habit_name}: No active streak\n"
        elif streak == 1:
            response += f"• {habit_name}: 1 day\n"
        else:
            response += f"• {habit_name}: {streak} days\n"
    
    # Add a tip about streaks
    response += "\nRemember, the power of streaks comes from consistency. Even a 2-day streak is worth celebrating! Focus on not breaking the chain."
    
    return response

def get_help_info():
    """Provide information about what the Digital Twin can do"""
    return """I'm your Digital Twin, your AI twin that's with you everywhere. I'm here to help you build better habits and improve your digital wellbeing. Here's what I can do for you:  

• **Progress Tracking**: Ask me about your weekly summary or habit progress
• **Habit Advice**: Get personalized advice for specific habits
• **Challenges**: Request daily challenges to boost your motivation
• **Screen Time**: Learn about your digital usage patterns
• **Achievements**: Check your badges and trophies
• **Suggestions**: Get recommendations for new habits to try
• **Motivation**: Ask for motivational support when you need it
• **Streak Information**: Track your consistency with habits

Just ask me questions in natural language, and I'll be with you everywhere on your journey to better habits!"""

@chatbot.route('/chatbot/message', methods=['POST'])
@login_required
def message():
    data = request.json
    user_message = data.get('message', '')
    
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400
    
    response = process_message(user_message)
    
    return jsonify({
        'response': response
    })
