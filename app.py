
import os
import sqlite3
import requests

from flask import Flask, jsonify, request, render_template

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "students.db")

# Hmar's API endpoints
PARTNER_READ_URL = "https://hemarpaulabian.onrender.com/students"
PARTNER_POST_URL = "https://hemarpaulabian.onrender.com/api/students"

REQUIRED_FIELDS = [
    "student_id",
    "name",
    "program",
    "year",
    "section"
]


# ---------------- DATABASE ----------------

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def student_dict(row):
    return dict(row) if row else None


def validate_student(data):
    if not isinstance(data, dict):
        return "JSON object is required."

    for field in REQUIRED_FIELDS:
        if field not in data or data[field] is None:
            return f"Missing required field: {field}"

        if str(data[field]).strip() == "":
            return f"{field} cannot be empty."

    try:
        year = int(data["year"])
        if year < 1:
            return "Year must be a positive number."
    except (ValueError, TypeError):
        return "Year must be a valid integer."

    return None


def insert_student(data):
    """Insert a student using the existing five-column schema."""
    conn = get_db_connection()

    try:
        cursor = conn.execute(
            """
            INSERT INTO students
            (student_id, name, program, year, section)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(data["student_id"]).strip(),
                str(data["name"]).strip(),
                str(data["program"]).strip(),
                int(data["year"]),
                str(data["section"]).strip()
            )
        )

        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


# ---------------- HOME PAGE ----------------

@app.route("/")
def home():
    return render_template("index.html")


# ---------------- STUDENT CRUD ----------------

# Get all students
@app.route("/students", methods=["GET"])
def get_students():
    conn = get_db_connection()

    try:
        rows = conn.execute(
            "SELECT * FROM students ORDER BY id DESC"
        ).fetchall()

        return jsonify([student_dict(row) for row in rows])
    finally:
        conn.close()


# Get one student by database ID
@app.route("/students/<int:student_id>", methods=["GET"])
def get_student(student_id):
    conn = get_db_connection()

    try:
        row = conn.execute(
            "SELECT * FROM students WHERE id = ?",
            (student_id,)
        ).fetchone()

        if row is None:
            return jsonify({"error": "Student not found"}), 404

        return jsonify(student_dict(row))
    finally:
        conn.close()


# Get students by section
@app.route("/students/section/<string:section>", methods=["GET"])
def get_students_by_section(section):
    conn = get_db_connection()

    try:
        rows = conn.execute(
            "SELECT * FROM students WHERE section = ? ORDER BY id",
            (section,)
        ).fetchall()

        return jsonify([student_dict(row) for row in rows])
    finally:
        conn.close()


# Get all students through the API
@app.route("/api/students", methods=["GET"])
def api_get_students():
    return get_students()


# Create a student or receive a record from Hmar
@app.route("/api/students", methods=["POST"])
def add_student():
    data = request.get_json(silent=True)

    error = validate_student(data)
    if error:
        return jsonify({"error": error}), 400

    try:
        new_id = insert_student(data)

        return jsonify({
            "message": "Student added successfully",
            "id": new_id,
            "student": data
        }), 201

    except sqlite3.Error:
        app.logger.exception("Could not insert student")
        return jsonify({"error": "Database error"}), 500


# Get, update, or delete one student through the API
@app.route("/api/students/<int:student_id>", methods=["GET", "PUT", "DELETE"])
def manage_student(student_id):
    conn = get_db_connection()

    try:
        row = conn.execute(
            "SELECT * FROM students WHERE id = ?",
            (student_id,)
        ).fetchone()

        if row is None:
            return jsonify({"error": "Student not found"}), 404

        if request.method == "GET":
            return jsonify(student_dict(row))

        if request.method == "PUT":
            data = request.get_json(silent=True)

            error = validate_student(data)
            if error:
                return jsonify({"error": error}), 400

            conn.execute(
                """
                UPDATE students
                SET student_id = ?, name = ?, program = ?,
                    year = ?, section = ?
                WHERE id = ?
                """,
                (
                    str(data["student_id"]).strip(),
                    str(data["name"]).strip(),
                    str(data["program"]).strip(),
                    int(data["year"]),
                    str(data["section"]).strip(),
                    student_id
                )
            )
            conn.commit()

            return jsonify({
                "message": "Student updated successfully",
                "id": student_id
            })

        conn.execute(
            "DELETE FROM students WHERE id = ?",
            (student_id,)
        )
        conn.commit()

        return jsonify({"message": "Student deleted successfully"})

    except sqlite3.Error:
        app.logger.exception("Database operation failed")
        return jsonify({"error": "Database error"}), 500
    finally:
        conn.close()


# ---------------- LAB 9: READ PARTNER RECORDS ----------------

@app.route("/partner-records", methods=["GET"])
def partner_records():
    try:
        response = requests.get(PARTNER_READ_URL, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Accept either a list or a {"students": [...]} response.
        if isinstance(data, dict) and isinstance(data.get("students"), list):
            data = data["students"]

        if not isinstance(data, list):
            return jsonify({
                "error": "Partner API did not return a student list."
            }), 502

        return jsonify(data)

    except (requests.RequestException, ValueError):
        app.logger.exception("Could not retrieve partner records")
        return jsonify({
            "error": "Unable to retrieve Hmar's records. Try again later."
        }), 502


# ---------------- LAB 9: IMPORT PARTNER RECORD ----------------

@app.route("/import-student", methods=["POST"])
def import_student():
    data = request.get_json(silent=True)

    error = validate_student(data)
    if error:
        return jsonify({"error": error}), 400

    try:
        new_id = insert_student(data)

        return jsonify({
            "message": "Partner record imported successfully",
            "id": new_id,
            "student": data
        }), 201

    except sqlite3.Error:
        app.logger.exception("Could not import partner record")
        return jsonify({"error": "Database error"}), 500


# ---------------- LAB 9: SEND RECORD TO PARTNER ----------------

@app.route("/send-to-partner", methods=["POST"])
def send_to_partner():
    request_data = request.get_json(silent=True) or {}
    local_id = request_data.get("id")

    if local_id is None:
        return jsonify({
            "error": "Provide the local student database ID in JSON."
        }), 400

    try:
        local_id = int(local_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Student ID must be an integer."}), 400

    conn = get_db_connection()

    try:
        row = conn.execute(
            "SELECT * FROM students WHERE id = ?",
            (local_id,)
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return jsonify({"error": "Student not found"}), 404

    student = student_dict(row)

    # Send only the fields expected by the partner API.
    record = {
        field: student[field]
        for field in REQUIRED_FIELDS
    }

    try:
        response = requests.post(
            PARTNER_POST_URL,
            json=record,
            timeout=30
        )

        try:
            partner_response = response.json()
        except ValueError:
            partner_response = response.text[:1000]

        if not response.ok:
            return jsonify({
                "error": "Partner API rejected the record.",
                "partner_status": response.status_code,
                "partner_response": partner_response
            }), 502

        return jsonify({
            "message": "Student record sent to Hmar successfully.",
            "partner_status": response.status_code,
            "partner_response": partner_response
        }), 200

    except requests.RequestException:
        app.logger.exception("Could not send record to partner")
        return jsonify({
            "error": "Could not connect to Hmar's API. Try again later."
        }), 502


# ---------------- RUN APPLICATION ----------------

if __name__ == "__main__":
    app.run(debug=True)

