import base64
import csv
import io
import os
from datetime import date, datetime
from pathlib import Path

import cv2
import numpy as np
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from flask import Flask, Response, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
FACE_DIR = BASE_DIR / "data" / "faces"
MODEL_DIR = BASE_DIR / "models"
MODEL_PATH = MODEL_DIR / "lbph_model.yml"
CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
FACE_SIZE = (200, 200)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-secret-key-for-college-project")
face_cascade = cv2.CascadeClassifier(CASCADE_PATH)


def get_db_connection():
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return psycopg2.connect(database_url)

    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "attendance_system"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
    )


def ensure_folders():
    FACE_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)


def decode_image(data_url):
    if "," in data_url:
        data_url = data_url.split(",", 1)[1]

    image_bytes = base64.b64decode(data_url)
    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    if image is None:
        raise ValueError("Could not read the image from the browser.")

    return image


def detect_largest_face(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.2,
        minNeighbors=5,
        minSize=(80, 80),
    )

    if len(faces) == 0:
        return None

    x, y, w, h = max(faces, key=lambda box: box[2] * box[3])
    face = gray[y : y + h, x : x + w]
    return cv2.resize(face, FACE_SIZE)


def create_recognizer():
    if not hasattr(cv2, "face"):
        raise RuntimeError(
            "OpenCV face module is missing. Install dependencies with: "
            "pip install -r requirements.txt"
        )
    return cv2.face.LBPHFaceRecognizer_create()


def train_model():
    faces = []
    labels = []

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, face_image_path
                FROM students
                WHERE is_active = TRUE AND face_image_path IS NOT NULL
                """
            )
            students = cur.fetchall()

    for student in students:
        image_path = student["face_image_path"]
        if not image_path or not Path(image_path).exists():
            continue

        face = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if face is None:
            continue

        faces.append(cv2.resize(face, FACE_SIZE))
        labels.append(int(student["id"]))

    if not faces:
        return 0

    recognizer = create_recognizer()
    recognizer.train(faces, np.array(labels))
    recognizer.save(str(MODEL_PATH))
    return len(faces)


def load_model():
    if not MODEL_PATH.exists():
        return None

    recognizer = create_recognizer()
    recognizer.read(str(MODEL_PATH))
    return recognizer


def get_student_by_id(cur, student_id):
    cur.execute(
        """
        SELECT id, full_name, roll_number, is_active
        FROM students
        WHERE id = %s
        """,
        (student_id,),
    )
    return cur.fetchone()


def current_user():
    if "user_id" not in session:
        return None

    return {
        "id": session["user_id"],
        "full_name": session.get("full_name"),
        "username": session.get("username"),
        "role": session.get("role"),
    }


def require_login():
    if current_user() is None:
        return jsonify({"success": False, "message": "Please login first."}), 401
    return None


def require_role(role):
    login_error = require_login()
    if login_error:
        return login_error

    if session.get("role") != role:
        return jsonify({"success": False, "message": "You do not have permission for this action."}), 403

    return None


def parse_report_date(value):
    if not value:
        return date.today()

    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def fetch_attendance_report(report_date):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    s.id AS student_id,
                    s.full_name,
                    s.roll_number,
                    %s::date AS attendance_date,
                    CASE WHEN a.id IS NULL THEN 'absent' ELSE a.status END AS status,
                    TO_CHAR(a.marked_at, 'HH12:MI AM') AS marked_time,
                    a.marked_by,
                    u.full_name AS marked_by_name,
                    a.recognition_confidence
                FROM students s
                LEFT JOIN attendance a
                    ON a.student_id = s.id
                    AND a.attendance_date = %s
                LEFT JOIN users u ON u.id = a.marked_by_user_id
                WHERE s.is_active = TRUE
                ORDER BY s.roll_number, s.full_name
                """,
                (report_date, report_date),
            )
            return cur.fetchall()


@app.route("/")
def index():
    if session.get("role") == "admin":
        return redirect(url_for("admin_page"))
    if session.get("role") == "teacher":
        return redirect(url_for("teacher_page"))
    return redirect(url_for("login_page"))


