from flask import Flask, render_template, url_for, redirect, request, flash, send_from_directory, jsonify, session
import smtplib
import secrets
import random
import datetime
import os
from waitress import serve
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Boolean
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user

ASSETS_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = "Yoursecret"
EMAIL_PASSWORD = "Your email password"
EMAIL_NAME = "Your email name"


# CREATE DATABASE
class Base(DeclarativeBase):
    pass

# This datavase is offline
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://admin:willemerasmus@flaskdb.chouyammgprj.us-east-1.rds.amazonaws.com/macrodb'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)



# CONFIGURE FLASK-LOGIN'S LOGIN MANAGER
login_manager = LoginManager()
login_manager.init_app(app)


# CREATE A USER_LOADER CALLBACK
@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)


# CREATE TABLE IN DB
class User(UserMixin, db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)
    password: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(1000))
    api_key: Mapped[str] = mapped_column(String(20))
    session_available: Mapped[bool] = mapped_column(Boolean())
    last_trade: Mapped[str] = mapped_column(String(50))

    def __init__(self, email, password, name, api_key, session_available, last_trade):
        self.email = email
        self.password = password
        self.name = name
        self.api_key = api_key
        self.session_available = session_available
        self.last_trade = last_trade


class Trade(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(6), nullable=False)
    buy_or_sell: Mapped[str] = mapped_column(String(4), nullable=False)
    risk_perc: Mapped[str] = mapped_column(String(4), nullable=False)
    sl: Mapped[str] = mapped_column(String(6), nullable=False)
    tp: Mapped[str] = mapped_column(String(6), nullable=False)
    time_of_posting: Mapped[str] = mapped_column(String(50))

    def __init__(self, symbol, buy_or_sell, risk_perc, sl, tp, time_of_posting):
        self.symbol = symbol
        self.risk_perc = risk_perc
        self.buy_or_sell = buy_or_sell
        self.sl = sl
        self.tp = tp
        self.time_of_posting = time_of_posting


@app.route('/')
def home():
    return render_template('index.html', logged_in=current_user.is_authenticated)


@app.route('/contact', methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        subject = (f"MACRO PERSPECTIVE: My name is {request.form.get('name')} and my "
                   f"email is {request.form.get('email')}")
        message = request.form.get('message')

        connection = smtplib.SMTP("smtp.gmail.com")
        connection.starttls()
        connection.login(user=EMAIL_NAME, password=EMAIL_PASSWORD)
        connection.sendmail(from_addr=EMAIL_NAME, to_addrs=EMAIL_NAME, msg=f"Subject:{subject}\n\n{message}")
        connection.close()
        return redirect(url_for('home'))
    return render_template('contact.html', logged_in=current_user.is_authenticated)


@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get('email')
        result = db.session.execute(db.select(User).where(User.email == email))
        user = result.scalar()
        if user:
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))

        numbers = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
        secret = ""
        for n in range(4):
            secret += str(random.choice(numbers))
        connection = smtplib.SMTP("smtp.gmail.com")
        connection.starttls()
        connection.login(user=EMAIL_NAME, password=EMAIL_PASSWORD)
        connection.sendmail(from_addr=EMAIL_NAME, to_addrs=email, msg=f"Subject: Macro Perspective\n\nVerification code"
                                                                      f":{secret}")
        connection.close()
        session['verification_code'] = secret
        session['password'] = request.form.get('password')
        session['email'] = email
        session['name'] = request.form.get('name')
        return redirect(url_for('verify'))

    return render_template("register.html", logged_in=current_user.is_authenticated)


@app.route('/register/verification', methods=["GET", "POST"])
def verify():
    email = session.get('email').lower()
    if request.method == "POST":
        user_verification = str(request.form.get("verification_code"))
        verification_code = session.get("verification_code")
        name = session.get('name')

        password = session.get('password')
        print(f"{name}, {email}, {password}")
        if user_verification == verification_code:
            hashed_password = generate_password_hash(
                password,
                method='pbkdf2:sha256',
                salt_length=8
            )

            api_key = secrets.token_urlsafe(20)

            new_user = User(
                email=email,
                name=name,
                password=hashed_password,
                api_key=api_key,
                session_available=True,
                last_trade="nothing",
            )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('account'))
        else:
            return redirect(url_for('register'))
    return render_template('verify.html', verification_email=email)


