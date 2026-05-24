import os
import sqlite3
import json
import secrets
from datetime import datetime
from flask import Flask, request, redirect, url_for, session, flash, send_file, abort, jsonify, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "SUPER_SECRET_KEY_CHANGE_THIS"

# =========================
# CONFIG
# =========================
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, "biez_audio_store.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads_protected")
COVER_FOLDER = os.path.join(BASE_DIR, "static", "covers")
ALLOWED_AUDIO = {"mp3", "wav"}
ALLOWED_IMAGES = {"png", "jpg", "jpeg", "webp"}

ADMIN_USERNAME = "KAVIRU"
ADMIN_PASSWORD = "BIEZ2005"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(COVER_FOLDER, exist_ok=True)
os.makedirs("static", exist_ok=True)

# =========================
# DATABASE
# =========================
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        email TEXT,
        phone TEXT,
        password_hash TEXT
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS audios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        filename TEXT,
        cover_image TEXT,
        genre TEXT,
        price REAL,
        duration TEXT,
        upload_date TEXT,
        active INTEGER DEFAULT 1
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        audio_id INTEGER,
        paid INTEGER,
        amount REAL,
        receipt_number TEXT,
        downloads_remaining INTEGER DEFAULT 1,
        purchase_date TEXT
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS payment_callbacks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mpesa_receipt TEXT,
        phone TEXT,
        amount REAL,
        status TEXT,
        raw_callback_json TEXT
    )
    ''')

    conn.commit()
    conn.close()


init_db()

# =========================
# HELPERS
# =========================
def allowed_audio(filename):
    return "." in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_AUDIO


def allowed_image(filename):
    return "." in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGES


def current_user():
    if 'user_id' not in session:
        return None

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    conn.close()
    return user


def user_paid(user_id, audio_id):
    conn = get_db()

    purchase = conn.execute(
        "SELECT * FROM purchases WHERE user_id=? AND audio_id=? AND paid=1",
        (user_id, audio_id)
    ).fetchone()

    conn.close()
    return purchase


def is_admin():
    return session.get("admin") == True


# =========================
# HOME
# =========================
@app.route('/')
def home():
    conn = get_db()
    audios = conn.execute("SELECT * FROM audios WHERE active=1 ORDER BY id DESC").fetchall()
    conn.close()

    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
<title>BIEZ KAVIRU MUSIC STORE</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="Buy premium audios securely with M-Pesa">

<style>

*{
margin:0;
padding:0;
box-sizing:border-box;
}

body{
overflow-x:hidden;
}

.container{
width:100%;
max-width:1400px;
margin:auto;
padding:20px;
}

img{
max-width:100%;
height:auto;
display:block;
}

input,button{
max-width:100%;
}

.grid{
display:grid;
grid-template-columns:repeat(auto-fit,minmax(280px,1fr));
gap:20px;
}

@media(max-width:768px){

header{
flex-direction:column;
gap:15px;
text-align:center;
}

.nav{
display:flex;
flex-wrap:wrap;
justify-content:center;
gap:10px;
}

}

body{
background:url('/static/backgrounds/main_bg.jpg');
background-size:cover;
background-position:center;
background-attachment:fixed;
background-repeat:no-repeat;
font-family:Arial;
color:white;
margin:0;
padding:0;
}
header{

background:
linear-gradient(
90deg,
rgba(0,15,18,0.92),
rgba(0,35,40,0.88),
rgba(0,15,18,0.92)
);

backdrop-filter:blur(14px);

border-bottom:1px solid rgba(0,255,204,0.18);

box-shadow:
0 4px 25px rgba(0,255,204,0.08),
0 8px 40px rgba(0,0,0,0.55);

padding:18px 24px;

display:flex;

justify-content:space-between;

align-items:center;

position:sticky;

top:0;

z-index:999;
}
.logo{

font-size:32px;

font-weight:900;

letter-spacing:3px;

text-transform:uppercase;

padding:10px 22px;

border-radius:16px;

color:#ffffff;

background:
linear-gradient(
135deg,
rgba(0,255,204,0.16),
rgba(0,180,255,0.12),
rgba(255,255,255,0.06)
);

border:1px solid rgba(0,255,204,0.22);

backdrop-filter:blur(12px);

box-shadow:
0 0 18px rgba(0,255,204,0.12),
0 6px 25px rgba(0,0,0,0.35);

text-shadow:
0 2px 8px rgba(0,0,0,0.65);

position:relative;

overflow:hidden;
}

.logo::before{

content:"";

position:absolute;

top:0;
left:-120%;

width:70%;
height:100%;

background:
linear-gradient(
90deg,
transparent,
rgba(255,255,255,0.18),
transparent
);

transform:skewX(-25deg);

animation:shine 4s linear infinite;
}

@keyframes shine{

100%{
left:160%;
}

}
.container{
padding:20px;
}
.grid{
display:grid;
grid-template-columns:repeat(auto-fit,minmax(250px,1fr));
gap:20px;
}
.card{
background:#1b1b1b;
border-radius:15px;
overflow:hidden;
box-shadow:0 0 10px rgba(0,0,0,0.4);
}
.card img{
width:100%;
height:220px;
object-fit:cover;
}
.card-content{
padding:15px;
}
.btn{
display:inline-block;
padding:10px 18px;
background:#00cc77;
color:white;
text-decoration:none;
border-radius:10px;
margin-top:10px;
}
.nav a{

color:#ffffff;

margin-left:18px;

text-decoration:none;

font-weight:bold;

font-size:16px;

transition:0.2s;

text-shadow:
0 0 5px rgba(255,255,255,0.4);
}

.nav a:hover{

color:#00ffcc;

text-shadow:
0 0 5px #00ffcc,
0 0 15px #00ffcc,
0 0 25px #00ffcc;

transform:scale(1.08);
}

#splash-screen{

position:fixed;
top:0;
left:0;

width:100%;
height:100vh;

background:
linear-gradient(rgba(0,0,0,0.88),rgba(0,0,0,0.92)),
url('/static/backgrounds/main_bg.jpg');

background-size:cover;
background-position:center;

display:flex;
flex-direction:column;
justify-content:center;
align-items:center;

z-index:999999;

transition:0.8s ease;
}

.splash-logo{

width:170px;

animation:
logoFloat 2s ease-in-out infinite,
logoGlow 2s infinite alternate;
}

.splash-title{

margin-top:25px;

font-size:55px;

font-weight:bold;

letter-spacing:4px;

color:#00ff99;

text-align:center;

text-shadow:
0 0 10px #00ff99,
0 0 25px #00ff99,
0 0 50px rgba(0,255,153,0.7);

animation:fadeText 2s ease;
}

.loader{

margin-top:35px;

width:70px;
height:70px;

border:5px solid rgba(255,255,255,0.08);

border-top:5px solid #00ff99;

border-radius:50%;

animation:spin 1s linear infinite;
}

@keyframes spin{

100%{
transform:rotate(360deg);
}

}

@keyframes logoFloat{

0%{
transform:translateY(0px);
}

50%{
transform:translateY(-10px);
}

100%{
transform:translateY(0px);
}

}

@keyframes logoGlow{

from{
filter:drop-shadow(0 0 5px #00ff99);
}

to{
filter:drop-shadow(0 0 25px #00ff99);
}

}

@keyframes fadeText{

from{
opacity:0;
transform:translateY(20px);
}

to{
opacity:1;
transform:translateY(0);
}

}

@media(max-width:768px){

.loader{
width:55px;
height:55px;
}

}

.neon-heading{

font-size:48px;

margin-top:45vh;

margin-bottom:35px;

font-weight:900;

letter-spacing:4px;

text-transform:uppercase;

text-align:center;

color:#f5f5f5;

text-shadow:
0 3px 10px rgba(0,0,0,0.95),
0 6px 25px rgba(0,0,0,0.85);

position:relative;
}

.neon-heading::after{

content:"";

display:block;

width:140px;

height:3px;

margin:14px auto 0 auto;

border-radius:10px;

background:linear-gradient(
90deg,
transparent,
rgba(255,255,255,0.95),
transparent
);

box-shadow:
0 0 10px rgba(0,0,0,0.45);
}

.card{

background:rgba(10,10,10,0.82);

border-radius:20px;

overflow:hidden;

border:1px solid rgba(0,255,204,0.15);

backdrop-filter:blur(10px);

box-shadow:
0 0 15px rgba(0,255,204,0.08),
0 0 40px rgba(0,0,0,0.6);

transition:0.35s;
}

.card:hover{

transform:translateY(-8px) scale(1.02);

box-shadow:
0 0 20px rgba(0,255,204,0.25),
0 0 50px rgba(0,255,204,0.18);
}

.btn{

display:inline-block;

padding:12px 22px;

background:linear-gradient(45deg,#00ffcc,#00ccff);

color:black;

font-weight:bold;

text-decoration:none;

border-radius:14px;

margin-top:12px;

transition:0.3s;

box-shadow:
0 0 10px rgba(0,255,204,0.35);
}

.btn:hover{

transform:scale(1.05);

box-shadow:
0 0 20px rgba(0,255,204,0.55);
}

@keyframes neonPulse{

from{

text-shadow:
0 0 5px #00ffcc,
0 0 10px #00ffcc,
0 0 20px #00ffcc;
}

to{

text-shadow:
0 0 10px #00ffcc,
0 0 20px #00ffcc,
0 0 40px #00ffcc,
0 0 70px rgba(0,255,204,0.9);
}
}

</style>
</head>

<div id="splash-screen">

<h1 class="splash-title">
BIEZ KAVIRU MUSIC STORE
</h1>

<div class="loader"></div>

</div>

<div id="main-content" style="display:none;">
<header>
<div class="logo neon-logo">
BIEZ KAVIRU MUSIC STORE
</div>
<div class="nav neon-nav">
<a href="/">Home</a>
{% if session.get('user_id') %}
<a href="/dashboard">Dashboard</a>
<a href="/logout">Logout</a>
{% else %}
<a href="/login">Login</a>
<a href="/register">Register</a>
{% endif %}
<a href="/admin">Admin</a>
</div>
</header>

<div class="container">
<h2 class="neon-heading">
Welcome to Kaviru Entertainment Home
</h2>

<p style="
text-align:center;
max-width:900px;
margin:20px auto 50px auto;
font-size:20px;
line-height:1.8;
color:#f5f5f5;

text-shadow:
0 2px 8px rgba(0,0,0,0.9);

background:rgba(0,0,0,0.25);

padding:22px 28px;

border-radius:18px;

backdrop-filter:blur(10px);

border:1px solid rgba(255,255,255,0.08);
">
Experience the sound of passion, creativity, and authentic entertainment.
Discover premium audio content crafted to inspire, entertain, and connect you to the Kaviru vibe.
</p>
<div class="grid">
{% for audio in audios %}
<div class="card">
<img src="/{{ audio['cover_image'] }}">
<div class="card-content">
<h3>{{ audio['title'] }}</h3>
<p>Genre: {{ audio['genre'] }}</p>
<p>Duration: {{ audio['duration'] }}</p>
<p>KES {{ audio['price'] }}</p>
<a class="btn" href="/audio/{{ audio['id'] }}">Listen (Audio)</a>
</div>
</div>
{% endfor %}
</div>
</div>
</div>

<script>

window.addEventListener("load", () => {

setTimeout(() => {

document.getElementById("splash-screen").style.opacity = "0";

setTimeout(() => {

document.getElementById("splash-screen").style.display = "none";

document.getElementById("main-content").style.display = "block";

}, 1000);

}, 3200);

});

</script>

</body>
</html>
    ''', audios=audios)