@app.route("/login")
def login_page():
    if session.get("role") == "admin":
        return redirect(url_for("admin_page"))
    if session.get("role") == "teacher":
        return redirect(url_for("teacher_page"))
    return render_template("login.html")


@app.route("/admin")
def admin_page():
    if session.get("role") != "admin":
        return redirect(url_for("login_page"))
    return render_template("admin.html", user=current_user())


@app.route("/teacher")
def teacher_page():
    if session.get("role") != "teacher":
        return redirect(url_for("login_page"))
    return render_template("teacher.html", user=current_user())


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"success": False, "message": "Username and password are required."}), 400

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, full_name, username, password_hash, role
                FROM users
                WHERE username = %s AND is_active = TRUE
                """,
                (username,),
            )
            user = cur.fetchone()

    if user is None or not check_password_hash(user["password_hash"], password):
        return jsonify({"success": False, "message": "Invalid username or password."}), 401

    session["user_id"] = user["id"]
    session["full_name"] = user["full_name"]
    session["username"] = user["username"]
    session["role"] = user["role"]

    redirect_url = url_for("admin_page") if user["role"] == "admin" else url_for("teacher_page")
    return jsonify({"success": True, "redirect_url": redirect_url})


@app.route("/api/register", methods=["POST"])
def register_student():
    permission_error = require_role("admin")
    if permission_error:
        return permission_error

    data = request.get_json(silent=True) or {}
    full_name = (data.get("full_name") or "").strip()
    roll_number = (data.get("roll_number") or "").strip()
    image_data = data.get("image")

    if not full_name or not roll_number or not image_data:
        return jsonify({"success": False, "message": "Name, roll number, and photo are required."}), 400

    try:
        image = decode_image(image_data)
        face = detect_largest_face(image)

        if face is None:
            return jsonify({"success": False, "message": "No face found. Sit facing the camera and try again."}), 400

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO students (roll_number, full_name)
                    VALUES (%s, %s)
                    RETURNING id
                    """,
                    (roll_number, full_name),
                )
                student = cur.fetchone()

                file_name = f"student_{student['id']}_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
                face_path = FACE_DIR / file_name
                cv2.imwrite(str(face_path), face)

                cur.execute(
                    "UPDATE students SET face_image_path = %s WHERE id = %s",
                    (str(face_path), student["id"]),
                )

        trained_faces = train_model()
        return jsonify(
            {
                "success": True,
                "message": f"Student registered successfully. Model trained with {trained_faces} face(s).",
            }
        )
    except psycopg2.errors.UniqueViolation:
        return jsonify({"success": False, "message": "This roll number is already registered."}), 409
    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 500


@app.route("/api/mark-attendance", methods=["POST"])
def mark_attendance():
    permission_error = require_role("teacher")
    if permission_error:
        return permission_error

    data = request.get_json(silent=True) or {}
    image_data = data.get("image")

    if not image_data:
        return jsonify({"success": False, "message": "Photo is required."}), 400

    try:
        recognizer = load_model()
        if recognizer is None:
            return jsonify({"success": False, "message": "No trained face model found. Register a student first."}), 400

        image = decode_image(image_data)
        face = detect_largest_face(image)

        if face is None:
            return jsonify({"success": False, "message": "No face found. Look at the camera and try again."}), 400

        student_id, confidence = recognizer.predict(face)
        threshold = float(os.getenv("FACE_CONFIDENCE_THRESHOLD", "80"))

        if confidence > threshold:
            return jsonify(
                {
                    "success": False,
                    "message": "Face not recognized. Try better lighting or register again.",
                    "confidence": round(float(confidence), 2),
                }
            ), 404

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT id, full_name, roll_number FROM students WHERE id = %s AND is_active = TRUE",
                    (int(student_id),),
                )
                student = cur.fetchone()

                if student is None:
                    return jsonify({"success": False, "message": "Recognized student is not active."}), 404

                cur.execute(
                    """
                    INSERT INTO attendance (student_id, marked_by, marked_by_user_id, recognition_confidence)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (student_id, attendance_date) DO NOTHING
                    RETURNING id
                    """,
                    (student["id"], "face_recognition", session["user_id"], float(confidence)),
                )
                inserted = cur.fetchone()

        if inserted:
            message = f"Attendance marked for {student['full_name']}."
        else:
            message = f"{student['full_name']} is already marked present today."

        return jsonify(
            {
                "success": True,
                "message": message,
                "student": dict(student),
                "confidence": round(float(confidence), 2),
            }
        )
    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 500


