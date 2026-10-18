
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "students.db")

conn = sqlite3.connect(DATABASE)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    name TEXT NOT NULL,
    program TEXT NOT NULL,
    year INTEGER NOT NULL,
    section TEXT NOT NULL
)
""")

# Reset the sample records
cursor.execute("DELETE FROM students")

students = [
    ("2026-00123", "jade casas", "BSIT", 1, "A"),
    ("2026-00124", "Mary debaja", "BSIT", 1, "A"),
    ("2026-00125", "hemar abian", "BSIT", 2, "B"),
    ("2026-00126", "raveen celo", "BSCS", 2, "A"),
    ("2026-00127", "lorenzo colasisang", "BSIT", 3, "B")
]

cursor.executemany("""
INSERT INTO students
(student_id, name, program, year, section)
VALUES (?, ?, ?, ?, ?)
""", students)

conn.commit()
conn.close()

print("Database created successfully with five student records.")