# =========================
# REGISTER
# =========================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        phone = request.form['phone']
        password = generate_password_hash(request.form['password'])

        conn = get_db()

        try:
            conn.execute(
                "INSERT INTO users (username,email,phone,password_hash) VALUES (?,?,?,?)",
                (username, email, phone, password)
            )
            conn.commit()
            flash("Registration successful")
            return redirect('/login')
        except:
            flash("Username already exists")

        conn.close()

    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
<title>Register | BIEZ KAVIRU MUSIC STORE</title>

<meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>

*{
margin:0;
padding:0;
box-sizing:border-box;
font-family:Arial;
}

body{
min-height:100vh;
display:flex;
justify-content:center;
align-items:center;

background:
linear-gradient(rgba(0,0,0,0.75),rgba(0,0,0,0.85)),
url('/static/backgrounds/login_bg.jpg');

background-size:cover;
background-position:center;
background-repeat:no-repeat;
background-attachment:fixed;

color:white;
padding:20px;
}

.register-box{
width:100%;
max-width:650px;

padding:50px 35px;

background:rgba(20,20,20,0.85);
backdrop-filter:blur(14px);

border-radius:25px;

border:1px solid rgba(0,255,204,0.25);

box-shadow:
0 0 30px rgba(0,255,204,0.12),
0 0 80px rgba(0,0,0,0.7);

text-align:center;
}