@app.route("/api/today")
def today_attendance():
    permission_error = require_login()
    if permission_error:
        return permission_error

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    a.id,
                    s.full_name,
                    s.roll_number,
                    a.attendance_date,
                    TO_CHAR(a.marked_at, 'HH12:MI AM') AS marked_time,
                    a.status,
                    a.marked_by,
                    a.recognition_confidence
                FROM attendance a
                JOIN students s ON s.id = a.student_id
                WHERE a.attendance_date = %s
                ORDER BY a.marked_at DESC
                """,
                (date.today(),),
            )
            rows = cur.fetchall()

    return jsonify({"success": True, "attendance": rows})


@app.route("/api/admin/students")
def admin_students():
    permission_error = require_login()
    if permission_error:
        return permission_error

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    s.id,
                    s.full_name,
                    s.roll_number,
                    s.is_active,
                    CASE WHEN a.id IS NULL THEN FALSE ELSE TRUE END AS present_today,
                    TO_CHAR(a.marked_at, 'HH12:MI AM') AS marked_time,
                    a.marked_by
                FROM students s
                LEFT JOIN attendance a
                    ON a.student_id = s.id
                    AND a.attendance_date = CURRENT_DATE
                WHERE s.is_active = TRUE
                ORDER BY s.roll_number, s.full_name
                """
            )
            rows = cur.fetchall()

    return jsonify({"success": True, "students": rows})


@app.route("/api/dashboard-stats")
def dashboard_stats():
    permission_error = require_login()
    if permission_error:
        return permission_error

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT COUNT(*) AS total_students FROM students WHERE is_active = TRUE")
            total_students = cur.fetchone()["total_students"]

            cur.execute(
                """
                SELECT COUNT(*) AS present_today
                FROM attendance
                WHERE attendance_date = CURRENT_DATE
                """
            )
            present_today = cur.fetchone()["present_today"]

            cur.execute(
                """
                SELECT COUNT(*) AS total_teachers
                FROM users
                WHERE role = 'teacher' AND is_active = TRUE
                """
            )
            total_teachers = cur.fetchone()["total_teachers"]

    absent_today = max(total_students - present_today, 0)

    return jsonify(
        {
            "success": True,
            "stats": {
                "total_students": total_students,
                "present_today": present_today,
                "absent_today": absent_today,
                "total_teachers": total_teachers,
            },
        }
    )


@app.route("/api/reports/attendance")
def attendance_report():
    permission_error = require_login()
    if permission_error:
        return permission_error

    report_date = parse_report_date(request.args.get("date"))
    if report_date is None:
        return jsonify({"success": False, "message": "Use date format YYYY-MM-DD."}), 400

    rows = fetch_attendance_report(report_date)
    present_count = sum(1 for row in rows if row["status"] == "present")
    absent_count = len(rows) - present_count

    return jsonify(
        {
            "success": True,
            "date": report_date.isoformat(),
            "summary": {
                "total_students": len(rows),
                "present": present_count,
                "absent": absent_count,
            },
            "attendance": rows,
        }
    )


