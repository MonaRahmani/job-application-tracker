const API_URL = "http://127.0.0.1:5000/api/applications";

const VALID_STATUSES = ["Applied", "Interview", "Offer", "Rejected"];

let applicationsData = [];

async function fetchApplications() {
    try {
        const res = await fetch(API_URL);
        if (!res.ok) {
            throw new Error(`GET failed: ${res.status} ${res.statusText}`);
        }
        applicationsData = await res.json();
        const filterEl = document.getElementById("status-filter");
        const filterStatus = filterEl ? filterEl.value : "All";
        renderApplications(applicationsData, filterStatus);
    } catch (err) {
        console.log(err);
    }
}

function renderApplications(applications, filterStatus = "All") {
    const tbody = document.getElementById("applications-body");
    tbody.innerHTML = "";

    let list = applications;
    if (filterStatus !== "All") {
        list = applications.filter((a) => a.status === filterStatus);
    }

    for (const app of list) {
        const tr = document.createElement("tr");

        const companyTd = document.createElement("td");
        companyTd.textContent = app.company ?? "";
        tr.appendChild(companyTd);

        const positionTd = document.createElement("td");
        positionTd.textContent = app.position ?? "";
        tr.appendChild(positionTd);

        const dateTd = document.createElement("td");
        dateTd.textContent = app.date_applied ?? "";
        tr.appendChild(dateTd);

        const statusTd = document.createElement("td");
        statusTd.textContent = app.status ?? "";
        tr.appendChild(statusTd);

        const notesTd = document.createElement("td");
        notesTd.textContent = app.notes ?? "";
        tr.appendChild(notesTd);

        const actionsTd = document.createElement("td");

        const editBtn = document.createElement("button");
        editBtn.type = "button";
        editBtn.textContent = "Edit Status";
        editBtn.addEventListener("click", () =>
            updateStatus(app.id, app.status)
        );

        const deleteBtn = document.createElement("button");
        deleteBtn.type = "button";
        deleteBtn.textContent = "Delete";
        deleteBtn.addEventListener("click", () => deleteApplication(app.id));

        actionsTd.appendChild(editBtn);
        actionsTd.appendChild(deleteBtn);
        tr.appendChild(actionsTd);

        tbody.appendChild(tr);
    }
}

async function addApplication(event) {
    event.preventDefault();
    try {
        const company = document.getElementById("company").value.trim();
        const position = document.getElementById("position").value.trim();
        const dateApplied = document.getElementById("date-applied").value;
        const status = document.getElementById("status").value;
        const notesRaw = document.getElementById("notes").value.trim();

        const payload = {
            company,
            position,
            status,
        };
        if (dateApplied) {
            payload.date_applied = dateApplied;
        }
        if (notesRaw) {
            payload.notes = notesRaw;
        }

        const res = await fetch(API_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        if (!res.ok) {
            const body = await res.json().catch(() => ({}));
            throw new Error(body.error || `${res.status} ${res.statusText}`);
        }

        document.getElementById("application-form").reset();
        await fetchApplications();
    } catch (err) {
        console.log(err);
    }
}

async function updateStatus(id, currentStatus) {
    try {
        const input = prompt(
            `Enter new status (current: ${currentStatus}):`,
            currentStatus
        );
        if (input === null) {
            return;
        }
        const newStatus = input.trim();
        if (!VALID_STATUSES.includes(newStatus)) {
            console.log("Invalid status:", newStatus);
            return;
        }

        const res = await fetch(`${API_URL}/${id}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status: newStatus }),
        });

        if (!res.ok) {
            const body = await res.json().catch(() => ({}));
            throw new Error(body.error || `${res.status} ${res.statusText}`);
        }

        await fetchApplications();
    } catch (err) {
        console.log(err);
    }
}

async function deleteApplication(id) {
    try {
        if (!confirm("Are you sure you want to delete this application?")) {
            return;
        }

        const res = await fetch(`${API_URL}/${id}`, {
            method: "DELETE",
        });

        if (!res.ok) {
            const body = await res.json().catch(() => ({}));
            throw new Error(body.error || `${res.status} ${res.statusText}`);
        }

        await fetchApplications();
    } catch (err) {
        console.log(err);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("application-form");
    const statusFilter = document.getElementById("status-filter");

    form.addEventListener("submit", addApplication);
    statusFilter.addEventListener("change", () => {
        renderApplications(applicationsData, statusFilter.value);
    });

    fetchApplications();
});
