from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from collections import defaultdict
import qrcode
import os
import re
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = 'something_secret_here'

# ✅ Connect to PostgreSQL with SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ✅ Database models
class Meal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    type = db.Column(db.String(50))
    date = db.Column(db.String(20))
    qr_code = db.Column(db.String(200))

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    meal_id = db.Column(db.Integer, db.ForeignKey('meal.id'))
    rating = db.Column(db.Integer)
    comment = db.Column(db.String(40))
    suggestion = db.Column(db.String(20))

class Snack(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    suggestion = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, server_default=func.now())

# ✅ QR Code
def sanitize_filename(text):
    return re.sub(r'[^a-zA-Z0-9_]', '', text.replace(' ', '_')).lower()

def generate_qr_code(meal_id, meal_name, meal_date):
    url = f'https://kitchen-meals.onrender.com/form/{meal_id}'
    img = qrcode.make(url)
    filename = f'qr_{sanitize_filename(meal_name)}_{meal_date}.png'
    path = os.path.join('static', filename)
    img.save(path)
    return filename

@app.route('/')
def home():
    if not session.get('authenticated'):
        return redirect(url_for('login'))

    meals = Meal.query.order_by(Meal.date.desc()).all()
    stats = db.session.query(
        Review.meal_id,
        db.func.round(db.func.avg(Review.rating), 2).label('avg_rating'),
        db.func.count().label('review_count')
    ).filter(Review.rating != None).group_by(Review.meal_id).all()
    
    meal_stats = {s.meal_id: s for s in stats}
    return render_template('index.html', meals=meals, meal_stats=meal_stats)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['password'] == '1717':
            session['authenticated'] = True
            return redirect(url_for('home'))
        error = 'Incorrect password. Please try again.'
    return render_template('login.html', error=error)

@app.route('/add_meal', methods=['POST'])
def add_meal():
    name = request.form['mealName']
    meal_type = request.form['mealType']
    date = request.form['mealDate']

    meal = Meal(name=name, type=meal_type, date=date)
    db.session.add(meal)
    db.session.commit()

    qr_filename = generate_qr_code(meal.id, name, date)
    meal.qr_code = qr_filename
    db.session.commit()

    return redirect(url_for('home'))

@app.route('/delete_meal/<int:meal_id>', methods=['POST'])
def delete_meal(meal_id):
    meal = Meal.query.get(meal_id)
    if meal:
        if meal.qr_code:
            path = os.path.join('static', meal.qr_code)
            if os.path.exists(path):
                os.remove(path)
        Review.query.filter_by(meal_id=meal_id).delete()
        db.session.delete(meal)
        db.session.commit()
    return redirect(url_for('home'))

@app.route('/form/<int:meal_id>')
def form(meal_id):
    return render_template('form.html', meal_id=meal_id)

@app.route('/submit_review/<int:meal_id>', methods=['POST'])
def submit_review(meal_id):
    rating = request.form.get('rating')
    comment = request.form.get('comment')
    suggestion = request.form.get('suggestion')
    review = Review(meal_id=meal_id, rating=rating, comment=comment, suggestion=suggestion)
    db.session.add(review)
    db.session.commit()
    return "<h2>Thank you for your feedback!</h2><p>You can now close this page.</p>"

@app.route('/comments')
def comments():
    results = db.session.query(Review, Meal).join(Meal).filter(
        Review.comment != None, Review.comment != ''
    ).order_by(Meal.date.desc()).all()

    grouped = defaultdict(list)
    for review, meal in results:
        grouped[meal.name].append({'id': review.id, 'comment': review.comment})

    return render_template('comments.html', grouped_comments=grouped)

@app.route('/delete_comment/<int:comment_id>', methods=['POST'])
def delete_comment(comment_id):
    Review.query.filter_by(id=comment_id).delete()
    db.session.commit()
    return redirect(url_for('comments'))

@app.route('/recommended')
def recommended():
    suggestions = db.session.query(
        db.func.lower(Review.suggestion).label("name"),
        db.func.count().label("count")
    ).filter(Review.suggestion != None, Review.suggestion != '').group_by("name").order_by(db.desc("count")).all()
    return render_template('recommended.html', suggestions=suggestions)

@app.route('/delete_suggestion', methods=['POST'])
def delete_suggestion():
    suggestion = request.form['suggestion']
    Review.query.filter(db.func.lower(Review.suggestion) == suggestion.lower()).delete()
    db.session.commit()
    return redirect(url_for('recommended'))

@app.route('/snack_form')
def snack_form():
    return render_template('snack_form.html')

@app.route('/submit_snack', methods=['POST'])
def submit_snack():
    snack = request.form['snack']
    db.session.add(Snack(suggestion=snack))
    db.session.commit()
    return "<h2>Thank you for your snack suggestion!</h2><p>You can now close this page.</p>"

@app.route('/snacks')
def snacks():
    snacks = Snack.query.order_by(Snack.created_at.desc()).all()
    return render_template('snacks.html', snacks=snacks)

@app.route('/delete_snack/<int:snack_id>', methods=['POST'])
def delete_snack(snack_id):
    Snack.query.filter_by(id=snack_id).delete()
    db.session.commit()
    return redirect(url_for('snacks'))

if __name__ == '__main__':
    app.run(debug=True)
