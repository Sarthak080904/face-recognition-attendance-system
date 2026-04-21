const usernameInput = document.querySelector("#username");
const passwordInput = document.querySelector("#password");
const loginBtn = document.querySelector("#loginBtn");
const loginResult = document.querySelector("#loginResult");

function showLoginResult(message, success = true) {
    loginResult.textContent = message;
    loginResult.className = success ? "result-box success" : "result-box error";
}

async function login() {
    const username = usernameInput.value.trim();
    const password = passwordInput.value;

    if (!username || !password) {
        showLoginResult("Enter username and password.", false);
        return;
    }

    loginBtn.disabled = true;
    showLoginResult("Checking login...");

    try {
        const response = await fetch("/api/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password }),
        });
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.message || "Login failed.");
        }

        window.location.href = data.redirect_url;
    } catch (error) {
        showLoginResult(error.message, false);
    } finally {
        loginBtn.disabled = false;
    }
}

loginBtn.addEventListener("click", login);
passwordInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
        login();
    }
});
