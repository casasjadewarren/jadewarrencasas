
import os
import sqlite3
import requests

from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "students.db")

PARTNER_URL = "https://hemarpaulabian.onrender.com/students"
PARTNER_POST_URL = "https://hemarpaulabian.onrender.com/api/students"


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()

    conn.execute("""
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

    columns = [
        column["name"]
        for column in conn.execute("PRAGMA table_info(students)").fetchall()
    ]

    if "source" not in columns:
        conn.execute("""
            ALTER TABLE students
            ADD COLUMN source TEXT DEFAULT 'Manual Entry'
        """)

    conn.commit()
    conn.close()


def student_dict(student):
    return {
        "id": student["id"],
        "student_id": student["student_id"],
        "name": student["name"],
        "program": student["program"],
        "year": student["year"],
        "section": student["section"],
        "source": student["source"] or "Manual Entry"
    }


def validate_student(data):
    student_id = str(data.get("student_id", "")).strip()
    name = str(data.get("name", data.get("student_name", ""))).strip()
    program = str(data.get("program", data.get("course", ""))).strip()
    year = data.get("year", data.get("year_level"))
    section = str(data.get("section", "")).strip()

    if not all([student_id, name, program, year, section]):
        return None, "All student fields are required."

    try:
        year = int(year)
        if year < 1:
            raise ValueError
    except (ValueError, TypeError):
        return None, "Year must be a positive number."

    return {
        "student_id": student_id,
        "name": name,
        "program": program,
        "year": year,
        "section": section
    }, None


def insert_student(data, default_source="Manual Entry"):
    student, error = validate_student(data)

    if error:
        return None, error

    source = str(data.get("source", default_source)).strip() or default_source

    conn = get_db_connection()

    existing = conn.execute(
        "SELECT id FROM students WHERE student_id = ?",
        (student["student_id"],)
    ).fetchone()

    if existing:
        conn.close()
        return None, "Student ID already exists."

    cursor = conn.execute("""
        INSERT INTO students
        (student_id, name, program, year, section, source)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        student["student_id"],
        student["name"],
        student["program"],
        student["year"],
        student["section"],
        source
    ))

    conn.commit()

    saved = conn.execute(
        "SELECT * FROM students WHERE id = ?",
        (cursor.lastrowid,)
    ).fetchone()

    result = student_dict(saved)
    conn.close()

    return result, None


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/students", methods=["GET"])
def get_students():
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM students ORDER BY id DESC"
    ).fetchall()
    conn.close()

    return jsonify([student_dict(row) for row in rows])


@app.route("/students/<int:student_id>", methods=["GET"])
def get_student(student_id):
    conn = get_db_connection()
    row = conn.execute(
        "SELECT * FROM students WHERE id = ?",
        (student_id,)
    ).fetchone()
    conn.close()

    if row is None:
        return jsonify({"error": "Student not found."}), 404

    return jsonify(student_dict(row))


@app.route("/students/section/<string:section>", methods=["GET"])
def get_students_by_section(section):
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM students WHERE section = ? ORDER BY name",
        (section,)
    ).fetchall()
    conn.close()

    return jsonify([student_dict(row) for row in rows])


@app.route("/api/students", methods=["GET", "POST"])
def api_students():
    if request.method == "GET":
        conn = get_db_connection()
        rows = conn.execute(
            "SELECT * FROM students ORDER BY id DESC"
        ).fetchall()
        conn.close()

        return jsonify([student_dict(row) for row in rows])

    data = request.get_json(silent=True) or {}

    # Requests coming directly through this API default to Partner API.
    result, error = insert_student(data, default_source="Partner API")

    if error:
        status = 409 if "already exists" in error else 400
        return jsonify({"error": error}), status

    return jsonify({
        "message": "Student added successfully.",
        "student": result
    }), 201