.logo{
font-size:42px;
font-weight:900;
color:#00ffcc;
letter-spacing:3px;
margin-bottom:10px;

text-shadow:
0 0 10px rgba(0,255,204,0.6),
0 0 25px rgba(0,255,204,0.4);
}

.subtitle{
color:#ddd;
margin-bottom:35px;
font-size:16px;
}

input{
width:100%;
padding:18px;

margin-bottom:15px;

border:none;
outline:none;

border-radius:12px;

background:#111;
color:white;

font-size:16px;

border:1px solid rgba(255,255,255,0.1);

transition:0.3s;
}

input:focus{
border:1px solid #00ffcc;
box-shadow:0 0 10px rgba(0,255,204,0.35);
}

button{
width:100%;
padding:18px;

border:none;
border-radius:12px;

background:linear-gradient(45deg,#00ffcc,#00ccff);

color:black;
font-weight:bold;
font-size:18px;

cursor:pointer;
transition:0.3s;

box-shadow:0 0 15px rgba(0,255,204,0.25);
}

button:hover{
transform:scale(1.03);
box-shadow:0 0 25px rgba(0,255,204,0.5);
}

.footer{
margin-top:20px;
font-size:13px;
color:#888;
}

a{
color:#00ffcc;
text-decoration:none;
}

</style>
</head>

<body>

<div class="register-box">

<div class="logo">BIEZ AUDIO</div>

<div class="subtitle">
Create your free account
</div>

<form method="POST">

<input name="username" placeholder="Username" required>

<input name="email" placeholder="Email" required>

<input name="phone" placeholder="Phone (2547XXXXXXX)" required>

<input type="password" name="password" placeholder="Password" required>

<button type="submit">CREATE ACCOUNT</button>

</form>

<div class="footer">
Already have an account? <a href="/login">Login</a>
</div>

</div>

</body>
</html>
''')


# =========================
# LOGIN
# =========================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE username=?",
            (username,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect('/dashboard')

        flash("Invalid credentials")

    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
<title>User Login | BIEZ KAVIRU MUSIC STORE</title>

<meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>

*{
margin:0;
padding:0;
box-sizing:border-box;
font-family:Arial;
}

body{
min-height:100vh;
display:flex;
justify-content:center;
align-items:center;

background:
linear-gradient(rgba(0,0,0,0.75),rgba(0,0,0,0.85)),
url('/static/backgrounds/login_bg.jpg');

background-size:cover;
background-position:center;
background-repeat:no-repeat;
background-attachment:fixed;

color:white;
padding:20px;
}

.login-box{
width:100%;
max-width:650px;

padding:50px 35px;

background:rgba(20,20,20,0.85);
backdrop-filter:blur(14px);

border-radius:25px;

border:1px solid rgba(0,255,204,0.25);

box-shadow:
0 0 30px rgba(0,255,204,0.12),
0 0 80px rgba(0,0,0,0.7);

text-align:center;
}

.logo{
font-size:42px;
font-weight:900;
color:#00ffcc;
letter-spacing:3px;
margin-bottom:10px;

text-shadow:
0 0 10px rgba(0,255,204,0.6),
0 0 25px rgba(0,255,204,0.4);
}

.subtitle{
color:#ddd;
margin-bottom:35px;
font-size:16px;
}

input{
width:100%;
padding:18px;

margin-bottom:15px;

border:none;
outline:none;

border-radius:12px;

background:#111;
color:white;

font-size:16px;

border:1px solid rgba(255,255,255,0.1);

transition:0.3s;
}

input:focus{
border:1px solid #00ffcc;
box-shadow:0 0 10px rgba(0,255,204,0.35);
}

button{
width:100%;
padding:18px;

border:none;
border-radius:12px;

background:linear-gradient(45deg,#00ffcc,#00ccff);

color:black;
font-weight:bold;
font-size:18px;

cursor:pointer;
transition:0.3s;

box-shadow:0 0 15px rgba(0,255,204,0.25);
}

button:hover{
transform:scale(1.03);
box-shadow:0 0 25px rgba(0,255,204,0.5);
}

.footer{
margin-top:20px;
font-size:13px;
color:#888;
}

a{
color:#00ffcc;
text-decoration:none;
}

</style>
</head>

<body>

<div class="login-box">

<div class="logo">BIEZ AUDIO</div>

<div class="subtitle">
Secure User Access Portal
</div>

<form method="POST">

<input name="username" placeholder="Username" required>

<input type="password" name="password" placeholder="Password" required>

<button type="submit">LOGIN</button>

</form>

<div class="footer">
Don't have an account? <a href="/register">Register</a>
</div>

</div>

</body>
</html>
''')


