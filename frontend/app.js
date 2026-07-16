const API_BASE = window.location.protocol === "file:"
    ? "http://127.0.0.1:5000/api"
    : `${window.location.origin}/api`;
const APPLICATIONS_URL = `${API_BASE}/applications`;
const VALID_STATUSES = ["Applied", "Interview", "Offer", "Rejected"];

let applicationsData = [];

async function apiFetch(path, options = {}) {
    const response = await fetch(`${API_BASE}${path}`, {
        credentials: "include",
        ...options,
        headers: {
            ...(options.body ? { "Content-Type": "application/json" } : {}),
            ...options.headers,
        },
    });

    if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.error || `${response.status} ${response.statusText}`);
    }
    return response;
}

function showMessage(message, isError = false) {
    const element = document.getElementById("message");
    element.textContent = message;
    element.classList.toggle("error", isError);
}

function showAuthenticatedView(user) {
    document.getElementById("auth-section").hidden = true;
    document.getElementById("tracker-section").hidden = false;
    document.getElementById("account-bar").hidden = false;
    document.getElementById("current-user").textContent = user.email;
}

function showLoggedOutView() {
    applicationsData = [];
    document.getElementById("tracker-section").hidden = true;
    document.getElementById("auth-section").hidden = false;
    document.getElementById("account-bar").hidden = true;
    document.getElementById("applications-body").innerHTML = "";
}

async function checkSession() {
    try {
        const response = await apiFetch("/auth/me");
        const { user } = await response.json();
        showAuthenticatedView(user);
        await fetchApplications();
    } catch (error) {
        showLoggedOutView();
    }
}

async function submitAuth(event) {
    event.preventDefault();
    const submitter = event.submitter;
    const action = submitter?.dataset.action || "login";
    const email = document.getElementById("auth-email").value.trim();
    const password = document.getElementById("auth-password").value;

    try {
        const response = await apiFetch(`/auth/${action}`, {
            method: "POST",
            body: JSON.stringify({ email, password }),
        });
        const { user } = await response.json();
        document.getElementById("auth-form").reset();
        showMessage(action === "register" ? "Account created." : "Welcome back.");
        showAuthenticatedView(user);
        await fetchApplications();
    } catch (error) {
        showMessage(error.message, true);
    }
}

async function logout() {
    try {
        await apiFetch("/auth/logout", { method: "POST" });
        showMessage("You have been logged out.");
        showLoggedOutView();
    } catch (error) {
        showMessage(error.message, true);
    }
}

async function fetchApplications() {
    try {
        const response = await apiFetch("/applications");
        applicationsData = await response.json();
        const filterStatus = document.getElementById("status-filter").value;
        renderApplications(applicationsData, filterStatus);
    } catch (error) {
        showMessage(error.message, true);
        if (error.message === "Authentication required") {
            showLoggedOutView();
        }
    }
}

function renderApplications(applications, filterStatus = "All") {
    const tbody = document.getElementById("applications-body");
    tbody.innerHTML = "";
    const list = filterStatus === "All"
        ? applications
        : applications.filter((application) => application.status === filterStatus);

    for (const application of list) {
        const row = document.createElement("tr");
        for (const field of ["company", "position", "date_applied", "status", "notes"]) {
            const cell = document.createElement("td");
            cell.textContent = application[field] ?? "";
            row.appendChild(cell);
        }

        const actions = document.createElement("td");
        const editButton = document.createElement("button");
        editButton.type = "button";
        editButton.textContent = "Edit Status";
        editButton.addEventListener("click", () => updateStatus(application.id, application.status));

        const deleteButton = document.createElement("button");
        deleteButton.type = "button";
        deleteButton.textContent = "Delete";
        deleteButton.addEventListener("click", () => deleteApplication(application.id));

        actions.append(editButton, deleteButton);
        row.appendChild(actions);
        tbody.appendChild(row);
    }
}

async function addApplication(event) {
    event.preventDefault();
    const payload = {
        company: document.getElementById("company").value.trim(),
        position: document.getElementById("position").value.trim(),
        date_applied: document.getElementById("date-applied").value,
        status: document.getElementById("status").value,
        notes: document.getElementById("notes").value.trim(),
    };

    try {
        await apiFetch("/applications", { method: "POST", body: JSON.stringify(payload) });
        document.getElementById("application-form").reset();
        showMessage("Application added.");
        await fetchApplications();
    } catch (error) {
        showMessage(error.message, true);
    }
}

async function updateStatus(id, currentStatus) {
    const input = prompt(`Enter new status (current: ${currentStatus}):`, currentStatus);
    if (input === null) return;
    const status = input.trim();
    if (!VALID_STATUSES.includes(status)) {
        showMessage("Choose Applied, Interview, Offer, or Rejected.", true);
        return;
    }

    try {
        await apiFetch(`/applications/${id}`, {
            method: "PUT",
            body: JSON.stringify({ status }),
        });
        await fetchApplications();
    } catch (error) {
        showMessage(error.message, true);
    }
}

async function deleteApplication(id) {
    if (!confirm("Are you sure you want to delete this application?")) return;
    try {
        await apiFetch(`/applications/${id}`, { method: "DELETE" });
        await fetchApplications();
    } catch (error) {
        showMessage(error.message, true);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("auth-form").addEventListener("submit", submitAuth);
    document.getElementById("logout-button").addEventListener("click", logout);
    document.getElementById("application-form").addEventListener("submit", addApplication);
    document.getElementById("status-filter").addEventListener("change", (event) => {
        renderApplications(applicationsData, event.target.value);
    });
    checkSession();
});
