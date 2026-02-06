from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    full_name = db.Column(db.String(100))
    age = db.Column(db.Integer)
    hobbies = db.Column(db.Text)
    bio = db.Column(db.Text)
    profile_pic = db.Column(db.String(100), default='default.jpg')
    join_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    habits = db.relationship('Habit', backref='user', lazy=True)
    habit_logs = db.relationship('HabitLog', backref='user', lazy=True)
    screen_time_logs = db.relationship('ScreenTimeLog', backref='user', lazy=True)
    achievements = db.relationship('UserAchievement', backref='user', lazy=True)
    app_limits = db.relationship('AppLimit', backref='user', lazy=True)
    detox_plans = db.relationship('DigitalDetoxPlan', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Habit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    frequency = db.Column(db.String(20), nullable=False)  # daily, weekly
    goal = db.Column(db.Integer)  # target number of completions
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    logs = db.relationship('HabitLog', backref='habit', lazy=True)
    
    def current_streak(self):
        # Calculate current streak
        logs = HabitLog.query.filter_by(habit_id=self.id, completed=True).order_by(HabitLog.date.desc()).all()
        if not logs:
            return 0
            
        streak = 1
        for i in range(len(logs) - 1):
            if (logs[i].date - logs[i+1].date).days == 1:
                streak += 1
            else:
                break
        return streak
    
    def completion_rate(self):
        total_logs = HabitLog.query.filter_by(habit_id=self.id).count()
        if total_logs == 0:
            return 0
        completed_logs = HabitLog.query.filter_by(habit_id=self.id, completed=True).count()
        return (completed_logs / total_logs) * 100
    
    def __repr__(self):
        return f'<Habit {self.name}>'

class HabitLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    completed = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)
    habit_id = db.Column(db.Integer, db.ForeignKey('habit.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def __repr__(self):
        return f'<HabitLog {self.habit_id} on {self.date}>'

class ScreenTimeLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    app_name = db.Column(db.String(100), nullable=False)
    usage_minutes = db.Column(db.Integer, nullable=False)
    upload_file = db.Column(db.String(100))  # Reference to the uploaded file
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def __repr__(self):
        return f'<ScreenTimeLog {self.app_name} - {self.usage_minutes} mins>'


class ScreenTime(db.Model):
    """Aggregated screen time data for a user"""
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    daily_average = db.Column(db.Integer, nullable=False)  # In minutes
    most_used_app = db.Column(db.String(100), nullable=False)
    weekly_change = db.Column(db.Integer, nullable=False)  # Percentage change
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def __repr__(self):
        return f'<ScreenTime {self.date} - {self.daily_average} mins>'
    
    @classmethod
    def generate_from_logs(cls, user_id):
        """Generate aggregated screen time data from logs"""
        from datetime import datetime, timedelta
        import sqlalchemy as sa
        
        # Get today's date and 7 days ago
        today = datetime.utcnow().date()
        week_ago = today - timedelta(days=7)
        two_weeks_ago = today - timedelta(days=14)
        
        # Get logs from the past week
        current_week_logs = ScreenTimeLog.query.filter(
            ScreenTimeLog.user_id == user_id,
            ScreenTimeLog.date >= week_ago,
            ScreenTimeLog.date <= today
        ).all()
        
        # Get logs from the previous week for comparison
        previous_week_logs = ScreenTimeLog.query.filter(
            ScreenTimeLog.user_id == user_id,
            ScreenTimeLog.date >= two_weeks_ago,
            ScreenTimeLog.date < week_ago
        ).all()
        
        # If no logs, return None
        if not current_week_logs:
            return None
        
        # Calculate daily average
        total_minutes = sum(log.usage_minutes for log in current_week_logs)
        # Get unique dates to know how many days of data we have
        unique_dates = set(log.date for log in current_week_logs)
        daily_average = total_minutes // len(unique_dates) if unique_dates else 0
        
        # Find most used app
        app_usage = {}
        for log in current_week_logs:
            app_usage[log.app_name] = app_usage.get(log.app_name, 0) + log.usage_minutes
        
        most_used_app = max(app_usage.items(), key=lambda x: x[1])[0] if app_usage else 'None'
        
        # Calculate weekly change percentage
        previous_total = sum(log.usage_minutes for log in previous_week_logs)
        previous_unique_dates = set(log.date for log in previous_week_logs)
        previous_daily_avg = previous_total // len(previous_unique_dates) if previous_unique_dates else 0
        
        if previous_daily_avg > 0:
            weekly_change = ((daily_average - previous_daily_avg) / previous_daily_avg) * 100
        else:
            weekly_change = 0
        
        # Create or update ScreenTime record
        screen_time = cls.query.filter_by(user_id=user_id, date=today).first()
        if not screen_time:
            screen_time = cls(user_id=user_id, date=today, daily_average=daily_average,
                             most_used_app=most_used_app, weekly_change=int(weekly_change))
            db.session.add(screen_time)
        else:
            screen_time.daily_average = daily_average
            screen_time.most_used_app = most_used_app
            screen_time.weekly_change = int(weekly_change)
        
        db.session.commit()
        return screen_time

class AppLimit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    app_name = db.Column(db.String(100), nullable=False)
    daily_limit_minutes = db.Column(db.Integer, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def __repr__(self):
        return f'<AppLimit {self.app_name} - {self.daily_limit_minutes} mins>'

class DigitalDetoxPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    daily_limit_minutes = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.Date, default=datetime.utcnow().date)
    end_date = db.Column(db.Date, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Detox settings
    enable_app_blocking = db.Column(db.Boolean, default=False)
    enable_notifications = db.Column(db.Boolean, default=True)
    enable_break_reminders = db.Column(db.Boolean, default=True)
    break_interval_minutes = db.Column(db.Integer, default=60)  # Remind every 60 minutes by default
    
    def __repr__(self):
        return f'<DigitalDetoxPlan {self.id} - {self.daily_limit_minutes} mins>'

class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    icon = db.Column(db.String(100))
    criteria = db.Column(db.String(100), nullable=False)  # e.g., "streak:10", "habits:5"
    
    # Relationships
    users = db.relationship('UserAchievement', backref='achievement', lazy=True)
    
    def __repr__(self):
        return f'<Achievement {self.name}>'

class UserAchievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievement.id'), nullable=False)
    earned_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<UserAchievement {self.user_id} - {self.achievement_id}>'

class DigitalTwin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    habit_id = db.Column(db.Integer, db.ForeignKey('habit.id'), nullable=False)
    completion_rate = db.Column(db.Float, default=0.0)  # AI twin's completion rate
    streak = db.Column(db.Integer, default=0)  # AI twin's streak
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref='digital_twin', lazy=True)
    habit = db.relationship('Habit', backref='digital_twin', lazy=True)
    
    def __repr__(self):
        return f'<DigitalTwin for User {self.user_id} - Habit {self.habit_id}>'
