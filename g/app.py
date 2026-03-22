from flask import Flask, render_template, request, redirect, session
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "secret"

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # таблица пользователей с аватаркой
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        password TEXT,
        avatar TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY,
        user TEXT,
        text TEXT,
        color TEXT,
        size INTEGER,
        font TEXT,
        image TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS likes (
        id INTEGER PRIMARY KEY,
        post_id INTEGER,
        user TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY,
        post_id INTEGER,
        user TEXT,
        text TEXT
    )""")

    conn.commit()
    conn.close()

init_db()

# --- ГЛАВНАЯ ---
@app.route("/", methods=["GET", "POST"])
def index():
    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    if request.method == "POST":
        text = request.form["text"]
        color = request.form["color"]
        size = request.form["size"]
        font = request.form["font"]

        image = request.files.get("image")
        filename = ""

        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        c.execute("INSERT INTO posts (user, text, color, size, font, image) VALUES (?, ?, ?, ?, ?, ?)",
                  (session["user"], text, color, size, font, filename))
        conn.commit()

    c.execute("SELECT * FROM posts ORDER BY id DESC")
    posts = c.fetchall()

    likes = {}
    user_likes = {}
    comments = {}
    for post in posts:
        c.execute("SELECT COUNT(*) FROM likes WHERE post_id=?", (post[0],))
        likes[post[0]] = c.fetchone()[0]

        c.execute("SELECT 1 FROM likes WHERE post_id=? AND user=?", (post[0], session["user"]))
        user_likes[post[0]] = c.fetchone() is not None

        c.execute("SELECT user, text FROM comments WHERE post_id=?", (post[0],))
        comments[post[0]] = c.fetchall()

    conn.close()
    return render_template("index.html", posts=posts, likes=likes, comments=comments, user_likes=user_likes)

# --- ЛАЙК ---
@app.route("/like/<int:post_id>")
def like(post_id):
    if "user" not in session:
        return redirect("/login")

    user = session["user"]

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT user FROM posts WHERE id=?", (post_id,))
    post_owner = c.fetchone()[0]

    if post_owner == user:
        conn.close()
        return redirect("/")

    c.execute("SELECT * FROM likes WHERE post_id=? AND user=?", (post_id, user))
    already_liked = c.fetchone()

    if already_liked:
        c.execute("DELETE FROM likes WHERE post_id=? AND user=?", (post_id, user))
    else:
        c.execute("INSERT INTO likes (post_id, user) VALUES (?, ?)", (post_id, user))

    conn.commit()
    conn.close()
    return redirect("/")

# --- КОММЕНТАРИЙ ---
@app.route("/comment/<int:post_id>", methods=["POST"])
def comment(post_id):
    if "user" not in session:
        return redirect("/login")

    text = request.form["text"]
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("INSERT INTO comments (post_id, user, text) VALUES (?, ?, ?)",
              (post_id, session["user"], text))
    conn.commit()
    conn.close()
    return redirect("/")

# --- ПРОФИЛЬ ---
@app.route("/profile/<username>", methods=["GET", "POST"])
def profile(username):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    user = c.fetchone()

    c.execute("SELECT * FROM posts WHERE user=? ORDER BY id DESC", (username,))
    posts = c.fetchall()

    # загрузка аватарки
    if request.method == "POST" and "user" in session and session["user"] == username:
        avatar = request.files.get("avatar")
        if avatar and allowed_file(avatar.filename):
            filename = secure_filename(avatar.filename)
            avatar.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            c.execute("UPDATE users SET avatar=? WHERE username=?", (filename, username))
            conn.commit()

    conn.close()
    return render_template("profile.html", user=user, posts=posts)

# --- ЛОГИН ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (user, password))
        result = c.fetchone()
        conn.close()

        if result:
            session["user"] = user
            return redirect("/")

    return render_template("login.html")

# --- РЕГИСТРАЦИЯ ---
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (user, password))
        conn.commit()
        conn.close()
        return redirect("/login")

    return render_template("register.html")

# --- ВЫХОД ---
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/login")

if __name__ == "__main__":
    app.run(debug=True)