@app.route("/api/reports/attendance.csv")
def attendance_report_csv():
    permission_error = require_login()
    if permission_error:
        return permission_error

    report_date = parse_report_date(request.args.get("date"))
    if report_date is None:
        return jsonify({"success": False, "message": "Use date format YYYY-MM-DD."}), 400

    rows = fetch_attendance_report(report_date)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Roll Number", "Student Name", "Status", "Marked Time", "Marked By", "Confidence"])

    for row in rows:
        marked_by = row["marked_by_name"] or row["marked_by"] or "-"
        writer.writerow(
            [
                report_date.isoformat(),
                row["roll_number"],
                row["full_name"],
                row["status"].title(),
                row["marked_time"] or "-",
                marked_by,
                row["recognition_confidence"] if row["recognition_confidence"] is not None else "-",
            ]
        )

    filename = f"attendance_report_{report_date.isoformat()}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.route("/api/teacher/manual-attendance", methods=["POST"])
def teacher_manual_attendance():
    permission_error = require_role("teacher")
    if permission_error:
        return permission_error

    data = request.get_json(silent=True) or {}
    student_id = data.get("student_id")

    if not student_id:
        return jsonify({"success": False, "message": "Student is required."}), 400

    try:
        student_id = int(student_id)
    except ValueError:
        return jsonify({"success": False, "message": "Invalid student id."}), 400

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            student = get_student_by_id(cur, student_id)

            if student is None or not student["is_active"]:
                return jsonify({"success": False, "message": "Student not found or inactive."}), 404

            cur.execute(
                """
                INSERT INTO attendance (student_id, marked_by, marked_by_user_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (student_id, attendance_date) DO NOTHING
                RETURNING id
                """,
                (student_id, "teacher_manual", session["user_id"]),
            )
            inserted = cur.fetchone()

    if inserted:
        message = f"Teacher marked attendance for {student['full_name']}."
    else:
        message = f"{student['full_name']} is already marked present today."

    return jsonify({"success": True, "message": message})


@app.route("/api/admin/teachers")
def admin_teachers():
    permission_error = require_role("admin")
    if permission_error:
        return permission_error

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, full_name, username, is_active, created_at
                FROM users
                WHERE role = 'teacher'
                ORDER BY created_at DESC
                """
            )
            teachers = cur.fetchall()

    return jsonify({"success": True, "teachers": teachers})


@app.route("/api/admin/teachers", methods=["POST"])
def admin_add_teacher():
    permission_error = require_role("admin")
    if permission_error:
        return permission_error

    data = request.get_json(silent=True) or {}
    full_name = (data.get("full_name") or "").strip()
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not full_name or not username or not password:
        return jsonify({"success": False, "message": "Teacher name, username, and password are required."}), 400

    if len(password) < 6:
        return jsonify({"success": False, "message": "Password must be at least 6 characters."}), 400

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (full_name, username, password_hash, role)
                    VALUES (%s, %s, %s, 'teacher')
                    """,
                    (full_name, username, generate_password_hash(password)),
                )
    except psycopg2.errors.UniqueViolation:
        return jsonify({"success": False, "message": "This username is already used."}), 409

    return jsonify({"success": True, "message": f"Teacher account created for {full_name}."})


@app.route("/api/admin/teachers/<int:teacher_id>", methods=["DELETE"])
def admin_delete_teacher(teacher_id):
    permission_error = require_role("admin")
    if permission_error:
        return permission_error

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, full_name, username
                FROM users
                WHERE id = %s AND role = 'teacher'
                """,
                (teacher_id,),
            )
            teacher = cur.fetchone()

            if teacher is None:
                return jsonify({"success": False, "message": "Teacher account not found."}), 404

            cur.execute(
                "UPDATE users SET is_active = FALSE WHERE id = %s AND role = 'teacher'",
                (teacher_id,),
            )

    return jsonify({"success": True, "message": f"Teacher account for {teacher['full_name']} was deleted."})


@app.route("/api/admin/students/<int:student_id>", methods=["DELETE"])
def admin_delete_student(student_id):
    permission_error = require_role("admin")
    if permission_error:
        return permission_error

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            student = get_student_by_id(cur, student_id)

            if student is None:
                return jsonify({"success": False, "message": "Student not found."}), 404

            cur.execute("DELETE FROM students WHERE id = %s", (student_id,))

    train_model()
    return jsonify({"success": True, "message": f"{student['full_name']} was deleted from the system."})


ensure_folders()


if __name__ == "__main__":
    app.run(debug=True)
