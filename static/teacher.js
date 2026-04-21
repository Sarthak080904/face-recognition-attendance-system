const video = document.querySelector("#camera");
const canvas = document.querySelector("#snapshot");
const cameraStatus = document.querySelector("#cameraStatus");
const attendanceBtn = document.querySelector("#attendanceBtn");
const refreshStudentsBtn = document.querySelector("#refreshStudentsBtn");
const refreshAttendanceBtn = document.querySelector("#refreshAttendanceBtn");
const resultBox = document.querySelector("#resultBox");
const teacherResult = document.querySelector("#teacherResult");
const studentAdminTable = document.querySelector("#studentAdminTable");
const attendanceTable = document.querySelector("#attendanceTable");
const reportDate = document.querySelector("#reportDate");
const loadReportBtn = document.querySelector("#loadReportBtn");
const downloadReportBtn = document.querySelector("#downloadReportBtn");
const reportSummary = document.querySelector("#reportSummary");
const reportTable = document.querySelector("#reportTable");
const totalStudents = document.querySelector("#totalStudents");
const presentToday = document.querySelector("#presentToday");
const absentToday = document.querySelector("#absentToday");

async function startCamera() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: { width: 640, height: 480 },
            audio: false,
        });
        video.srcObject = stream;
        cameraStatus.textContent = "Camera ready.";
    } catch (error) {
        cameraStatus.textContent = "Camera permission denied or camera not found.";
        showResult("Please allow camera access to mark face attendance.", false);
    }
}

function captureImage() {
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext("2d");
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/jpeg", 0.9);
}

function showResult(message, success = true) {
    resultBox.textContent = message;
    resultBox.className = success ? "result-box success" : "result-box error";
}

function showTeacherResult(message, success = true) {
    teacherResult.textContent = message;
    teacherResult.className = success ? "result-box success" : "result-box error";
}

function formatMarkedBy(row) {
    if (row.marked_by_name) {
        return row.marked_by_name;
    }

    if (row.marked_by === "teacher_manual") {
        return "Teacher Manual";
    }

    if (row.marked_by === "face_recognition") {
        return "Face Recognition";
    }

    return "-";
}

function getLocalDateValue() {
    const today = new Date();
    const timezoneOffset = today.getTimezoneOffset() * 60000;
    return new Date(today.getTime() - timezoneOffset).toISOString().slice(0, 10);
}

async function requestJson(url, options = {}) {
    const response = await fetch(url, {
        headers: { "Content-Type": "application/json" },
        ...options,
    });
    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.message || "Something went wrong.");
    }

    return data;
}

async function markFaceAttendance() {
    attendanceBtn.disabled = true;
    showResult("Recognizing face...");

    try {
        const data = await requestJson("/api/mark-attendance", {
            method: "POST",
            body: JSON.stringify({ image: captureImage() }),
        });
        showResult(`${data.message} Confidence: ${data.confidence}`);
        await refreshTeacherData();
    } catch (error) {
        showResult(error.message, false);
    } finally {
        attendanceBtn.disabled = false;
    }
}

async function loadStudents() {
    const data = await requestJson("/api/admin/students");
    const rows = data.students || [];

    if (rows.length === 0) {
        studentAdminTable.innerHTML = `<tr><td colspan="4">No students registered yet.</td></tr>`;
        return;
    }

    studentAdminTable.innerHTML = rows
        .map((student) => {
            const statusClass = student.present_today ? "pill" : "pill danger";
            const statusText = student.present_today ? `Present at ${student.marked_time}` : "Not marked";
            const action = student.present_today
                ? `<button type="button" class="small-btn" disabled>Already Present</button>`
                : `<button type="button" class="small-btn manual-btn" data-student-id="${student.id}">Mark Present</button>`;

            return `
                <tr>
                    <td>${student.full_name}</td>
                    <td>${student.roll_number}</td>
                    <td><span class="${statusClass}">${statusText}</span></td>
                    <td>${action}</td>
                </tr>
            `;
        })
        .join("");
}

async function loadTodayAttendance() {
    const data = await requestJson("/api/today");
    const rows = data.attendance || [];

    if (rows.length === 0) {
        attendanceTable.innerHTML = `<tr><td colspan="5">No attendance marked today.</td></tr>`;
        return;
    }

    attendanceTable.innerHTML = rows
        .map((row) => {
            const markedBy = row.marked_by === "teacher_manual" ? "Teacher Manual" : "Face Recognition";
            const confidence = row.recognition_confidence ?? "-";
            return `
                <tr>
                    <td>${row.full_name}</td>
                    <td>${row.roll_number}</td>
                    <td>${row.marked_time}</td>
                    <td><span class="pill">${markedBy}</span></td>
                    <td>${confidence}</td>
                </tr>
            `;
        })
        .join("");
}

async function markManualAttendance(studentId) {
    showTeacherResult("Marking manual attendance...");

    try {
        const data = await requestJson("/api/teacher/manual-attendance", {
            method: "POST",
            body: JSON.stringify({ student_id: studentId }),
        });
        showTeacherResult(data.message);
        await refreshTeacherData();
    } catch (error) {
        showTeacherResult(error.message, false);
    }
}

async function refreshTeacherData() {
    await loadStudents();
    await loadTodayAttendance();
    await loadStats();
}

async function loadStats() {
    const data = await requestJson("/api/dashboard-stats");
    const stats = data.stats;

    totalStudents.textContent = stats.total_students;
    presentToday.textContent = stats.present_today;
    absentToday.textContent = stats.absent_today;
}

async function loadReport() {
    const selectedDate = reportDate.value;
    const data = await requestJson(`/api/reports/attendance?date=${selectedDate}`);
    const rows = data.attendance || [];

    reportSummary.textContent = `Date: ${data.date} | Total: ${data.summary.total_students} | Present: ${data.summary.present} | Absent: ${data.summary.absent}`;
    reportSummary.className = "result-box success";

    if (rows.length === 0) {
        reportTable.innerHTML = `<tr><td colspan="5">No students found for report.</td></tr>`;
        return;
    }

    reportTable.innerHTML = rows
        .map((row) => {
            const statusClass = row.status === "present" ? "pill" : "pill danger";
            return `
                <tr>
                    <td>${row.full_name}</td>
                    <td>${row.roll_number}</td>
                    <td><span class="${statusClass}">${row.status}</span></td>
                    <td>${row.marked_time || "-"}</td>
                    <td>${formatMarkedBy(row)}</td>
                </tr>
            `;
        })
        .join("");
}

function downloadReport() {
    window.location.href = `/api/reports/attendance.csv?date=${reportDate.value}`;
}

attendanceBtn.addEventListener("click", markFaceAttendance);
refreshStudentsBtn.addEventListener("click", loadStudents);
refreshAttendanceBtn.addEventListener("click", loadTodayAttendance);
loadReportBtn.addEventListener("click", loadReport);
downloadReportBtn.addEventListener("click", downloadReport);
studentAdminTable.addEventListener("click", (event) => {
    const button = event.target.closest(".manual-btn");
    if (button) {
        markManualAttendance(button.dataset.studentId);
    }
});

reportDate.value = getLocalDateValue();
startCamera();
refreshTeacherData();
loadReport();
