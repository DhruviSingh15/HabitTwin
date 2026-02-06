# 🧠 HabitTwin – Your Digital Twin for Habit Building

HabitTwin is a habit-tracking and self-improvement web application that creates a **digital twin of user behavior** to analyze habits, track progress, and generate meaningful insights.  
Built using **Flask**, **SQLite**, and modern frontend technologies, the project focuses on consistency, analytics, and long-term personal growth.

---

## 🚀 Features

- 🔐 User authentication and profile management  
- 📊 Habit creation, tracking, and streak monitoring  
- 🧠 Digital Twin concept to model user behavior  
- 📈 Progress analytics and insights  
- 🗂️ Modular Flask architecture  
- ⚡ Clean and responsive UI  
- 🧪 Sample data generation for testing  

---

## 🛠 Tech Stack

### Backend
- **Python (Flask)**
- **Flask-SQLAlchemy**
- **SQLite**
- **Flask-Migrate**

### Frontend
- **HTML**
- **CSS**
- **JavaScript**

---

## 📁 Project Structure
```
HabitTwin/
├── app/ # Application modules
├── instance/ # Instance-specific config & DB
├── migrations/ # Database migrations
├── static/ # CSS, JS, assets
├── app.py # Main Flask entry point
├── init_db.py # Initialize database
├── add_sample_data.py # Insert demo/sample data
├── list_users.py # Utility script to list users
├── LICENSE # MIT License
└── README.md # Project documentation
```

---

## ⚙️ Setup & Installation

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/your-username/HabitTwin.git
cd HabitTwin
2️⃣ Create Virtual Environment (Optional)
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate # Linux/Mac
```
3️⃣ Install Dependencies
```bash
pip install -r requirements.txt
```
4️⃣ Initialize Database
```bash
python init_db.py
```
5️⃣ (Optional) Add Sample Data
```bash
python add_sample_data.py
```
6️⃣ Run the Application
```bash
python app.py
```
Open browser at:
```bash
http://localhost:5000
```
