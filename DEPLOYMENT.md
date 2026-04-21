# Free Hosting Guide

This guide explains how to host the Face Recognition Attendance System online so it can be opened from a smartphone browser.

Recommended free setup:

- Flask app hosting: Render
- PostgreSQL database: Neon
- Code hosting: GitHub

## Important Notes

- Phone camera access requires HTTPS. Render gives an HTTPS URL automatically.
- GitHub Pages, Netlify, and Vercel static hosting are not enough because this project needs a Python/OpenCV backend.
- Free hosting can sleep after inactivity. The first request may take some time.
- Uploaded face images and the trained model are stored on the server filesystem. On free hosting this can be temporary. For a college demo, it is acceptable, but for production use cloud storage should be added.

## Step 1: Create A Neon PostgreSQL Database

1. Go to `https://neon.tech/`.
2. Create a free account.
3. Create a new PostgreSQL project.
4. Copy the database connection string. It looks like:

```text
postgresql://username:password@host/database?sslmode=require
```

This will be used as `DATABASE_URL` on Render.

## Step 2: Upload Project To GitHub

Create a GitHub repository and upload this project folder.

Do not upload `.env` because it contains your password.

Files that should be uploaded include:

- `app.py`
- `requirements.txt`
- `.python-version`
- `runtime.txt`
- `schema.sql`
- `render.yaml`
- `templates/`
- `static/`
- `README.md`
- `DEPLOYMENT.md`

## Step 3: Create Render Web Service

1. Go to `https://render.com/`.
2. Create a free account.
3. Click **New +**.
4. Select **Web Service**.
5. Connect your GitHub repository.
6. Render should detect `render.yaml`.
7. Add this environment variable manually:

```text
DATABASE_URL=your_neon_database_connection_string
```

8. Deploy the service.

Render will give a URL like:

```text
https://face-recognition-attendance-system.onrender.com
```

## Step 4: Create Tables In Online Database

Open Neon SQL Editor and run the table creation part of `schema.sql`.

Important: Neon SQL Editor does not support `\connect` and `\gexec`, so do not run those lines there.

Run from:

```sql
CREATE TABLE IF NOT EXISTS students ...
```

through the default admin insert query.

The default admin login is:

```text
Username: admin
Password: admin123
```

## Step 5: Open Website On Smartphone

Open your Render HTTPS URL on your phone:

```text
https://your-render-app-name.onrender.com
```

Login as teacher and allow camera permission.

The phone camera should work because Render uses HTTPS.

## Step 6: Common Problems

### Camera Not Opening

Check:

- Website URL starts with `https://`
- Browser camera permission is allowed
- Phone browser supports camera access

### Database Error

Check:

- `DATABASE_URL` is correctly added in Render environment variables
- Neon database is active
- Tables were created

### psycopg2 Python Version Error

If Render logs show an error like:

```text
undefined symbol: _PyInterpreterState_Get
```

Render is using an unsupported Python version. First, add this environment variable in Render:

```text
PYTHON_VERSION=3.10.13
```

Also make sure this file exists in your GitHub repository:

```text
.python-version
```

It should contain:

```text
3.10.13
```

This older file is also included for compatibility:

```text
runtime.txt
```

It should contain:

```text
python-3.10.13
```

Commit and push the file, then redeploy on Render.

### Face Recognition Fails

Try:

- Better lighting
- Register face again
- Increase `FACE_CONFIDENCE_THRESHOLD` from `80` to `90`

### App Sleeps

Free Render apps may sleep after inactivity. Open the URL and wait 30-60 seconds.

## Production Improvement Ideas

For real production use, add:

- Cloud image storage
- Cloud model storage
- Admin password change
- HTTPS-only cookies
- Better face recognition model
- Anti-spoofing/liveness detection