# =========================
# LOGOUT
# =========================
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


# =========================
# DASHBOARD
# =========================
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db()

    purchases = conn.execute('''
        SELECT purchases.*, audios.title
        FROM purchases
        JOIN audios ON purchases.audio_id = audios.id
        WHERE purchases.user_id=?
    ''', (session['user_id'],)).fetchall()

    conn.close()

    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>
body{
margin:0;
font-family:Arial;
color:white;
background:url('/static/backgrounds/main_bg.jpg');
background-size:cover;
background-position:center;
background-attachment:fixed;
}

.container{
max-width:1100px;
margin:auto;
padding:30px;
}

.header{
display:flex;
justify-content:space-between;
align-items:center;
padding:20px;
background:rgba(0,0,0,0.5);
backdrop-filter:blur(12px);
border-bottom:1px solid rgba(0,255,204,0.2);
border-radius:15px;
margin-bottom:25px;
}

.header h1{
color:#00ffcc;
}

.card{
background:rgba(0,0,0,0.55);
backdrop-filter:blur(12px);
border:1px solid rgba(0,255,204,0.15);
border-radius:18px;
padding:20px;
margin-bottom:15px;
transition:0.3s;
}

.card:hover{
transform:translateY(-5px);
}

.btn{
display:inline-block;
padding:10px 16px;
background:linear-gradient(45deg,#00ffcc,#00ccff);
color:black;
border-radius:12px;
text-decoration:none;
font-weight:bold;
margin-right:8px;
}

.section-title{
color:#00ffcc;
font-size:24px;
margin:20px 0 10px;
}
</style>
</head>

<body>

<div class="container">

<div class="header">
<h1>Welcome {{ session['username'] }}</h1>
<a class="btn" href="/logout">Logout</a>
</div>

<div class="section-title">Your Purchases</div>

{% for item in purchases %}
<div class="card">
    <h2>{{ item['title'] }}</h2>
    <p>Downloads Remaining: {{ item['downloads_remaining'] }}</p>

    <a class="btn" href="/stream/{{ item['audio_id'] }}">Stream</a>
    <a class="btn" href="/download/{{ item['audio_id'] }}">Download</a>
</div>
{% endfor %}

</div>

</body>
</html>
''', purchases=purchases)


# =========================
# AUDIO DETAILS
# =========================
@app.route('/audio/<int:audio_id>')
def audio_details(audio_id):
    conn = get_db()
    audio = conn.execute("SELECT * FROM audios WHERE id=?", (audio_id,)).fetchone()
    conn.close()

    if not audio:
        abort(404)

    paid = False

    if 'user_id' in session:
        paid = user_paid(session['user_id'], audio_id)

    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>

body{
margin:0;
padding:40px;
font-family:Arial;
color:white;
background:url('/static/backgrounds/login_bg.jpg');
background-size:cover;
background-position:center;
background-attachment:fixed;
}

/* MAIN CARD */
.audio-container{
max-width:700px;
margin:auto;
background:rgba(0,0,0,0.55);
backdrop-filter:blur(12px);
border:1px solid rgba(0,255,204,0.2);
border-radius:20px;
padding:25px;
box-shadow:0 0 25px rgba(0,255,204,0.12);
}

/* IMAGE */
.audio-container img{
width:100%;
max-width:320px;
border-radius:15px;
border:1px solid rgba(0,255,204,0.2);
}

/* TEXT */
h1{
color:#fff;
margin-top:15px;
}

p{
color:#ccc;
}

/* LOCK BOX */
.lock-box{
margin-top:20px;
padding:20px;
border-radius:16px;
border:1px solid rgba(0,255,204,0.25);
background:rgba(0,0,0,0.4);
box-shadow:0 0 20px rgba(0,255,204,0.12);
}

/* TITLE (UNCHANGED TEXT) */
.lock-box h3{
color:#00ffcc;
margin-bottom:12px;
text-shadow:0 0 10px rgba(0,255,204,0.4);
}

/* INPUT */
.lock-box input{
width:100%;
padding:14px;
margin-bottom:12px;
border-radius:10px;
border:1px solid rgba(0,255,204,0.25);
background:#111;
color:white;
font-size:15px;
outline:none;
}

/* BUTTON */
.lock-box button{
width:100%;
padding:14px;
border:none;
border-radius:12px;
background:linear-gradient(45deg,#00ffcc,#00ccff);
color:black;
font-weight:bold;
cursor:pointer;
box-shadow:0 0 18px rgba(0,255,204,0.35);
transition:0.3s;
}

.lock-box button:hover{
transform:scale(1.03);
}

/* FIX: ensure links are clickable and not blocked */
.action-links{
margin-top:20px;
display:flex;
flex-direction:column;
gap:12px;
}

.action-links a{
display:inline-block;
padding:12px 16px;
border-radius:12px;
background:rgba(0,255,204,0.12);
border:1px solid rgba(0,255,204,0.25);
color:#00ffcc;
text-decoration:none;
font-weight:bold;
text-align:center;
}

.action-links a:hover{
background:rgba(0,255,204,0.2);
}

</style>
</head>

<body>

<div class="audio-container">

    <img src="/{{ audio['cover_image'] }}">

    <h1>{{ audio['title'] }}</h1>

    <p>Genre: {{ audio['genre'] }}</p>
    <p>Price: KES {{ audio['price'] }}</p>

    {% if paid %}

        <div class="action-links">
            <a href="/stream/{{ audio['id'] }}">Listen Now</a>
            <a href="/download/{{ audio['id'] }}">Download</a>
        </div>

    {% else %}

        <div class="lock-box">

            <h3>Locked Premium Audio</h3>

            <form method="POST" action="/pay/{{ audio['id'] }}">

                <input name="phone"
                       placeholder="2547XXXXXXXX"
                       required>

                <button type="submit">
                    Pay with M-Pesa
                </button>

            </form>

        </div>

    {% endif %}

</div>

</body>
</html>
''', audio=audio, paid=paid)


