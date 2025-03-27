from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import qrcode
import os
import re
from collections import defaultdict

app = Flask(__name__)
app.secret_key = 'something_secret_here'  # Required for session handling

def get_db_connection():
    conn = sqlite3.connect('meals.db')
    conn.row_factory = sqlite3.Row
    return conn

# ✅ Sanitize meal name for safe filenames
def sanitize_filename(text):
    return re.sub(r'[^a-zA-Z0-9_]', '', text.replace(' ', '_')).lower()

# ✅ Generate QR code image with custom filename
def generate_qr_code(meal_id, meal_name, meal_date):
    url = f'https://kitchen-meals.onrender.com/form/{meal_id}'
    img = qrcode.make(url)

    safe_name = sanitize_filename(meal_name)
    filename = f'qr_{safe_name}_{meal_date}.png'
    qr_path = os.path.join('static', filename)
    img.save(qr_path)

    return filename

def generate_snack_qr():
    url = 'https://kitchen-meals.onrender.com/snack_form'
    img = qrcode.make(url)
    img.save('static/snack_qr.png')

@app.route('/')
def home():
    if not session.get('authenticated'):
        return redirect(url_for('login'))

    conn = get_db_connection()
    meals = conn.execute('SELECT * FROM meals ORDER BY date DESC').fetchall()

    stats = conn.execute('''
        SELECT meal_id, 
               ROUND(AVG(rating), 2) AS avg_rating, 
               COUNT(*) AS review_count
        FROM reviews
        WHERE rating IS NOT NULL
        GROUP BY meal_id
    ''').fetchall()

    meal_stats = {stat['meal_id']: stat for stat in stats}
    conn.close()
    return render_template('index.html', meals=meals, meal_stats=meal_stats)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['password'] == '1717':
            session['authenticated'] = True
            return redirect(url_for('home'))
        else:
            error = 'Incorrect password. Please try again.'
    return render_template('login.html', error=error)

@app.route('/add_meal', methods=['POST'])
def add_meal():
    name = request.form['mealName']
    meal_type = request.form['mealType']
    date = request.form['mealDate']

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO meals (name, type, date) VALUES (?, ?, ?)',
                   (name, meal_type, date))
    meal_id = cursor.lastrowid

    # ✅ Generate QR with custom filename
    qr_filename = generate_qr_code(meal_id, name, date)
    cursor.execute('UPDATE meals SET qr_code = ? WHERE id = ?', (qr_filename, meal_id))

    conn.commit()
    conn.close()

    return redirect(url_for('home'))

@app.route('/delete_meal/<int:meal_id>', methods=['POST'])
def delete_meal(meal_id):
    conn = get_db_connection()
    qr_code = conn.execute('SELECT qr_code FROM meals WHERE id = ?', (meal_id,)).fetchone()
    if qr_code and qr_code['qr_code']:
        qr_path = os.path.join('static', qr_code['qr_code'])
        if os.path.exists(qr_path):
            os.remove(qr_path)

    conn.execute('DELETE FROM reviews WHERE meal_id = ?', (meal_id,))
    conn.execute('DELETE FROM meals WHERE id = ?', (meal_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('home'))

@app.route('/form/<int:meal_id>')
def form(meal_id):
    return render_template('form.html', meal_id=meal_id)

@app.route('/submit_review/<int:meal_id>', methods=['POST'])
def submit_review(meal_id):
    rating = request.form.get('rating')
    comment = request.form.get('comment')
    suggestion = request.form.get('suggestion')

    conn = get_db_connection()
    conn.execute('INSERT INTO reviews (meal_id, rating, comment, suggestion) VALUES (?, ?, ?, ?)',
                 (meal_id, rating, comment, suggestion))
    conn.commit()
    conn.close()

    return "<h2>Thank you for your feedback!</h2><p>You can now close this page.</p>"

@app.route('/comments')
def comments():
    conn = get_db_connection()
    data = conn.execute('''
        SELECT reviews.id, reviews.comment, meals.name AS meal_name
        FROM reviews
        JOIN meals ON reviews.meal_id = meals.id
        WHERE reviews.comment IS NOT NULL AND reviews.comment != ''
        ORDER BY meals.date DESC
    ''').fetchall()
    conn.close()

    grouped = defaultdict(list)
    for row in data:
        grouped[row['meal_name']].append(row)

    return render_template('comments.html', grouped_comments=grouped)

@app.route('/delete_comment/<int:comment_id>', methods=['POST'])
def delete_comment(comment_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM reviews WHERE id = ?', (comment_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('comments'))

@app.route('/recommended')
def recommended():
    conn = get_db_connection()
    suggestions = conn.execute('''
        SELECT LOWER(suggestion) AS name, COUNT(*) AS count
        FROM reviews
        WHERE suggestion IS NOT NULL AND suggestion != ''
        GROUP BY name
        ORDER BY count DESC
    ''').fetchall()
    conn.close()
    return render_template('recommended.html', suggestions=suggestions)

@app.route('/delete_suggestion', methods=['POST'])
def delete_suggestion():
    suggestion = request.form['suggestion']
    conn = get_db_connection()
    conn.execute('DELETE FROM reviews WHERE LOWER(suggestion) = LOWER(?)', (suggestion,))
    conn.commit()
    conn.close()
    return redirect(url_for('recommended'))

@app.route('/snack_form')
def snack_form():
    return render_template('snack_form.html')

@app.route('/submit_snack', methods=['POST'])
def submit_snack():
    snack = request.form['snack']
    conn = get_db_connection()
    conn.execute('INSERT INTO snacks (suggestion) VALUES (?)', (snack,))
    conn.commit()
    conn.close()
    return "<h2>Thank you for your snack suggestion!</h2><p>You can now close this page.</p>"

@app.route('/snacks')
def snacks():
    conn = get_db_connection()
    snacks = conn.execute('SELECT * FROM snacks ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('snacks.html', snacks=snacks)

@app.route('/delete_snack/<int:snack_id>', methods=['POST'])
def delete_snack(snack_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM snacks WHERE id = ?', (snack_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('snacks'))

if __name__ == '__main__':
    app.run(debug=True)
