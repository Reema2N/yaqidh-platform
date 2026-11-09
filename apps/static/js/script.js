// Global State
// Page data (incidents, alerts, charts) is rendered by the Django templates
// and refreshed from /dashboard/api/live/; this file only adds UI behaviour.
let cameras = [];

let currentCameraFilter = 'all';
let selectedCameraId = null;

// Live frames: show a "waiting" state instead of a broken image when the
// detection pipeline has not produced a frame yet. ('error' does not bubble,
// so we listen in the capture phase.)
document.addEventListener('error', function (event) {
    const img = event.target;
    if (img && img.classList && img.classList.contains('live-feed-img')) {
        const holder = img.closest('.feed-placeholder');
        if (holder) holder.classList.add('no-signal');
    }
}, true);

document.addEventListener('load', function (event) {
    const img = event.target;
    if (img && img.classList && img.classList.contains('live-feed-img')) {
        const holder = img.closest('.feed-placeholder');
        if (holder) holder.classList.remove('no-signal');
    }
}, true);

// Initialize
document.addEventListener('DOMContentLoaded', function () {
    initializeTime();
    initializePasswordToggle();
    initializeDashboard();
    initializeLiveMonitoring();
    initializeReports();
    initializeUsers();
});

// Password Toggle
function initializePasswordToggle() {
    const togglePassword = document.querySelector('.toggle-password');
    const passwordInput = document.getElementById('password');

    if (!togglePassword || !passwordInput) return;

    togglePassword.addEventListener('click', function () {
        const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
        passwordInput.setAttribute('type', type);

        const icon = this.querySelector('i');
        if (icon) {
            icon.classList.toggle('fa-eye');
            icon.classList.toggle('fa-eye-slash');
        }
    });
}

// Time and Date
function initializeTime() {
    function updateTime() {
        const now = new Date();
        const timeElement = document.getElementById('current-time');
        const dateElement = document.getElementById('current-date');

        if (timeElement) {
            timeElement.textContent = now.toLocaleTimeString();
        }

        if (dateElement) {
            dateElement.textContent = now.toLocaleDateString('en-US', {
                weekday: 'long',
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });
        }
    }

    updateTime();
    setInterval(updateTime, 1000);
}

// Dashboard
function initializeDashboard() {
    // Alerts are rendered server-side and refreshed by fetchDashboardData()
    // in dashboard.html, so there is nothing to draw here.
}

// Live Monitoring
function initializeLiveMonitoring() {
    const grid = document.getElementById('live-cameras-grid');
    if (!grid) return;

    const filterSelect = document.getElementById('camera-filter');
    const cameraCards = document.querySelectorAll('.live-camera-card');

    if (filterSelect) {
        filterSelect.addEventListener('change', function () {
            currentCameraFilter = this.value;
            filterLiveCameras();
        });
    }

    cameraCards.forEach(card => {
        card.addEventListener('click', function () {
            openCameraModalFromCard(this);
        });
    });

    createCameraModal();
}

function filterLiveCameras() {
    const cameraCards = document.querySelectorAll('.live-camera-card');
    const grid = document.getElementById('live-cameras-grid');

    if (!grid) return;

    let visibleCount = 0;

    cameraCards.forEach(card => {
        let shouldShow = true;

        if (currentCameraFilter === 'alert') {
            shouldShow = card.classList.contains('alert');
        }

        card.style.display = shouldShow ? '' : 'none';

        if (shouldShow) {
            visibleCount++;
        }
    });

    let noAlertsMessage = document.getElementById('no-alerts-message');

    if (visibleCount === 0 && currentCameraFilter === 'alert') {
        if (!noAlertsMessage) {
            noAlertsMessage = document.createElement('div');
            noAlertsMessage.id = 'no-alerts-message';
            noAlertsMessage.className = 'card';
            noAlertsMessage.style.textAlign = 'center';
            noAlertsMessage.style.padding = '60px';
            noAlertsMessage.style.color = '#94a3b8';
            noAlertsMessage.style.gridColumn = '1 / -1';

            noAlertsMessage.innerHTML = `
                <i class="fas fa-shield-alt" style="font-size:64px; margin-bottom:20px; color:#22c55e;"></i>
                <h2 style="margin-bottom:10px; color:white;">No Active Alerts</h2>
                <p>There are currently no violence alerts detected.</p>
            `;

            grid.appendChild(noAlertsMessage);
        }
    } else {
        if (noAlertsMessage) {
            noAlertsMessage.remove();
        }
    }
}

