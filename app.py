from flask import Flask, render_template, request, jsonify, redirect, session
import sqlite3
import time
import os

# ✅ IMPORTANT for Render (static + templates)
app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = "admin123"


# ✅ DB CONNECTION (WAL MODE)
def get_db():
    conn = sqlite3.connect("database.db", timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


# -------- INIT DB --------
conn = get_db()
c = conn.cursor()

c.execute("CREATE TABLE IF NOT EXISTS faq (id INTEGER PRIMARY KEY AUTOINCREMENT, question TEXT, answer TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS unknown (id INTEGER PRIMARY KEY AUTOINCREMENT, question TEXT)")

conn.commit()
conn.close()


# -------- HELPERS --------
def clean(text):
    return text.lower().strip()


def get_answer(msg):
    msg = clean(msg)

    conn = get_db()
    c = conn.cursor()

    data = c.execute("SELECT question, answer FROM faq").fetchall()
    conn.close()

    for q, a in data:
        if clean(q) in msg or msg in clean(q):
            return a

    return None


# -------- ROUTES --------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    msg = request.json["message"]
    reply = get_answer(msg)

    if not reply:
        conn = get_db()
        c = conn.cursor()

        c.execute("INSERT INTO unknown (question) VALUES (?)", (msg,))
        conn.commit()
        conn.close()

        reply = "I will learn this soon 😊"

    return jsonify({"reply": reply})


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        if request.form["password"] == "admin123":
            session["admin"] = True
            return redirect("/dashboard")
    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if not session.get("admin"):
        return redirect("/admin")

    conn = get_db()
    c = conn.cursor()

    faq = c.execute("SELECT * FROM faq").fetchall()
    unknown = c.execute("SELECT * FROM unknown").fetchall()

    conn.close()

    return render_template("admin.html", faq=faq, unknown=unknown)


@app.route("/add", methods=["POST"])
def add():
    if not session.get("admin"):
        return redirect("/admin")

    q = request.form["question"]
    a = request.form["answer"]

    conn = get_db()
    c = conn.cursor()

    c.execute("INSERT INTO faq (question, answer) VALUES (?,?)", (q, a))
    conn.commit()
    conn.close()

    return redirect("/dashboard")


# ✅ DELETE WITH RETRY (FIX LOCK)
@app.route("/delete/<int:id>")
def delete(id):
    if not session.get("admin"):
        return redirect("/admin")

    for _ in range(3):
        try:
            conn = get_db()
            c = conn.cursor()

            c.execute("DELETE FROM unknown WHERE id=?", (id,))
            conn.commit()
            conn.close()

            break
        except sqlite3.OperationalError:
            time.sleep(0.5)

    return redirect("/dashboard")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ✅ RENDER PORT FIX
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
