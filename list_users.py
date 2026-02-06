from app import create_app, db
from app.models import User

def list_registered_users():
    app = create_app()
    with app.app_context():
        # Get all users
        users = User.query.all()
        
        if not users:
            print("No users found in the database.")
            return
            
        print("\nRegistered Users:")
        print("----------------")
        for user in users: 
            print(f"Username: {user.username}")
            print(f"Email: {user.email}")
            print("----------------")

if __name__ == '__main__':
    list_registered_users()