@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get('email').lower()
        password = request.form.get('password')

        # Find user by email entered.
        result = db.session.execute(db.select(User).where(User.email == email))
        user = result.scalar()

        # Email doesn't exist or password incorrect.
        if not user:
            flash("That email does not exist, please try again.")
            return redirect(url_for('login'))
        elif not check_password_hash(user.password, password):
            flash('Password incorrect, please try again.')
            return redirect(url_for('login'))
        else:
            login_user(user)
            return redirect(url_for('account'))

    return render_template("login.html", logged_in=current_user.is_authenticated)


@app.route('/account')
@login_required
def account():
    return render_template("account.html",
                           name=current_user.name,
                           api_key=current_user.api_key,
                           id=current_user.id,
                           logged_in=current_user.is_authenticated)


@app.route('/account/download-ea')
@login_required
def download_ea():
    return send_from_directory('static', 'files/MacroPerspective.ex5')


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))



# @app.route('/trade')
# def get_latest_trade_id():
#     result = db.session.query(Trade).order_by(Trade.id.desc()).first()
#     latest_trade = result
#     print(latest_trade)
#     return jsonify(trade={
#         "id": latest_trade.id
#     })


@app.route('/trade/<user_id>')
def get_latest_trade(user_id):
    api_key = request.args.get("api_key")
    user = db.get_or_404(User, user_id)
    latest_trade = db.session.query(Trade).order_by(Trade.id.desc()).first()
    if api_key == user.api_key and user.session_available:
        user.session_available = False
        current_time = datetime.datetime.now()
        if len(str(current_time.minute)) == 1:
            user.last_trade = (f"Your last trade was on {current_time.day}/{current_time.month}/{current_time.year} at "
                               f"{current_time.hour}:0{current_time.minute}")
        else:
            user.last_trade = (f"Your last trade was on {current_time.day}/{current_time.month}/{current_time.year} at "
                               f"{current_time.hour}:{current_time.minute}")
        db.session.commit()
        return jsonify(message1={
            "symbol": latest_trade.symbol,
            "buy or sell": latest_trade.buy_or_sell,
            "risk percentage": latest_trade.risk_perc,
            "stop loss": latest_trade.sl,
            "take profit": latest_trade.tp,
        })
    elif not user.session_available and api_key == user.api_key:
        return jsonify(message2={
                        "Previous trade received": user.last_trade,
                        "Latest Trade": latest_trade.time_of_posting,
                        "Error": "No New Trades available"})
    else:
        return jsonify(message3={"error": "Wrong API key"}), 404


@app.route('/post_new_trade', methods=["GET", "POST"])
def post_new_trade():
    args = request.args.get('symbol').split('?')
    current_time = datetime.datetime.now()
    if len(str(current_time.minute)) == 1:
        time_of_posting = (f"The last trade was posted on {current_time.day}/{current_time.month}/{current_time.year} "
                           f"at {current_time.hour}:0{current_time.minute}")
        time_of_posting_msg = (f"Successfully posted the latest trade on {current_time.day}/{current_time.month}/"
                               f"{current_time.year} at {current_time.hour}:0{current_time.minute}!")
    else:
        time_of_posting_msg = (f"Successfully posted the latest trade on {current_time.day}/{current_time.month}/"
                               f"{current_time.year} at {current_time.hour}:{current_time.minute}!")
        time_of_posting = (f"The last trade was posted on {current_time.day}/{current_time.month}/{current_time.year} "
                           f"at {current_time.hour}:{current_time.minute}")
    new_trade = Trade(
        symbol=args[0],
        buy_or_sell=args[1].split("=")[1],
        risk_perc=args[2].split("=")[1],
        sl=args[3].split("=")[1],
        tp=args[4].split("=")[1],
        time_of_posting=time_of_posting,
    )
    db.session.add(new_trade)
    db.session.commit()
    all_users = db.session.execute(db.select(User).order_by(User.id)).scalars().all()
    for user in all_users:
        user.session_available = True
        db.session.commit()
    return jsonify(response={
        "success": f"{time_of_posting_msg}"}), 200


mode = "dev"

if __name__ == "__main__":
    if mode == "prod":
        serve(app, host='127.0.0.1', port=8000, url_scheme="https")
    elif mode == "dev":
        app.run(debug=True)
