from app import create_app, db
from app.models import AppLimit

# Create the application context
app = create_app()
with app.app_context():
    # Create the AppLimit table
    print("Creating AppLimit table...")
    db.create_all()
    print("Database updated successfully!")
