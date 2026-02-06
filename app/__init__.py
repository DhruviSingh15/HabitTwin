from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_executor import Executor
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
executor = Executor()

def create_app():
    app = Flask(__name__)
    
    # Configure app
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URI', 'sqlite:///habittwin.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
    app.config['PROFILE_PICS'] = os.path.join(app.config['UPLOAD_FOLDER'], 'profile_pics')
    app.config['EXCEL_FILES'] = os.path.join(app.config['UPLOAD_FOLDER'], 'excel_files')
    
    # Ensure upload directories exist
    os.makedirs(app.config['PROFILE_PICS'], exist_ok=True)
    os.makedirs(app.config['EXCEL_FILES'], exist_ok=True)
    
    # Add context processor for template variables
    @app.context_processor
    def inject_now():
        from datetime import datetime
        return {'now': datetime.utcnow()}
    
    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    migrate.init_app(app, db)
    executor.init_app(app)
    
    # Import and register blueprints
    from app.auth.routes import auth
    from app.main.routes import main
    from app.profile.routes import profile
    from app.habits.routes import habits
    from app.wellbeing.routes import wellbeing
    from app.insights.routes import insights
    from app.gamification.routes import gamification
    from app.chatbot.routes import chatbot
    
    app.register_blueprint(auth)
    app.register_blueprint(main)
    app.register_blueprint(profile)
    app.register_blueprint(habits)
    app.register_blueprint(wellbeing)
    app.register_blueprint(insights)
    app.register_blueprint(gamification)
    app.register_blueprint(chatbot)
    
    # Import models for migrations
    from app.models import User, Habit, HabitLog, ScreenTimeLog, Achievement, UserAchievement
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))
    
    return app
