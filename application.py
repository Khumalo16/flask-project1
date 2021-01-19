import os

from flask import Flask, session, render_template, request, redirect, url_for,flash
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from datetime import timedelta, date, datetime


app = Flask(__name__)
Session(app)
app.permanent_session_lifetime = timedelta(minutes=10)

user = 0
# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine("postgresql://hhlfjdydmhizma:f2137338537e4dd691d12095ab2abf893b8bfca7b2b72d74a260c27367a6111a@ec2-54-144-196-35.compute-1.amazonaws.com:5432/d4edp75p3661vk")
db = scoped_session(sessionmaker(bind=engine))

isbn = db.execute("SELECT id, isbn, title,author, year FROM books WHERE id = 2").fetchone()
@app.route("/login")
def index():
    return render_template('book/index.html')

@app.route("/registrationPage", methods=["POST", "GET"])
def registrationPage():
    return render_template('book/registrationPage.html')

@app.route("/registration", methods=["POST", "GET"])
def registration():
    if request.method == "GET":
        return render_template('book/registrationPage.html')
    name = request.form.get("name")
    surname = request.form.get("surname")
    username = request.form.get("username")
    password = request.form.get("password")
    confirm = request.form.get("confirm")

    select = "SELECT id FROM users WHERE username = :username"
    insert = "INSERT INTO users (name, surname, username, password) VALUES (:name, :surname, :username, :password)"
    
    if password != confirm:
        flash("Password does not match")
        return  redirect(url_for('registrationPage'))
    
    user_id = db.execute(select,{"username": username}).rowcount
 
    if user_id != 0:
        flash("username is not available, please choose another one!")
        return redirect(url_for('registrationPage'))
        
    db.execute(insert,{"name":name, "surname": surname, "username": username, "password": password})
    db.commit()

    flash("You are successful registered in Books review store website!")
    return  redirect(url_for('index'))

@app.route("/search", methods=["POST"])
def login():
    if request.method == "POST":
       
        username = request.form.get("username")
        password = request.form.get("password")
        select = "SELECT * FROM users WHERE username = :username AND password = :password"

        if db.execute(select,{"username": username, "password": password}).rowcount == 0:
            flash("incorect username/password")
            return redirect(url_for('index'))

        select = "SELECT * FROM users WHERE username = :username"
        user_id = db.execute(select,{"username": username}).fetchone()

        session.permanent = True
        session["user_id"] = user_id[0]
        user = user_id[0]
        return render_template('book/search.html')
    return  redirect(url_for('index'))

@app.route("/search", methods=["GET"])
def check():
    if session.get("user_id") is not None:
        return render_template('book/search.html')

    return redirect(url_for('index'))

@app.route("/loginout")
def logout():
    session.clear()
    flash("You have loged out")
    return redirect(url_for('index'))

@app.route("/book", methods=["POST","GET"])
def book():
    
    select = "SELECT * FROM books WHERE isbn LIKE :isbn OR title LIKE :title OR author LIKE :author"
    if session.get("user_id") is None:
        return redirect(url_for('index'))
    if request.method == "POST":
        book = request.form.get("book")
        getbook = db.execute(select,{"isbn":"%"+book+"%", "title": "%"+book+"%", "author":"%"+book+"%"}).fetchall()
        session["getbook"] = getbook

        if not getbook:
            return render_template('book/noBookFound.html') 
    if request.method == "GET":
        if not session.get("getbook"):
            return render_template('book/noBookFound.html')
        
    return render_template('book/results.html', books=session.get("getbook"))

@app.route("/details/<string:isbn>", methods=["POST","GET"])
def details(isbn):
    if session.get("user_id") is None:
        return redirect(url_for('index'))

    if request.method == "GET":
        session['isbn'] = isbn
    session["isbn"] = isbn
    user_id = session["user_id"]
    isbn_id = db.execute("SELECT id FROM books WHERE isbn = :isbn",{"isbn": isbn}).fetchone()
    isbn_id = isbn_id[0]
    details = db.execute("SELECT isbn, title, author, year FROM books WHERE isbn = :isbn",{"isbn": isbn}).fetchone()
    select = "SELECT name, surname, reviews, time, rate, realtime FROM reviews JOIN users ON users.id = reviews.user_id JOIN books ON books.id = reviews.isbn_id WHERE isbn_id = :isbn_id"
    reviews = db.execute(select, {"isbn_id":isbn_id}).fetchall()
    print(reviews)
    rates = []
    for rate in range(1,6):
        rates.append(rate)
        rate+=1
    return render_template('book/review.html', details=details, reviews=reviews,rates=rates)


@app.route("/review", methods=["POST", "GET"])
def review():
    if session.get("user_id") is None:
        return redirect(url_for('index'))

    if request.method == "POST":
        user_id = session["user_id"]
        isbn = session["isbn"]
        rate = int(request.form.get("rate"))
        review = request.form.get("reviews")
        today = date.today()
        now = datetime.now()
        now = str(now.hour) +":" + str(now.minute)
        time = today.strftime("%b %d ,%Y")

        if review is None:
            flash("Write something if you would like to review on this book!")
            return redirect(('details/' + isbn))
        
        # check if the book has reviewed already
        isbn_id = db.execute("SELECT id FROM books WHERE isbn = :isbn",{"isbn": isbn}).fetchone()
        isbn_id = isbn_id[0]
        print(isbn_id)
        select_user = "SELECT * FROM reviews JOIN users ON users.id = reviews.user_id JOIN books ON books.id = reviews.isbn_id WHERE user_id = :user_id AND isbn_id = :isbn_id"
        
        reviewed = db.execute(select_user,{"user_id":user_id, "isbn_id": isbn_id}).fetchone()
        if reviewed is None:
            db.execute("INSERT INTO reviews (user_id, isbn_id, reviews, time, rate, realtime) VALUES (:user_id, :isbn_id, :reviews, :time, :rate, :realtime)",
                       {"user_id": user_id, "isbn_id": isbn_id, "reviews":review, "time": time, "rate":rate, "realtime": now})
            db.commit()
            return redirect(('details/' + isbn))        
        else:
            timereviewed = reviewed.time
            now = reviewed.realtime
            flash("You've reviewed this book date " + timereviewed + " at "+ now)
            return redirect(('details/' + isbn))
    return redirect(('book' + isbn))