from app import create_app, db
from app.models import ScreenTimeLog, User, ScreenTime
import random
from datetime import datetime, timedelta

# Create the Flask app
app = create_app()

with app.app_context():
    # Get the first user
    user = User.query.first()
    
    if user:
        print(f"Adding sample data for user: {user.username}")
        
        # Add screen time logs for the past 14 days
        for i in range(14):
            date = (datetime.utcnow() - timedelta(days=i)).date()
            
            # Add logs for different apps
            for app_name in ['Instagram', 'YouTube', 'Twitter', 'TikTok', 'Productivity App']:
                # Random usage between 10 and 120 minutes
                minutes = random.randint(10, 120)
                
                # Create and add the log
                log = ScreenTimeLog(
                    user_id=user.id,
                    date=date,
                    app_name=app_name,
                    usage_minutes=minutes
                )
                db.session.add(log)
        
        # Commit all the logs
        db.session.commit()
        
        # Generate the aggregated screen time data
        screen_time = ScreenTime.generate_from_logs(user.id)
        
        if screen_time:
            print(f"Generated screen time data: {screen_time.daily_average} minutes daily average")
        else:
            print("Failed to generate screen time data")
            
        print("Sample data added successfully!")
    else:
        print("No users found in the database. Please create a user first.")
