import sqlite3
from flask_bcrypt import generate_password_hash

DB_NAME = "quiz.db"

conn = sqlite3.connect(DB_NAME)
c = conn.cursor()

# Borrar tablas si existen
c.execute("DROP TABLE IF EXISTS answers")
c.execute("DROP TABLE IF EXISTS questions")
c.execute("DROP TABLE IF EXISTS rounds")
c.execute("DROP TABLE IF EXISTS users")

# Tabla usuarios
c.execute("""
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    total_points INTEGER NOT NULL DEFAULT 0
)
""")

# Tabla rondas (semana)
c.execute("""
CREATE TABLE rounds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    week_number INTEGER NOT NULL,
    author_user_id INTEGER NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY(author_user_id) REFERENCES users(id)
)
""")

# Tabla preguntas
c.execute("""
CREATE TABLE questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    round_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    correct_answer TEXT NOT NULL,
    FOREIGN KEY(round_id) REFERENCES rounds(id)
)
""")

# Tabla respuestas
c.execute("""
CREATE TABLE answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    answer_text TEXT NOT NULL,
    is_correct INTEGER NOT NULL,
    FOREIGN KEY(question_id) REFERENCES questions(id),
    FOREIGN KEY(user_id) REFERENCES users(id)
)
""")

# Crear 5 usuarios de ejemplo
usernames = ["alice", "bob", "carol", "dave", "eve"]
password = "test"
pw_hash = generate_password_hash(password).decode("utf-8")

for u in usernames:
    c.execute(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
        (u, pw_hash)
    )

conn.commit()
conn.close()

print("Base de datos inicializada con 5 usuarios (contraseña: test).")