# =========================
# MPESA PAYMENT SIMULATION
# =========================
@app.route('/pay/<int:audio_id>', methods=['POST'])
def pay(audio_id):
    if 'user_id' not in session:
        return redirect('/login')

    phone = request.form['phone']

    conn = get_db()
    audio = conn.execute("SELECT * FROM audios WHERE id=?", (audio_id,)).fetchone()

    receipt = "BIEZ" + secrets.token_hex(4).upper()

    conn.execute('''
    INSERT INTO purchases (
        user_id,
        audio_id,
        paid,
        amount,
        receipt_number,
        downloads_remaining,
        purchase_date
    ) VALUES (?,?,?,?,?,?,?)
    ''', (
        session['user_id'],
        audio_id,
        1,
        audio['price'],
        receipt,
        1,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.execute('''
    INSERT INTO payment_callbacks (
        mpesa_receipt,
        phone,
        amount,
        status,
        raw_callback_json
    ) VALUES (?,?,?,?,?)
    ''', (
        receipt,
        phone,
        audio['price'],
        "SUCCESS",
        json.dumps({"simulated": True})
    ))

    conn.commit()
    conn.close()

    flash("Payment successful. Audio unlocked.")

    return redirect(f'/audio/{audio_id}')


# =========================
# STREAM PROTECTED AUDIO
# =========================
@app.route('/stream/<int:audio_id>')
def stream_audio(audio_id):
    if 'user_id' not in session:
        return "Access Denied"

    purchase = user_paid(session['user_id'], audio_id)

    if not purchase:
        return "Access Denied"

    conn = get_db()
    audio = conn.execute("SELECT * FROM audios WHERE id=?", (audio_id,)).fetchone()
    conn.close()

    file_path = os.path.join(UPLOAD_FOLDER, audio['filename'])

    if not os.path.exists(file_path):
        return "Audio file missing"

    return send_file(file_path)


# =========================
# DOWNLOAD PROTECTED AUDIO
# =========================
@app.route('/download/<int:audio_id>')
def download_audio(audio_id):
    if 'user_id' not in session:
        return "Access Denied"

    conn = get_db()

    purchase = conn.execute(
        "SELECT * FROM purchases WHERE user_id=? AND audio_id=? AND paid=1",
        (session['user_id'], audio_id)
    ).fetchone()

    if not purchase:
        conn.close()
        return "Access Denied"

    if purchase['downloads_remaining'] <= 0:
        conn.close()
        return "Download limit reached"

    audio = conn.execute("SELECT * FROM audios WHERE id=?", (audio_id,)).fetchone()

    conn.execute(
        "UPDATE purchases SET downloads_remaining = downloads_remaining - 1 WHERE id=?",
        (purchase['id'],)
    )

    conn.commit()
    conn.close()

    file_path = os.path.join(UPLOAD_FOLDER, audio['filename'])

    return send_file(file_path, as_attachment=True)


# =========================
# ADMIN LOGIN
# =========================
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect('/admin/dashboard')

    return render_template_string('''

<!DOCTYPE html>
<html>
<head>
<title>Admin Login | BIEZ KAVIRU MUSIC STORE</title>

<meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>

*{
margin:0;
padding:0;
box-sizing:border-box;
}

body{
min-height:100vh;
display:flex;
justify-content:center;
align-items:center;

background:
linear-gradient(rgba(0,0,0,0.75),rgba(0,0,0,0.75)),
url('/static/backgrounds/login_bg.jpg');

background-size:cover;
background-position:center;
background-repeat:no-repeat;
background-attachment:fixed;

font-family:Arial,sans-serif;
padding:20px;
overflow-x:hidden;
}

.login-box{
width:100%;
max-width:650px;
padding:50px 35px;
background:rgba(20,20,20,0.85);
backdrop-filter:blur(14px);
border-radius:25px;
border:1px solid rgba(0,255,204,0.25);
box-shadow:0 0 30px rgba(0,255,204,0.12),
0 0 80px rgba(0,0,0,0.7);
text-align:center;
margin:auto;
}

.subtitle{
color:#ddd;
margin-bottom:25px;
font-size:16px;
}

.form-container form{
display:flex;
flex-direction:column;
gap:18px;
}

input{
width:100%;
padding:18px;
border:none;
outline:none;
border-radius:12px;
background:#111;
color:white;
font-size:16px;
border:1px solid rgba(255,255,255,0.1);
}

input::placeholder{
font-size:16px;
color:rgba(255,255,255,0.75);
}

button{
width:100%;
padding:18px;
border:none;
border-radius:12px;
background:linear-gradient(45deg,#00ffcc,#00ccff);
color:black;
font-weight:bold;
font-size:18px;
cursor:pointer;
}

form{
display:flex;
flex-direction:column;
gap:18px;
}

.logo{
font-size:58px;
font-weight:900;
color:#00ff99;
margin-bottom:18px;
letter-spacing:4px;

text-shadow:
0 0 10px rgba(0,255,153,0.7),
0 0 25px rgba(0,255,153,0.5),
0 0 45px rgba(0,255,153,0.35);
}

.subtitle{
color:#f1f1f1;
font-size:20px;
font-weight:500;
margin-bottom:40px;
line-height:1.8;
letter-spacing:1px;
}}

input{
width:100%;
padding:30px 22px;   /* ↑ increases height */
margin-bottom:18px;

border:none;
outline:none;
border-radius:14px;

background:#111;
color:white;

font-size:22px;
font-weight:600;
letter-spacing:0.5px;

line-height:1.6;  /* helps vertical breathing space */
}

input::placeholder{
font-size:22px;
color:rgba(255,255,255,0.95);
font-weight:700;
opacity:1;

/* key fix for thin look */
letter-spacing:0.5px;
-webkit-font-smoothing:antialiased;
-moz-osx-font-smoothing:grayscale;
}

input:focus{
border:1px solid #00ff99;

box-shadow:0 0 12px rgba(0,255,153,0.35);
}

input:focus{
border:1px solid #00ff99;

box-shadow:
0 0 10px rgba(0,255,153,0.35);
}

button{

width:100%;

padding:24px;

border:none;

border-radius:14px;

background:linear-gradient(45deg,#00ff99,#00cc77);

color:black;

font-size:22px;

font-weight:bold;

cursor:pointer;

transition:0.3s;
}

button:hover{

transform:scale(1.03);

box-shadow:
0 0 20px rgba(0,255,153,0.45);
}

.footer-text{

margin-top:25px;

font-size:13px;

color:#888;
}

@media(max-width:500px){

.login-box{
padding:30px 22px;
}

.logo{
font-size:30px;
}

}

</style>
</head>

<body>

<div class="login-box">

<div class="logo">
BIEZ ADMIN
</div>

<div class="subtitle">
Secure Administrator Access Panel<br>
Premium Audio Management System
</div>

<form method="POST">

<input
name="username"
placeholder="Administrator Username"
required
>

<input
type="password"
name="password"
placeholder="Administrator Password"
required
>

<button type="submit">
ACCESS DASHBOARD
</button>

</form>

<div class="footer-text">
BIEZ KAVIRU MUSIC STORE © 2026
</div>

</div>

</body>
</html>
''')


# =========================
# ADMIN DASHBOARD
# =========================
@app.route('/admin/dashboard')
def admin_dashboard():
    if not is_admin():
        return redirect('/admin')

    conn = get_db()

    audios = conn.execute("SELECT * FROM audios ORDER BY id DESC").fetchall()
    users = conn.execute("SELECT COUNT(*) as total FROM users").fetchone()
    purchases = conn.execute("SELECT COUNT(*) as total FROM purchases").fetchone()

    revenue = conn.execute(
        "SELECT SUM(amount) as total FROM purchases WHERE paid=1"
    ).fetchone()

    conn.close()

    return render_template_string('''
<!DOCTYPE html>
<html>
<head>

<title>BIEZ ADMIN DASHBOARD</title>

<meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>

*{
margin:0;
padding:0;
box-sizing:border-box;
}

body{

background:
linear-gradient(rgba(0,0,0,0.82),rgba(0,0,0,0.82)),
url('/static/backgrounds/admin_bg.jpg');

background-size:cover;
background-position:center;
background-repeat:no-repeat;
background-attachment:fixed;

font-family:Arial,sans-serif;

color:white;

overflow-x:hidden;
}

.container{
width:100%;
max-width:1500px;
margin:auto;
padding:35px;
}

.topbar{

display:flex;
justify-content:space-between;
align-items:center;

flex-wrap:wrap;

gap:20px;

margin-bottom:40px;
}

.logo{

font-size:48px;
font-weight:900;
color:#00ff99;

letter-spacing:3px;

text-shadow:
0 0 10px rgba(0,255,153,0.7),
0 0 30px rgba(0,255,153,0.4);
}

.upload-btn{

padding:18px 28px;

background:linear-gradient(45deg,#00ff99,#00cc77);

color:black;

font-size:18px;

font-weight:bold;

text-decoration:none;

border-radius:18px;

transition:0.3s;
}

.upload-btn:hover{

transform:scale(1.05);

box-shadow:
0 0 25px rgba(0,255,153,0.4);
}

.stats-grid{

display:grid;

grid-template-columns:
repeat(auto-fit,minmax(300px,1fr));

gap:25px;

margin-bottom:45px;
}

.stat-card{

background:rgba(20,20,20,0.82);

backdrop-filter:blur(15px);

padding:35px;

border-radius:25px;

border:1px solid rgba(0,255,153,0.18);

box-shadow:
0 0 25px rgba(0,255,153,0.08),
0 0 80px rgba(0,0,0,0.6);

transition:0.3s;
}

.stat-card:hover{

transform:translateY(-6px);

box-shadow:
0 0 30px rgba(0,255,153,0.22);
}

.stat-title{

font-size:18px;

color:#aaaaaa;

margin-bottom:15px;
}

.stat-value{

font-size:42px;

font-weight:bold;

color:#00ff99;
}

.section-title{

font-size:34px;

margin-bottom:30px;

color:#00ff99;

font-weight:900;
}

.audio-grid{

display:grid;

grid-template-columns:
repeat(auto-fit,minmax(320px,1fr));

gap:25px;
}

.audio-card{

background:rgba(18,18,18,0.84);

backdrop-filter:blur(14px);

border-radius:25px;

overflow:hidden;

border:1px solid rgba(0,255,153,0.15);

transition:0.3s;

box-shadow:
0 0 20px rgba(0,0,0,0.45);
}

.audio-card:hover{

transform:translateY(-8px);

box-shadow:
0 0 30px rgba(0,255,153,0.2);
}

.audio-image{

width:100%;
height:250px;
object-fit:cover;
}

.audio-content{
padding:25px;
}

.audio-title{

font-size:26px;

font-weight:bold;

margin-bottom:12px;
}

.audio-price{

font-size:22px;

color:#00ff99;

font-weight:bold;
}

.audio-date{

margin-top:10px;

color:#aaaaaa;

font-size:14px;
}

@media(max-width:768px){

.container{
padding:20px;
}

.logo{
font-size:34px;
}

.section-title{
font-size:28px;
}

.stat-value{
font-size:32px;
}

}

</style>

</head>

<body>

<div class="container">

<div class="topbar">

<div class="logo">
BIEZ ADMIN
</div>

<a class="upload-btn" href="/admin/upload">
UPLOAD AUDIO
</a>

</div>

<div class="stats-grid">

<div class="stat-card">
<div class="stat-title">
TOTAL USERS
</div>

<div class="stat-value">
{{ users['total'] }}
</div>
</div>

<div class="stat-card">
<div class="stat-title">
TOTAL PURCHASES
</div>

<div class="stat-value">
{{ purchases['total'] }}
</div>
</div>

<div class="stat-card">
<div class="stat-title">
TOTAL REVENUE
</div>

<div class="stat-value">
KES {{ revenue['total'] or 0 }}
</div>
</div>

</div>

<div class="section-title">
UPLOADED TRACKS
</div>

<div class="audio-grid">

{% for audio in audios %}

<div class="audio-card">

<img
class="audio-image"
src="/{{ audio['cover_image'] }}"
>

<div class="audio-content">

<div class="audio-title">
{{ audio['title'] }}
</div>

<div class="audio-price">
KES {{ audio['price'] }}
</div>

<div class="audio-date">
{{ audio['genre'] }} • {{ audio['duration'] }}
</div>

</div>

</div>

{% endfor %}

</div>

</div>

</body>
</html>

''', audios=audios, users=users, purchases=purchases, revenue=revenue)


# =========================
# ADMIN UPLOAD
# =========================
@app.route('/admin/upload', methods=['GET', 'POST'])
def upload_audio():
    if not is_admin():
        return redirect('/admin')

    if request.method == 'POST':
        title = request.form['title']
        genre = request.form['genre']
        price = request.form['price']
        duration = request.form['duration']

        audio_file = request.files['audio']
        cover_file = request.files['cover']

        if not allowed_audio(audio_file.filename):
            return "Invalid audio format"

        if not allowed_image(cover_file.filename):
            return "Invalid image format"

        audio_filename = secure_filename(audio_file.filename)
        cover_filename = secure_filename(cover_file.filename)

        audio_path = os.path.join(UPLOAD_FOLDER, audio_filename)
        cover_path = os.path.join(COVER_FOLDER, cover_filename)

        audio_file.save(audio_path)
        cover_file.save(cover_path)

        webp_filename = cover_filename

        conn = get_db()

        conn.execute('''
        INSERT INTO audios (
            title,
            filename,
            cover_image,
            genre,
            price,
            duration,
            upload_date
        ) VALUES (?,?,?,?,?,?,?)
        ''', (
            title,
            audio_filename,
            f"static/covers/{cover_filename}",
            genre,
            price,
            duration,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        conn.commit()
        conn.close()

        return redirect('/admin/dashboard')

    return render_template_string('''
<!DOCTYPE html>
<html>
<head>

<title>Upload Audio | BIEZ ADMIN</title>

<meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>

*{
margin:0;
padding:0;
box-sizing:border-box;
font-family:Arial,sans-serif;
}

body{

min-height:100vh;

background:
linear-gradient(rgba(0,0,0,0.82),rgba(0,0,0,0.82)),
url('/static/backgrounds/admin_bg.jpg');

background-size:cover;
background-position:center;
background-repeat:no-repeat;
background-attachment:fixed;

display:flex;
justify-content:center;
align-items:center;

padding:30px;

color:white;
}

.upload-box{

width:100%;
max-width:750px;

background:rgba(18,18,18,0.82);

backdrop-filter:blur(15px);

border-radius:28px;

padding:45px;

border:1px solid rgba(0,255,153,0.2);

box-shadow:
0 0 30px rgba(0,255,153,0.12),
0 0 90px rgba(0,0,0,0.65);
}

.logo{

font-size:42px;
font-weight:900;

color:#00ff99;

margin-bottom:12px;

text-align:center;

letter-spacing:3px;

text-shadow:
0 0 10px rgba(0,255,153,0.7),
0 0 30px rgba(0,255,153,0.35);
}

.subtitle{

text-align:center;

color:#cccccc;

margin-bottom:35px;

font-size:16px;
}

form{
display:flex;
flex-direction:column;
gap:18px;
}

input{

width:100%;

padding:18px;

border:none;
outline:none;

border-radius:14px;

background:#111;

color:white;

font-size:17px;

border:1px solid rgba(255,255,255,0.08);

transition:0.3s;
}

input:focus{

border:1px solid #00ff99;

box-shadow:
0 0 15px rgba(0,255,153,0.3);
}

input::placeholder{
color:rgba(255,255,255,0.7);
}

label{

font-size:15px;

color:#00ff99;

margin-bottom:-8px;
}

button{

width:100%;

padding:20px;

border:none;

border-radius:15px;

background:linear-gradient(45deg,#00ff99,#00cc77);

color:black;

font-size:20px;

font-weight:bold;

cursor:pointer;

transition:0.3s;
}

button:hover{

transform:scale(1.02);

box-shadow:
0 0 25px rgba(0,255,153,0.35);
}

</style>

</head>

<body>

<div class="upload-box">

<div class="logo">
BIEZ ADMIN
</div>

<div class="subtitle">
Upload Premium Audio Content
</div>

<form method="POST" enctype="multipart/form-data">

<input name="title" placeholder="Audio Title" required>

<input name="genre" placeholder="Genre" required>

<input name="duration" placeholder="Duration e.g 3:45" required>

<input name="price" placeholder="Price (KES)" required>

<label>Upload Audio File</label>
<input type="file" name="audio" required>

<label>Upload Cover Image</label>
<input type="file" name="cover" required>

<button type="submit">
UPLOAD AUDIO
</button>

</form>

</div>

</body>
</html>
''')


# =========================
# ROBOTS
# =========================
@app.route('/robots.txt')
def robots():
    return """
User-agent: *
Allow: /
Sitemap: https://yourdomain.com/sitemap.xml
""", 200, {'Content-Type': 'text/plain'}


# =========================
# SITEMAP
# =========================
@app.route('/sitemap.xml')
def sitemap():
    conn = get_db()
    audios = conn.execute("SELECT * FROM audios").fetchall()
    conn.close()

    xml = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
'''

    xml += '<url><loc>http://127.0.0.1:5000/</loc></url>'

    for audio in audios:
        xml += f'<url><loc>http://127.0.0.1:5000/audio/{audio["id"]}</loc></url>'

    xml += '</urlset>'

    return xml, 200, {'Content-Type': 'application/xml'}


# =========================
# MOCK DARAJA CALLBACK
# =========================
@app.route('/mpesa/callback', methods=['POST'])
def mpesa_callback():
    data = request.json

    conn = get_db()

    conn.execute('''
    INSERT INTO payment_callbacks (
        mpesa_receipt,
        phone,
        amount,
        status,
        raw_callback_json
    ) VALUES (?,?,?,?,?)
    ''', (
        data.get('receipt', ''),
        data.get('phone', ''),
        data.get('amount', 0),
        'SUCCESS',
        json.dumps(data)
    ))

    conn.commit()
    conn.close()

    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"})


# =========================
# RUN
# =========================
if __name__ == '__main__':
    app.run(debug=True)

