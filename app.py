import sqlite3
from flask import Flask, jsonify, request, render_template

app = Flask(__name__)

DATABASE = "students.db"


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# Home page
@app.route("/")
def home():
    return render_template("index.html")


# Get all students (existing endpoint)
@app.route("/students")
def get_students():
    conn = get_db_connection()
    students = conn.execute(
        "SELECT * FROM students ORDER BY id"
    ).fetchall()
    conn.close()

    return jsonify([dict(student) for student in students])


# Get one student by database ID (existing endpoint)
@app.route("/students/<int:id>")
def get_student_by_id(id):
    conn = get_db_connection()
    student = conn.execute(
        "SELECT * FROM students WHERE id = ?", (id,)
    ).fetchone()
    conn.close()

    if student is None:
        return jsonify({"error": "Student not found"}), 404

    return jsonify(dict(student))


# Get students by section (existing endpoint)
@app.route("/students/section/<string:section>")
def get_students_by_section(section):
    conn = get_db_connection()
    students = conn.execute(
        "SELECT * FROM students WHERE section = ? ORDER BY id",
        (section,)
    ).fetchall()
    conn.close()

    return jsonify([dict(student) for student in students])


# API: Read all students
@app.route("/api/students", methods=["GET"])
def api_students():
    conn = get_db_connection()
    students = conn.execute(
        "SELECT * FROM students ORDER BY id"
    ).fetchall()
    conn.close()

    return jsonify([dict(student) for student in students])


# API: Create a student
@app.route("/api/students", methods=["POST"])
def add_student():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "JSON data is required"}), 400

    required_fields = [
        "student_id", "name", "program", "year", "section"
    ]

    if any(field not in data for field in required_fields):
        return jsonify({"error": "Missing required student fields"}), 400

    conn = get_db_connection()

    cursor = conn.execute(
        """
        INSERT INTO students
        (student_id, name, program, year, section)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            data["student_id"],
            data["name"],
            data["program"],
            data["year"],
            data["section"]
        )
    )

    conn.commit()
    new_id = cursor.lastrowid
    conn.close()

    return jsonify({
        "message": "Student added",
        "id": new_id
    }), 201


# API: Read one student
@app.route("/api/students/<int:id>", methods=["GET"])
def api_get_student(id):
    conn = get_db_connection()
    student = conn.execute(
        "SELECT * FROM students WHERE id = ?", (id,)
    ).fetchone()
    conn.close()

    if student is None:
        return jsonify({"error": "Student not found"}), 404

    return jsonify(dict(student))


# API: Update a student
@app.route("/api/students/<int:id>", methods=["PUT"])
def update_student(id):
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "JSON data is required"}), 400

    required_fields = [
        "student_id", "name", "program", "year", "section"
    ]

    if any(field not in data for field in required_fields):
        return jsonify({"error": "Missing required student fields"}), 400

    conn = get_db_connection()

    cursor = conn.execute(
        """
        UPDATE students
        SET student_id = ?, name = ?, program = ?,
            year = ?, section = ?
        WHERE id = ?
        """,
        (
            data["student_id"],
            data["name"],
            data["program"],
            data["year"],
            data["section"],
            id
        )
    )

    conn.commit()
    updated = cursor.rowcount
    conn.close()

    if updated == 0:
        return jsonify({"error": "Student not found"}), 404

    return jsonify({"message": "Student updated"})


# API: Delete a student
@app.route("/api/students/<int:id>", methods=["DELETE"])
def delete_student(id):
    conn = get_db_connection()
    cursor = conn.execute(
        "DELETE FROM students WHERE id = ?", (id,)
    )

    conn.commit()
    deleted = cursor.rowcount
    conn.close()

    if deleted == 0:
        return jsonify({"error": "Student not found"}), 404

    return jsonify({"message": "Student deleted"})


if __name__ == "__main__":
    app.run(debug=True)
