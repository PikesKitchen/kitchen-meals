import sqlite3

# Connect to the database (or create it if it doesn't exist)
conn = sqlite3.connect('meals.db')
c = conn.cursor()

# ✅ Meals table
c.execute('''
    CREATE TABLE IF NOT EXISTS meals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        date TEXT NOT NULL,
        qr_code TEXT
    )
''')

# ✅ Reviews table
c.execute('''
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        meal_id INTEGER,
        rating INTEGER,
        comment TEXT,
        suggestion TEXT,
        FOREIGN KEY (meal_id) REFERENCES meals(id)
    )
''')

# ✅ Snacks table (Step 8)
c.execute('''
    CREATE TABLE IF NOT EXISTS snacks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        suggestion TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

# Commit and close connection
conn.commit()
conn.close()
