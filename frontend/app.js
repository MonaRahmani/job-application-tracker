const API_BASE = window.location.protocol === "file:"
    ? "http://127.0.0.1:5000/api"
    : `${window.location.origin}/api`;
const VALID_STATUSES = ["Applied", "Interview", "Offer", "Rejected"];

let applicationsData = [];
let activeMatchApplicationId = null;

async function apiFetch(path, options = {}) {
    const isFormData = options.body instanceof FormData;
    const response = await fetch(`${API_BASE}${path}`, {
        credentials: "include",
        ...options,
        headers: {
            ...(options.body && !isFormData ? { "Content-Type": "application/json" } : {}),
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
        await fetchProfile();
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
        await fetchProfile();
        await fetchApplications();
    } catch (error) {
        showMessage(error.message, true);
    }
}

async function fetchProfile() {
    const response = await apiFetch("/profile");
    const { user } = await response.json();
    const status = document.getElementById("resume-status");
    status.textContent = user.resume_filename
        ? `Current resume: ${user.resume_filename}`
        : "No resume uploaded yet.";
}

async function uploadResume(event) {
    event.preventDefault();
    const input = document.getElementById("resume-file");
    if (!input.files.length) return;
    const formData = new FormData();
    formData.append("resume", input.files[0]);
    try {
        const response = await apiFetch("/profile/resume", { method: "POST", body: formData });
        const { user } = await response.json();
        document.getElementById("resume-status").textContent = `Current resume: ${user.resume_filename}`;
        input.value = "";
        showMessage("Resume uploaded and ready for matching.");
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

        const matchCell = document.createElement("td");
        matchCell.className = "match-cell";
        const score = document.createElement("strong");
        score.className = "match-score";
        score.textContent = application.match_score === null
            ? "Not matched"
            : `${application.match_score}/100`;
        const matchButton = document.createElement("button");
        matchButton.type = "button";
        matchButton.className = "open-match-button";
        matchButton.textContent = "Open Matcher";
        matchButton.addEventListener("click", () => openMatchModal(application));
        matchCell.append(score, matchButton);
        row.appendChild(matchCell);

        const actions = document.createElement("td");
        const editButton = document.createElement("button");
        editButton.type = "button";
        editButton.className = "edit-status-button";
        editButton.textContent = "Edit Status";
        editButton.addEventListener("click", () => updateStatus(application.id, application.status));

        const deleteButton = document.createElement("button");
        deleteButton.type = "button";
        deleteButton.className = "delete-button";
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

function renderMatchDetails(application) {
    document.getElementById("modal-match-score").textContent = application.match_score === null
        ? "Not matched yet"
        : `${application.match_score}/100`;

    const matched = document.getElementById("modal-matched-keywords");
    const missing = document.getElementById("modal-missing-keywords");
    const suggestions = document.getElementById("modal-match-suggestions");
    matched.innerHTML = "";
    missing.innerHTML = "";
    suggestions.innerHTML = "";

    for (const keyword of application.matched_keywords || []) {
        const chip = document.createElement("span");
        chip.className = "keyword-chip matched";
        chip.textContent = keyword;
        matched.appendChild(chip);
    }
    for (const keyword of application.missing_keywords || []) {
        const chip = document.createElement("span");
        chip.className = "keyword-chip missing";
        chip.textContent = keyword;
        missing.appendChild(chip);
    }
    for (const suggestion of application.match_suggestions || []) {
        const item = document.createElement("li");
        item.textContent = suggestion;
        suggestions.appendChild(item);
    }
}

function openMatchModal(application) {
    activeMatchApplicationId = application.id;
    document.getElementById("match-modal-title").textContent = `${application.company} — ${application.position}`;
    document.getElementById("modal-job-description").value = application.job_description || "";
    document.getElementById("modal-match-status").textContent = "";
    renderMatchDetails(application);
    document.getElementById("match-modal").showModal();
}

async function matchApplication(event) {
    event.preventDefault();
    if (activeMatchApplicationId === null) return;
    const button = document.getElementById("run-match-button");
    const status = document.getElementById("modal-match-status");
    const jobDescription = document.getElementById("modal-job-description").value.trim();
    button.disabled = true;
    button.textContent = "Matching…";
    status.textContent = "Analyzing your resume and job description…";
    try {
        const response = await apiFetch(`/applications/${activeMatchApplicationId}/match`, {
            method: "POST",
            body: JSON.stringify({ job_description: jobDescription }),
        });
        const updated = await response.json();
        applicationsData = applicationsData.map((application) =>
            application.id === updated.id ? updated : application
        );
        renderMatchDetails(updated);
        renderApplications(applicationsData, document.getElementById("status-filter").value);
        status.textContent = "Match complete.";
        showMessage("Resume match updated.");
    } catch (error) {
        status.textContent = error.message;
    }
    button.disabled = false;
    button.textContent = "Match Resume";
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
    document.getElementById("resume-form").addEventListener("submit", uploadResume);
    document.getElementById("match-form").addEventListener("submit", matchApplication);
    document.getElementById("close-match-modal").addEventListener("click", () => {
        document.getElementById("match-modal").close();
    });
    document.getElementById("match-modal").addEventListener("click", (event) => {
        if (event.target === event.currentTarget) event.currentTarget.close();
    });
    document.getElementById("status-filter").addEventListener("change", (event) => {
        renderApplications(applicationsData, event.target.value);
    });
    checkSession();
});
