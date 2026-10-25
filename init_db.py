
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
    section TEXT NOT NULL,
    source TEXT DEFAULT 'Manual Entry'
)
""")

# Add source to an existing database if it is missing
cursor.execute("PRAGMA table_info(students)")
columns = [column[1] for column in cursor.fetchall()]

if "source" not in columns:
    cursor.execute("""
        ALTER TABLE students
        ADD COLUMN source TEXT DEFAULT 'Manual Entry'
    """)

# Reset sample records only when this script is run
cursor.execute("DELETE FROM students")

students = [
    ("2026-00123", "jade casas", "BSIT", 1, "A", "Manual Entry"),
    ("2026-00124", "Mary debaja", "BSIT", 1, "A", "Manual Entry"),
    ("2026-00125", "hemar abian", "BSIT", 2, "B", "Partner API"),
    ("2026-00126", "raveen celo", "BSCS", 2, "A", "Manual Entry"),
    ("2026-00127", "lorenzo colasisang", "BSIT", 3, "B", "Manual Entry")
]

cursor.executemany("""
INSERT INTO students
(student_id, name, program, year, section, source)
VALUES (?, ?, ?, ?, ?, ?)
""", students)

conn.commit()
conn.close()

print("Database created successfully with five student records.")