@app.route("/api/students/<int:student_id>", methods=["GET", "PUT", "DELETE"])
def api_student_detail(student_id):
    conn = get_db_connection()

    existing = conn.execute(
        "SELECT * FROM students WHERE id = ?",
        (student_id,)
    ).fetchone()

    if existing is None:
        conn.close()
        return jsonify({"error": "Student not found."}), 404

    if request.method == "GET":
        result = student_dict(existing)
        conn.close()
        return jsonify(result)

    if request.method == "DELETE":
        conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
        conn.commit()
        conn.close()
        return jsonify({"message": "Student deleted successfully."})

    data = request.get_json(silent=True) or {}
    student, error = validate_student(data)

    if error:
        conn.close()
        return jsonify({"error": error}), 400

    source = str(
        data.get("source", existing["source"] or "Manual Entry")
    ).strip() or "Manual Entry"

    duplicate = conn.execute("""
        SELECT id FROM students
        WHERE student_id = ? AND id != ?
    """, (student["student_id"], student_id)).fetchone()

    if duplicate:
        conn.close()
        return jsonify({"error": "Another student already uses that Student ID."}), 409

    conn.execute("""
        UPDATE students
        SET student_id = ?, name = ?, program = ?,
            year = ?, section = ?, source = ?
        WHERE id = ?
    """, (
        student["student_id"],
        student["name"],
        student["program"],
        student["year"],
        student["section"],
        source,
        student_id
    ))

    conn.commit()

    updated = conn.execute(
        "SELECT * FROM students WHERE id = ?",
        (student_id,)
    ).fetchone()

    result = student_dict(updated)
    conn.close()

    return jsonify({
        "message": "Student updated successfully.",
        "student": result
    })


@app.route("/partner-records", methods=["GET"])
def partner_records():
    try:
        response = requests.get(PARTNER_URL, timeout=20)
        response.raise_for_status()
        data = response.json()

        if isinstance(data, dict):
            records = data.get("students", [])
        elif isinstance(data, list):
            records = data
        else:
            records = []

        return jsonify(records)

    except requests.RequestException as error:
        return jsonify({
            "error": "Could not connect to the partner API.",
            "details": str(error)
        }), 502
    except ValueError:
        return jsonify({"error": "Partner API returned invalid JSON."}), 502


@app.route("/import-student", methods=["POST"])
def import_student():
    data = request.get_json(silent=True) or {}

    # Imported records from the partner always get this source.
    data["source"] = "Partner API"

    result, error = insert_student(data, default_source="Partner API")

    if error:
        status = 409 if "already exists" in error else 400
        return jsonify({"error": error}), status

    return jsonify({
        "message": "Partner student imported successfully.",
        "student": result
    }), 201


@app.route("/send-to-partner", methods=["POST"])
def send_to_partner():
    data = request.get_json(silent=True) or {}
    local_id = data.get("id")

    try:
        local_id = int(local_id)
    except (ValueError, TypeError):
        return jsonify({"error": "A valid local student ID is required."}), 400

    conn = get_db_connection()
    row = conn.execute(
        "SELECT * FROM students WHERE id = ?",
        (local_id,)
    ).fetchone()
    conn.close()

    if row is None:
        return jsonify({"error": "Student not found."}), 404

    payload = {
        "student_id": row["student_id"],
        "name": row["name"],
        "program": row["program"],
        "year": row["year"],
        "section": row["section"]
    }

    try:
        response = requests.post(
            PARTNER_POST_URL,
            json=payload,
            timeout=20
        )

        try:
            partner_data = response.json()
        except ValueError:
            partner_data = {"response": response.text[:500]}

        if not response.ok:
            return jsonify({
                "error": "Partner API rejected the student.",
                "partner_status": response.status_code,
                "partner_response": partner_data
            }), 502

        return jsonify({
            "message": "Student sent to partner successfully.",
            "partner_response": partner_data
        })

    except requests.RequestException as error:
        return jsonify({
            "error": "Could not send the student to the partner API.",
            "details": str(error)
        }), 502


# Add the column safely without deleting existing student records.
init_db()


if __name__ == "__main__":
    app.run(debug=True)
