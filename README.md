# Face Recognition Attendance System

This is a beginner-friendly college project using:

- HTML, CSS, and JavaScript for the web page and camera
- Python Flask for the backend
- OpenCV for face detection and face recognition
- PostgreSQL for student and attendance records

## Step 1: Open This Folder In VS Code

Open this project folder:

```powershell
c:\Users\sarth_q4pse7u\.vscode\attendace_system
```

## Step 2: Create The PostgreSQL Database And Tables

Open PowerShell in this folder and run:

```powershell
psql -U postgres -f schema.sql
```

PostgreSQL will ask for your `postgres` password.

If PowerShell says `psql` is not recognized, use the full PostgreSQL path:

```powershell
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -f schema.sql
```

When it asks for the password, type your PostgreSQL password there. Do not type the password as a separate PowerShell command.

If `psql` is not recognized, open **SQL Shell (psql)** from the Start Menu and run:

```sql
\i 'c:/Users/sarth_q4pse7u/.vscode/attendace_system/schema.sql'
```

## Step 3: Create Your Python Virtual Environment

Run these commands in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run this once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then activate again:

```powershell
.\.venv\Scripts\Activate.ps1
```

## Step 4: Install Python Packages

```powershell
pip install -r requirements.txt
```

## Step 5: Create Your `.env` File

Copy `.env.example` and create a new file named `.env`.

Update this line with your real PostgreSQL password:

```env
DB_PASSWORD=your_postgres_password_here
```

## Step 6: Run The Project

```powershell
python app.py
```

Open this URL in your browser:

```text
http://127.0.0.1:5000
```

For online hosting and smartphone camera usage, see `DEPLOYMENT.md`.

## Step 7: Use The System

Login with the default admin account:

```text
Username: admin
Password: admin123
```

Admin can:

- Add student name, roll number, and face photo.
- Add teacher login accounts.
- Delete teacher accounts.
- Delete students from the system.
- View dashboard cards for total students, present today, absent today, and total teachers.

Teacher can:

- Login with the account created by admin.
- Mark attendance using face recognition.
- Manually mark a student present if face recognition misses the student.
- View today's attendance records.
- View dashboard cards for total students, present today, and absent today.

Reports:

- Admin and teacher can select a date and view present/absent records.
- Admin and teacher can download the selected date report as a CSV file.

## Updating The Database After Project Changes

If we add new database columns later, run the schema file again. It is safe because the script uses `IF NOT EXISTS`.

```powershell
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -f schema.sql
```

For this role-based update, running the command above creates the `users` table, default admin account, and teacher/manual attendance tracking columns.

## Important Notes

- This project uses OpenCV LBPH face recognition, which is easier to install than advanced deep learning face recognition libraries.
- For better accuracy, use good lighting and keep your face straight toward the camera.
- If the wrong person is recognized, reduce `FACE_CONFIDENCE_THRESHOLD` in `.env`, for example from `80` to `65`.
- If the correct person is not recognized, increase `FACE_CONFIDENCE_THRESHOLD`, for example from `80` to `90`.

## Database Tables

The `students` table stores student details and the saved face image path.

The `attendance` table stores one attendance record per student per day.

The `users` table stores admin and teacher login accounts.
