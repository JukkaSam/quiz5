from flask import Flask, render_template, request, redirect, session, url_for
from flask_bcrypt import check_password_hash
import sqlite3

app = Flask(__name__)
app.secret_key = "cambia_esto_por_algo_mas_secreto"

DB_NAME = "quiz.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return user

@app.route("/")
def index():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))
    return redirect(url_for("dashboard"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            return redirect(url_for("dashboard"))
        else:
            return "Login incorrecto"

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
def dashboard():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    conn = get_db()
    # Ronda activa (suponemos solo una activa a la vez)
    round_row = conn.execute("SELECT * FROM rounds WHERE active = 1 ORDER BY id DESC LIMIT 1").fetchone()
    # Ranking
    ranking = conn.execute("SELECT username, total_points FROM users ORDER BY total_points DESC").fetchall()
    conn.close()

    return render_template("dashboard.html", user=user, current_round=round_row, ranking=ranking)

@app.route("/create_round", methods=["GET", "POST"])
def create_round():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    if request.method == "POST":
        week_number = int(request.form["week_number"])
        q1 = request.form["q1"]
        a1 = request.form["a1"]
        q2 = request.form["q2"]
        a2 = request.form["a2"]
        q3 = request.form["q3"]
        a3 = request.form["a3"]

        conn = get_db()
        # Desactivar rondas anteriores si quieres solo una activa
        conn.execute("UPDATE rounds SET active = 0")
        conn.execute(
            "INSERT INTO rounds (week_number, author_user_id, active) VALUES (?, ?, 1)",
            (week_number, user["id"])
        )
        round_id = conn.execute("SELECT last_insert_rowid() as id").fetchone()["id"]

        questions = [(round_id, q1, a1), (round_id, q2, a2), (round_id, q3, a3)]
        conn.executemany(
            "INSERT INTO questions (round_id, text, correct_answer) VALUES (?, ?, ?)",
            questions
        )

        conn.commit()
        conn.close()

        return redirect(url_for("dashboard"))

    return render_template("create_round.html", user=user)

@app.route("/answer_round/<int:round_id>", methods=["GET", "POST"])
def answer_round(round_id):
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    conn = get_db()
    round_row = conn.execute("SELECT * FROM rounds WHERE id = ?", (round_id,)).fetchone()
    questions = conn.execute("SELECT * FROM questions WHERE round_id = ?", (round_id,)).fetchall()

    if request.method == "POST":
        # Comprobar si ya había respondido todas (no dejamos contestar dos veces)
        existing = conn.execute(
            "SELECT COUNT(*) AS c FROM answers WHERE user_id = ? AND question_id IN (SELECT id FROM questions WHERE round_id = ?)",
            (user["id"], round_id)
        ).fetchone()["c"]
        if existing > 0:
            conn.close()
            return "Ya has respondido esta ronda."

        total_correct = 0
        for q in questions:
            ans = request.form.get(f"q{q['id']}")
            is_correct = 1 if ans.strip().lower() == q["correct_answer"].strip().lower() else 0
            if is_correct:
                total_correct += 1
            conn.execute(
                "INSERT INTO answers (question_id, user_id, answer_text, is_correct) VALUES (?, ?, ?, ?)",
                (q["id"], user["id"], ans, is_correct)
            )

        # Actualizar puntos del usuario (1 por acierto, +1 si acierta las 3)
        bonus = 1 if total_correct == len(questions) else 0
        conn.execute(
            "UPDATE users SET total_points = total_points + ? WHERE id = ?",
            (total_correct + bonus, user["id"])
        )

        conn.commit()
        conn.close()

        return redirect(url_for("round_results", round_id=round_id))

    # GET: mostrar formulario de respuestas
    conn.close()
    return render_template("answer_round.html", user=user, round_row=round_row, questions=questions)

@app.route("/round_results/<int:round_id>")
def round_results(round_id):
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    conn = get_db()

    # Comprobar si el usuario ha respondido todas las preguntas de esa ronda
    answered_count = conn.execute("""
        SELECT COUNT(*) AS c FROM answers
        WHERE user_id = ? AND question_id IN (SELECT id FROM questions WHERE round_id = ?)
    """, (user["id"], round_id)).fetchone()["c"]

    total_questions = conn.execute(
        "SELECT COUNT(*) AS c FROM questions WHERE round_id = ?",
        (round_id,)
    ).fetchone()["c"]

    if answered_count < total_questions:
        conn.close()
        return "No puedes ver resultados hasta que contestes todas las preguntas."

    # Ahora sí: mostrar resultados de todos
    # (si quieres, puedes limitarlo a solo estadísticas globales)
    results = conn.execute("""
        SELECT u.username, q.text AS question_text, a.answer_text, a.is_correct
        FROM answers a
        JOIN users u ON a.user_id = u.id
        JOIN questions q ON a.question_id = q.id
        WHERE q.round_id = ?
        ORDER BY u.username, q.id
    """, (round_id,)).fetchall()

    conn.close()

    return render_template("round_results.html", user=user, results=results)
    
if __name__ == "__main__":
    app.run(debug=True)
