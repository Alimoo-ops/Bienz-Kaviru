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
DATABASE = os.path.join(BASE_DIR, "bienz_audio_store.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads_protected")
COVER_FOLDER = os.path.join(BASE_DIR, "static", "covers")
ALLOWED_AUDIO = {"mp3", "wav"}
ALLOWED_IMAGES = {"png", "jpg", "jpeg", "webp"}

ADMIN_USERNAME = "KAVIRU"
ADMIN_PASSWORD = "BIENZ2005"

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
<title>BIENZ AUDIO STORE</title>
<meta name="viewport" content="width=device-width, initial-scale=2">
<meta name="description" content="Buy premium audios securely with M-Pesa">
<style>
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
background:#121212;
padding:15px;
display:flex;
justify-content:space-between;
align-items:center;
position:sticky;
top:0;
}
.logo{
font-size:28px;
font-weight:bold;
color:#00ff99;
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
color:white;
margin-left:15px;
text-decoration:none;
}
</style>
</head>
<body>
<header>
<div class="logo">BIENZ AUDIO STORE</div>
<div class="nav">
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
<h2>Premium Audio Marketplace</h2>
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
    <body style="
background:url('/static/backgrounds/login_bg.jpg');
background-size:cover;
background-position:center;
background-attachment:fixed;
background-repeat:no-repeat;
color:white;
font-family:Arial;
padding:40px;
">
    <h1>Register</h1>
    <form method="POST">
    <input name="username" placeholder="Username" required><br><br>
    <input name="email" placeholder="Email" required><br><br>
    <input name="phone" placeholder="Phone" required><br><br>
    <input type="password" name="password" placeholder="Password" required><br><br>
    <button>Register</button>
    </form>
    </body>
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
    <body style="
background:url('/static/backgrounds/login_bg.jpg');
background-size:cover;
background-position:center;
background-attachment:fixed;
background-repeat:no-repeat;
color:white;
font-family:Arial;
padding:40px;
">
    <h1>User Login</h1>
    <form method="POST">
    <input name="username" placeholder="Username" required><br><br>
    <input type="password" name="password" placeholder="Password" required><br><br>
    <button>Login</button>
    </form>
    </body>
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
    <body style="
background:url('/static/backgrounds/admin_bg.jpg');
background-size:cover;
background-position:center;
background-attachment:fixed;
background-repeat:no-repeat;
color:white;
font-family:Arial;
padding:40px;
">
    <h1>Welcome {{ session['username'] }}</h1>

    <h2>Your Purchases</h2>

    {% for item in purchases %}
    <div style="background:#222;padding:20px;margin-bottom:15px;border-radius:10px;">
    <h3>{{ item['title'] }}</h3>
    <p>Downloads Remaining: {{ item['downloads_remaining'] }}</p>

    <a href="/stream/{{ item['audio_id'] }}">Stream</a>
    |
    <a href="/download/{{ item['audio_id'] }}">Download</a>
    </div>
    {% endfor %}
    </body>
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
    <body style="
background:url('/static/backgrounds/login_bg.jpg');
background-size:cover;
background-position:center;
background-attachment:fixed;
background-repeat:no-repeat;
color:white;
font-family:Arial;
padding:40px;
">
    <img src="/{{ audio['cover_image'] }}" width="300">
    <h1>{{ audio['title'] }}</h1>
    <p>Genre: {{ audio['genre'] }}</p>
    <p>Price: KES {{ audio['price'] }}</p>

    {% if paid %}
        <a href="/stream/{{ audio['id'] }}">Listen Now</a><br><br>
        <a href="/download/{{ audio['id'] }}">Download</a>
    {% else %}
        <h3>Locked Premium Audio</h3>
        <form method="POST" action="/pay/{{ audio['id'] }}">
        <input name="phone" placeholder="2547XXXXXXXX" required>
        <button>Pay with M-Pesa</button>
        </form>
    {% endif %}
    </body>
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

    receipt = "BIENZ" + secrets.token_hex(4).upper()

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
    <body style="
background:url('/static/backgrounds/login_bg.jpg');
background-size:cover;
background-position:center;
background-attachment:fixed;
background-repeat:no-repeat;
color:white;
font-family:Arial;
padding:40px;
">
    <h1>Admin Login</h1>
    <form method="POST">
    <input name="username" placeholder="Admin Username"><br><br>
    <input type="password" name="password" placeholder="Admin Password"><br><br>
    <button>Login</button>
    </form>
    </body>
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
    <body style="
background:url('/static/backgrounds/login_bg.jpg');
background-size:cover;
background-position:center;
background-attachment:fixed;
background-repeat:no-repeat;
color:white;
font-family:Arial;
padding:40px;
">
    <h1>Admin Dashboard</h1>

    <h3>Total Users: {{ users['total'] }}</h3>
    <h3>Total Purchases: {{ purchases['total'] }}</h3>
    <h3>Total Revenue: KES {{ revenue['total'] or 0 }}</h3>

    <a href="/admin/upload">Upload Audio</a>

    <hr>

    {% for audio in audios %}
    <div style="background:#222;padding:20px;margin-bottom:20px;border-radius:10px;">
    <h2>{{ audio['title'] }}</h2>
    <p>KES {{ audio['price'] }}</p>
    </div>
    {% endfor %}

    </body>
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
    <body style="
background:url('/static/backgrounds/login_bg.jpg');
background-size:cover;
background-position:center;
background-attachment:fixed;
background-repeat:no-repeat;
color:white;
font-family:Arial;
padding:40px;
">
    <h1>Upload Audio</h1>

    <form method="POST" enctype="multipart/form-data">
    <input name="title" placeholder="Title" required><br><br>
    <input name="genre" placeholder="Genre" required><br><br>
    <input name="duration" placeholder="Duration e.g 3:45" required><br><br>
    <input name="price" placeholder="Price" required><br><br>

    <label>Upload Audio</label><br>
    <input type="file" name="audio" required><br><br>

    <label>Upload Cover</label><br>
    <input type="file" name="cover" required><br><br>

    <button>Upload Audio</button>
    </form>
    </body>
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