function createCameraModal() {
    if (document.getElementById('camera-modal')) return;

    const modal = document.createElement('div');
    modal.id = 'camera-modal';
    modal.className = 'modal';

    modal.innerHTML = `
        <div class="modal-content" style="max-width: 1200px;">
            <div class="camera-video" style="aspect-ratio: 16/9; background: #020617; position: relative;">
                <div class="feed-placeholder">
                    <i class="fas fa-camera" style="font-size: 96px; color: #334155;"></i>
                    <p id="modal-camera-name" style="font-size: 24px; color: #94a3b8;"></p>
                    <div class="live-indicator" style="margin-top: 20px;">
                        <span class="pulse"></span>
                        <span>LIVE</span>
                    </div>
                </div>
                <div id="modal-alert-overlay"></div>
            </div>

            <div style="padding: 1.5rem; border-top: 1px solid #1e293b;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h3 id="modal-camera-title" style="font-size: 24px; color: white; margin-bottom: 8px;"></h3>
                        <p id="modal-camera-location" style="color: #94a3b8;"></p>
                    </div>

                    <button class="btn-primary" id="close-camera-modal-btn">
                        <i class="fas fa-times"></i> Close
                    </button>
                </div>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    modal.addEventListener('click', function (e) {
        if (e.target === modal) {
            closeCameraModal();
        }
    });

    document.getElementById('close-camera-modal-btn').addEventListener('click', closeCameraModal);
}

function openCameraModalFromCard(card) {
    const modal = document.getElementById('camera-modal');
    const cameraName = document.getElementById('modal-camera-name');
    const cameraTitle = document.getElementById('modal-camera-title');
    const cameraLocation = document.getElementById('modal-camera-location');
    const alertOverlay = document.getElementById('modal-alert-overlay');

    if (!modal || !cameraName || !cameraTitle || !cameraLocation || !alertOverlay) return;

    const id = card.dataset.cameraId || 'Camera';
    const title = card.querySelector('.camera-info h3')?.textContent || 'Camera';
    const location = card.querySelector('.camera-info p')?.textContent || '';

    cameraName.textContent = id;
    cameraTitle.textContent = title;
    cameraLocation.textContent = location;

    if (card.classList.contains('alert')) {
        alertOverlay.innerHTML = `
            <div class="alert-overlay">
                <div class="alert-banner" style="font-size: 16px; padding: 16px 24px;">
                    <div>
                        <i class="fas fa-exclamation-triangle"></i>
                        VIOLENCE DETECTED
                    </div>
                    <span>Alert Active</span>
                </div>
            </div>
        `;
    } else {
        alertOverlay.innerHTML = '';
    }

    modal.classList.add('active');
}

function closeCameraModal() {
    const modal = document.getElementById('camera-modal');
    if (modal) {
        modal.classList.remove('active');
    }
}



// Reports Page
function initializeReports() {
    // Charts are drawn in reports.html from real database aggregates.
}

// Users Page
let editingUserId = null;

function initializeUsers() {
    const addUserBtn = document.getElementById('add-user-btn');
    const userSearch = document.getElementById('user-search');
    const modal = document.getElementById('user-modal');
    const cancelBtn = document.getElementById('cancel-user-btn');
    const saveBtn = document.getElementById('save-user-btn');
    const userForm = document.getElementById('user-form');
    const modalTitle = document.getElementById('modal-title');

    if (!addUserBtn || !userSearch || !modal || !cancelBtn || !saveBtn || !userForm) return;

    addUserBtn.addEventListener('click', () => {
        editingUserId = null;
        userForm.reset();
        if (modalTitle) modalTitle.textContent = 'Add New User';
        saveBtn.textContent = 'Save User';
        modal.classList.add('active');
    });

    cancelBtn.addEventListener('click', () => {
        modal.classList.remove('active');
        userForm.reset();
        editingUserId = null;
        if (modalTitle) modalTitle.textContent = 'Add New User';
        saveBtn.textContent = 'Save User';
    });

    saveBtn.addEventListener('click', function(e) {
        e.preventDefault();
        saveUser();
    });

    userForm.addEventListener('submit', function(e) {
        e.preventDefault();
        saveUser();
    });

    const editButtons = document.querySelectorAll('.edit-user-btn');
    editButtons.forEach(button => {
        button.addEventListener('click', function () {
            editingUserId = this.dataset.userId;

            document.getElementById('user-name').value = this.dataset.fullName || '';
            document.getElementById('user-email').value = this.dataset.email || '';
            document.getElementById('user-phone').value = this.dataset.phone || '';
            document.getElementById('user-role').value = (this.dataset.role || '').toLowerCase();
            document.getElementById('user-status').value = (this.dataset.status || '').toLowerCase();

            if (modalTitle) modalTitle.textContent = 'Edit User';
            saveBtn.textContent = 'Update User';
            modal.classList.add('active');
        });
    });

    userSearch.addEventListener('input', filterUsersTable);

    modal.addEventListener('click', function (e) {
        if (e.target === modal) {
            modal.classList.remove('active');
            userForm.reset();
            editingUserId = null;
            if (modalTitle) modalTitle.textContent = 'Add New User';
            saveBtn.textContent = 'Save User';
        }
    });
}

function filterUsersTable() {
    const searchInput = document.getElementById('user-search');
    const rows = document.querySelectorAll('.data-table tbody tr');

    if (!searchInput || rows.length === 0) return;

    const searchTerm = searchInput.value.toLowerCase().trim();

    rows.forEach(row => {
        const rowText = row.textContent.toLowerCase();
        row.style.display = rowText.includes(searchTerm) ? '' : 'none';
    });
}

function saveUser() {
    const nameInput = document.getElementById('user-name');
    const emailInput = document.getElementById('user-email');
    const phoneInput = document.getElementById('user-phone');
    const roleInput = document.getElementById('user-role');
    const statusInput = document.getElementById('user-status');
    const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
    const saveBtn = document.getElementById('save-user-btn');
    const modal = document.getElementById('user-modal');
    const userForm = document.getElementById('user-form');

    if (!nameInput || !emailInput || !phoneInput || !roleInput || !statusInput || !csrfInput || !saveBtn) {
        alert('Form elements are missing.');
        return;
    }

    const full_name = nameInput.value.trim();
    const email = emailInput.value.trim();
    const phone = phoneInput.value.trim();
    const role = roleInput.value.trim().toLowerCase();
    const status = statusInput.value.trim().toLowerCase();
    const csrfToken = csrfInput.value;

    if (!full_name || !email || !phone || !role || !status) {
        alert('Please fill in all required fields');
        return;
    }

    saveBtn.disabled = true;
    saveBtn.textContent = editingUserId ? 'Updating...' : 'Saving...';

    const url = editingUserId ? `/users/update/${editingUserId}/` : '/users/add/';

    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify({
            full_name: full_name,
            email: email,
            phone: phone,
            role: role,
            status: status
        })
    })
    .then(async response => {
        const data = await response.json();
        return { status: response.status, ok: response.ok, data: data };
    })
    .then(result => {
        if (result.ok && result.data.success) {
            alert(editingUserId ? 'User updated successfully' : 'User added successfully');
            if (modal) modal.classList.remove('active');
            if (userForm) userForm.reset();
            editingUserId = null;
            location.reload();
        } else {
            alert(result.data.error || `Failed to save user (HTTP ${result.status})`);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Something went wrong while saving the user');
    })
    .finally(() => {
        saveBtn.disabled = false;
        saveBtn.textContent = editingUserId ? 'Update User' : 'Save User';
    });
}

// Delete User
document.querySelectorAll(".delete-user-btn").forEach(btn => {
    btn.addEventListener("click", function () {
        const userId = this.dataset.userId;
        const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');

        if (!csrfInput) {
            alert("CSRF token not found");
            return;
        }

        if (!confirm("Are you sure you want to delete this user?")) {
            return;
        }

        fetch("/users/delete/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfInput.value,
                "X-Requested-With": "XMLHttpRequest"
            },
            body: JSON.stringify({
                user_id: userId
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                location.reload();
            } else {
                alert(data.error || "Failed to delete user");
            }
        })
        .catch(error => {
            console.error("Delete error:", error);
            alert("Something went wrong while deleting the user");
        });
    });
});