-- Run this file with PostgreSQL psql, not inside pgAdmin's normal query window.
-- It creates the database if it does not exist, then creates the required tables.
--
-- Example:
-- psql -U postgres -f schema.sql

SELECT 'CREATE DATABASE attendance_system'
WHERE NOT EXISTS (
    SELECT FROM pg_database WHERE datname = 'attendance_system'
)\gexec

\connect attendance_system

CREATE TABLE IF NOT EXISTS students (
    id SERIAL PRIMARY KEY,
    roll_number VARCHAR(50) UNIQUE NOT NULL,
    full_name VARCHAR(120) NOT NULL,
    face_image_path TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(120) NOT NULL,
    username VARCHAR(80) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'teacher')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS attendance (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    attendance_date DATE NOT NULL DEFAULT CURRENT_DATE,
    marked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status VARCHAR(20) NOT NULL DEFAULT 'present',
    marked_by VARCHAR(30) NOT NULL DEFAULT 'face_recognition',
    recognition_confidence NUMERIC(8, 3),
    UNIQUE (student_id, attendance_date)
);

ALTER TABLE attendance
ADD COLUMN IF NOT EXISTS marked_by VARCHAR(30) NOT NULL DEFAULT 'face_recognition';

ALTER TABLE attendance
ADD COLUMN IF NOT EXISTS marked_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(attendance_date);
CREATE INDEX IF NOT EXISTS idx_attendance_student_id ON attendance(student_id);

INSERT INTO users (full_name, username, password_hash, role)
SELECT
    'System Admin',
    'admin',
    'pbkdf2:sha256:600000$qv8QwsWCcQSXXmiP$cc6cb97c1494b6ced4aebdb3c4017a7da09e16a1d65e5412a92de9307e69c0ef',
    'admin'
WHERE NOT EXISTS (
    SELECT FROM users WHERE username = 'admin'
);
