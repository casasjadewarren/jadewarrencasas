
import os
import sqlite3
import requests

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "students.db")

# Partner API URLs
PARTNER_READ_URL = "https://hemarpaulabian.onrender.com/students"
PARTNER_POST_URL = "https://hemarpaulabian.onrender.com/api/students"


# ---------------- DATABASE ----------------

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def student_dict(row):
    return dict(row) if row else None


def init_db():
    """Create the table if it does not already exist."""
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            name TEXT NOT NULL,
            program TEXT NOT NULL,
            year INTEGER NOT NULL,
            section TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def validate_student(data):
    if not isinstance(data, dict):
        return None, "Request must contain a JSON object."

    student_id = str(data.get("student_id", "")).strip()
    name = str(data.get("name", data.get("student_name", ""))).strip()
    program = str(data.get("program", data.get("course", "BSIT"))).strip()
    section = str(data.get("section", "")).strip()

    try:
        year = int(data.get("year", data.get("year_level", 3)))
    except (TypeError, ValueError):
        return None, "Year must be a valid number."

    if not student_id or not name or not section:
        return None, "Student ID, name, and section are required."

    if not program:
        program = "BSIT"

    return {
        "student_id": student_id,
        "name": name,
        "program": program,
        "year": year,
        "section": section
    }, None


def insert_student(data):
    student, error = validate_student(data)

    if error:
        return None, error

    conn = get_db_connection()
    cursor = conn.execute("""
        INSERT INTO students
        (student_id, name, program, year, section)
        VALUES (?, ?, ?, ?, ?)
    """, (
        student["student_id"],
        student["name"],
        student["program"],
        student["year"],
        student["section"]
    ))

    conn.commit()
    new_id = cursor.lastrowid
    conn.close()

    student["id"] = new_id
    return student, None


# ---------------- WEB PAGE ----------------

@app.route("/")
def index():
    return render_template("index.html")


# ---------------- STUDENT CRUD API ----------------

@app.route("/students", methods=["GET"])
def get_students():
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM students ORDER BY id DESC"
    ).fetchall()
    conn.close()

    return jsonify([dict(row) for row in rows])


@app.route("/students/<int:student_id>", methods=["GET"])
def get_student(student_id):
    conn = get_db_connection()
    row = conn.execute(
        "SELECT * FROM students WHERE id = ?",
        (student_id,)
    ).fetchone()
    conn.close()

    if row is None:
        return jsonify({"success": False, "message": "Student not found."}), 404

    return jsonify(dict(row))


@app.route("/students/section/<string:section>", methods=["GET"])
def get_students_by_section(section):
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM students WHERE section = ? ORDER BY name",
        (section,)
    ).fetchall()
    conn.close()

    return jsonify([dict(row) for row in rows])


@app.route("/api/students", methods=["GET", "POST"])
def students_api():
    if request.method == "GET":
        return get_students()

    data = request.get_json(silent=True)
    student, error = insert_student(data or {})

    if error:
        return jsonify({"success": False, "message": error}), 400

    return jsonify({
        "success": True,
        "message": "Student created successfully.",
        "student": student
    }), 201


@app.route("/api/students/<int:student_id>", methods=["GET", "PUT", "DELETE"])
def student_detail_api(student_id):
    conn = get_db_connection()
    existing = conn.execute(
        "SELECT * FROM students WHERE id = ?",
        (student_id,)
    ).fetchone()

    if existing is None:
        conn.close()
        return jsonify({"success": False, "message": "Student not found."}), 404

    if request.method == "GET":
        result = dict(existing)
        conn.close()
        return jsonify(result)

    if request.method == "DELETE":
        conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "message": "Student deleted successfully."
        })

    data = request.get_json(silent=True)
    student, error = validate_student(data or {})

    if error:
        conn.close()
        return jsonify({"success": False, "message": error}), 400

    conn.execute("""
        UPDATE students
        SET student_id = ?, name = ?, program = ?, year = ?, section = ?
        WHERE id = ?
    """, (
        student["student_id"],
        student["name"],
        student["program"],
        student["year"],
        student["section"],
        student_id
    ))

    conn.commit()
    conn.close()

    student["id"] = student_id

    return jsonify({
        "success": True,
        "message": "Student updated successfully.",
        "student": student
    })


# ---------------- PARTNER API ----------------

@app.route("/partner-records", methods=["GET"])
def partner_records():
    try:
        response = requests.get(PARTNER_READ_URL, timeout=30)
        response.raise_for_status()
        data = response.json()

        if isinstance(data, dict):
            data = data.get("students", [])

        if not isinstance(data, list):
            return jsonify({
                "success": False,
                "message": "Partner API did not return a student list."
            }), 502

        return jsonify({
            "success": True,
            "students": data
        })

    except requests.RequestException as error:
        return jsonify({
            "success": False,
            "message": f"Could not connect to partner API: {error}"
        }), 502

    except ValueError:
        return jsonify({
            "success": False,
            "message": "Partner API returned invalid JSON."
        }), 502


@app.route("/import-student", methods=["POST"])
def import_partner_student():
    data = request.get_json(silent=True) or {}

    student, error = validate_student(data)

    if error:
        return jsonify({"success": False, "message": error}), 400

    try:
        conn = get_db_connection()

        # Prevent importing the same student ID more than once.
        existing = conn.execute(
            "SELECT id FROM students WHERE student_id = ?",
            (student["student_id"],)
        ).fetchone()

        if existing:
            conn.close()
            return jsonify({
                "success": False,
                "message": "This student ID already exists in your database."
            }), 409

        cursor = conn.execute("""
            INSERT INTO students
            (student_id, name, program, year, section)
            VALUES (?, ?, ?, ?, ?)
        """, (
            student["student_id"],
            student["name"],
            student["program"],
            student["year"],
            student["section"]
        ))

        conn.commit()
        student["id"] = cursor.lastrowid
        conn.close()

        return jsonify({
            "success": True,
            "message": f"{student['name']} imported successfully.",
            "student": student
        }), 201

    except sqlite3.Error as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 500


@app.route("/send-to-partner", methods=["POST"])
def send_to_partner():
    data = request.get_json(silent=True) or {}
    local_id = data.get("id")

    try:
        local_id = int(local_id)
    except (TypeError, ValueError):
        return jsonify({
            "success": False,
            "message": "A valid local student database ID is required."
        }), 400

    conn = get_db_connection()
    row = conn.execute(
        "SELECT * FROM students WHERE id = ?",
        (local_id,)
    ).fetchone()
    conn.close()

    if row is None:
        return jsonify({
            "success": False,
            "message": "Student not found in your database."
        }), 404

    student = dict(row)

    payload = {
        "student_id": student["student_id"],
        "name": student["name"],
        "program": student["program"],
        "year": student["year"],
        "section": student["section"]
    }

    try:
        response = requests.post(
            PARTNER_POST_URL,
            json=payload,
            timeout=30
        )

        if not response.ok:
            return jsonify({
                "success": False,
                "message": (
                    f"Partner API rejected the record "
                    f"(HTTP {response.status_code})."
                ),
                "partner_response": response.text[:500]
            }), 502

        return jsonify({
            "success": True,
            "message": f"{student['name']} sent to partner successfully."
        })

    except requests.RequestException as error:
        return jsonify({
            "success": False,
            "message": f"Could not send record to partner: {error}"
        }), 502


# ---------------- START APPLICATION ----------------

init_db()

if __name__ == "__main__":
    app.run(debug=True)
