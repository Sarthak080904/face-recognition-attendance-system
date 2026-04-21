const video = document.querySelector("#camera");
const canvas = document.querySelector("#snapshot");
const cameraStatus = document.querySelector("#cameraStatus");
const registerBtn = document.querySelector("#registerBtn");
const teacherBtn = document.querySelector("#teacherBtn");
const refreshStudentsBtn = document.querySelector("#refreshStudentsBtn");
const refreshTeachersBtn = document.querySelector("#refreshTeachersBtn");
const adminResult = document.querySelector("#adminResult");
const studentTable = document.querySelector("#studentTable");
const teacherTable = document.querySelector("#teacherTable");
const reportDate = document.querySelector("#reportDate");
const loadReportBtn = document.querySelector("#loadReportBtn");
const downloadReportBtn = document.querySelector("#downloadReportBtn");
const reportSummary = document.querySelector("#reportSummary");
const reportTable = document.querySelector("#reportTable");
const totalStudents = document.querySelector("#totalStudents");
const presentToday = document.querySelector("#presentToday");
const absentToday = document.querySelector("#absentToday");
const totalTeachers = document.querySelector("#totalTeachers");

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
        showAdminResult("Please allow camera access to register student faces.", false);
    }
}

function captureImage() {
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext("2d");
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/jpeg", 0.9);
}

function showAdminResult(message, success = true) {
    adminResult.textContent = message;
    adminResult.className = success ? "result-box success" : "result-box error";
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

async function registerStudent() {
    const fullName = document.querySelector("#fullName").value.trim();
    const rollNumber = document.querySelector("#rollNumber").value.trim();

    if (!fullName || !rollNumber) {
        showAdminResult("Enter student name and roll number.", false);
        return;
    }

    registerBtn.disabled = true;
    showAdminResult("Adding student face...");

    try {
        const data = await requestJson("/api/register", {
            method: "POST",
            body: JSON.stringify({
                full_name: fullName,
                roll_number: rollNumber,
                image: captureImage(),
            }),
        });
        showAdminResult(data.message);
        document.querySelector("#fullName").value = "";
        document.querySelector("#rollNumber").value = "";
        await loadStudents();
        await loadStats();
    } catch (error) {
        showAdminResult(error.message, false);
    } finally {
        registerBtn.disabled = false;
    }
}

async function addTeacher() {
    const fullName = document.querySelector("#teacherName").value.trim();
    const username = document.querySelector("#teacherUsername").value.trim();
    const password = document.querySelector("#teacherPassword").value;

    teacherBtn.disabled = true;
    showAdminResult("Creating teacher account...");

    try {
        const data = await requestJson("/api/admin/teachers", {
            method: "POST",
            body: JSON.stringify({ full_name: fullName, username, password }),
        });
        showAdminResult(data.message);
        document.querySelector("#teacherName").value = "";
        document.querySelector("#teacherUsername").value = "";
        document.querySelector("#teacherPassword").value = "";
        await loadTeachers();
        await loadStats();
    } catch (error) {
        showAdminResult(error.message, false);
    } finally {
        teacherBtn.disabled = false;
    }
}

async function loadStudents() {
    const data = await requestJson("/api/admin/students");
    const rows = data.students || [];

    if (rows.length === 0) {
        studentTable.innerHTML = `<tr><td colspan="4">No active students yet.</td></tr>`;
        return;
    }

    studentTable.innerHTML = rows
        .map((student) => {
            const status = student.present_today ? `Present at ${student.marked_time}` : "Not marked";
            const statusClass = student.present_today ? "pill" : "pill danger";
            return `
                <tr>
                    <td>${student.full_name}</td>
                    <td>${student.roll_number}</td>
                    <td><span class="${statusClass}">${status}</span></td>
                    <td><button type="button" class="small-btn danger-btn delete-student-btn" data-student-id="${student.id}">Delete</button></td>
                </tr>
            `;
        })
        .join("");
}

async function loadTeachers() {
    const data = await requestJson("/api/admin/teachers");
    const rows = data.teachers || [];

    if (rows.length === 0) {
        teacherTable.innerHTML = `<tr><td colspan="4">No teacher accounts yet.</td></tr>`;
        return;
    }

    teacherTable.innerHTML = rows
        .map((teacher) => `
            <tr>
                <td>${teacher.full_name}</td>
                <td>${teacher.username}</td>
                <td><span class="pill">${teacher.is_active ? "Active" : "Inactive"}</span></td>
                <td><button type="button" class="small-btn danger-btn delete-teacher-btn" data-teacher-id="${teacher.id}" ${teacher.is_active ? "" : "disabled"}>Delete</button></td>
            </tr>
        `)
        .join("");
}

async function deleteStudent(studentId) {
    if (!confirm("Delete this student from the active list?")) {
        return;
    }

    try {
        const data = await requestJson(`/api/admin/students/${studentId}`, {
            method: "DELETE",
        });
        showAdminResult(data.message);
        await loadStudents();
        await loadStats();
    } catch (error) {
        showAdminResult(error.message, false);
    }
}

async function deleteTeacher(teacherId) {
    if (!confirm("Delete this teacher account? The teacher will no longer be able to login.")) {
        return;
    }

    try {
        const data = await requestJson(`/api/admin/teachers/${teacherId}`, {
            method: "DELETE",
        });
        showAdminResult(data.message);
        await loadTeachers();
        await loadStats();
    } catch (error) {
        showAdminResult(error.message, false);
    }
}

async function loadStats() {
    const data = await requestJson("/api/dashboard-stats");
    const stats = data.stats;

    totalStudents.textContent = stats.total_students;
    presentToday.textContent = stats.present_today;
    absentToday.textContent = stats.absent_today;
    totalTeachers.textContent = stats.total_teachers;
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

registerBtn.addEventListener("click", registerStudent);
teacherBtn.addEventListener("click", addTeacher);
refreshStudentsBtn.addEventListener("click", loadStudents);
refreshTeachersBtn.addEventListener("click", loadTeachers);
loadReportBtn.addEventListener("click", loadReport);
downloadReportBtn.addEventListener("click", downloadReport);
studentTable.addEventListener("click", (event) => {
    const button = event.target.closest(".delete-student-btn");
    if (button) {
        deleteStudent(button.dataset.studentId);
    }
});
teacherTable.addEventListener("click", (event) => {
    const button = event.target.closest(".delete-teacher-btn");
    if (button) {
        deleteTeacher(button.dataset.teacherId);
    }
});

reportDate.value = getLocalDateValue();
startCamera();
loadStats();
loadStudents();
loadTeachers();
loadReport();
