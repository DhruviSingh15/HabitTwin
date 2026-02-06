from app import create_app, db
from app.models import DigitalDetoxPlan

# Create the application context
app = create_app()
with app.app_context():
    # Create the DigitalDetoxPlan table
    print("Creating DigitalDetoxPlan table...")
    db.create_all()
    print("Database updated successfully!")
