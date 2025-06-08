// API Configuration
const API_BASE_URL = 'http://localhost:5000/api';

// Global state
let currentEmails = [];
let currentFilter = 'all';
let userPreferences = null;

// API Functions
async function fetchEmails(filter = 'all') {
    try {
        const response = await fetch(`${API_BASE_URL}/emails?filter=${filter}`);
        if (!response.ok) throw new Error('Failed to fetch emails');
        return await response.json();
    } catch (error) {
        console.error('Error fetching emails:', error);
        return [];
    }
}

async function fetchEmailDetails(emailId) {
    try {
        const response = await fetch(`${API_BASE_URL}/emails/${emailId}`);
        if (!response.ok) throw new Error('Failed to fetch email details');
        return await response.json();
    } catch (error) {
        console.error('Error fetching email details:', error);
        return null;
    }
}

async function sendEmailReply(emailId, replyContent) {
    try {
        const response = await fetch(`${API_BASE_URL}/emails/${emailId}/reply`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ reply: replyContent })
        });
        if (!response.ok) throw new Error('Failed to send reply');
        return await response.json();
    } catch (error) {
        console.error('Error sending reply:', error);
        throw error;
    }
}

async function saveUserPreferences(preferences) {
    try {
        const response = await fetch(`${API_BASE_URL}/user/preferences`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(preferences)
        });
        if (!response.ok) throw new Error('Failed to save preferences');
        return await response.json();
    } catch (error) {
        console.error('Error saving preferences:', error);
        throw error;
    }
}

async function loadUserPreferences() {
    try {
        const response = await fetch(`${API_BASE_URL}/user/preferences`);
        if (!response.ok) throw new Error('Failed to load preferences');
        return await response.json();
    } catch (error) {
        console.error('Error loading preferences:', error);
        return {};
    }
}

async function fetchStats() {
    try {
        const response = await fetch(`${API_BASE_URL}/stats`);
        if (!response.ok) throw new Error('Failed to fetch stats');
        return await response.json();
    } catch (error) {
        console.error('Error fetching stats:', error);
        return {};
    }
}

// Utility Functions
function showLoading(containerId) {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = '<div class="loading">Loading...</div>';
    }
}

function showError(containerId, message) {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `<div class="error">Error: ${message}</div>`;
    }
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
}

function mapBackendTagsToFrontend(tags) {
    // Map backend tags to frontend filter categories
    const tagMap = {
        'urgent': 'urgent',
        'high_priority': 'high-priority',
        'low_priority': 'low-priority',
        'meeting': 'meeting',
        'issue': 'issue'
    };
    
    return tags.map(tag => tagMap[tag] || tag);
}

// Update the existing showHome function to include task stats
async function showHome() {
    // Hide all sections
    document.querySelectorAll('.email-section').forEach(section => {
        section.classList.remove('active');
    });
    document.getElementById('home').style.display = 'flex';
    
    // Update nav
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    
    // Load stats for home page
    await loadDashboardStats();
    await updateTaskStats();
}

async function loadDashboardStats() {
    try {
        const stats = await fetchStats();
        // Update dashboard with stats if you have elements for them
        console.log('Dashboard stats:', stats);
    } catch (error) {
        console.error('Failed to load dashboard stats:', error);
    }
}

function getStarted() {
    // Hide home screen
    document.getElementById('home').style.display = 'none';
    // Show setup screen
    document.getElementById('setup').classList.add('active');
    
    // Load existing preferences if any
    loadExistingPreferences();
}

async function loadExistingPreferences() {
    try {
        userPreferences = await loadUserPreferences();
        if (userPreferences.workSummary) {
            document.getElementById('workSummary').value = userPreferences.workSummary;
        }
        if (userPreferences.urgentEmails) {
            document.getElementById('urgentEmails').value = userPreferences.urgentEmails;
        }
        if (userPreferences.highPriorityEmails) {
            document.getElementById('highPriorityEmails').value = userPreferences.highPriorityEmails;
        }
    } catch (error) {
        console.error('Failed to load existing preferences:', error);
    }
}

function skipSetup() {
    // Hide setup screen and show all emails
    document.getElementById('setup').classList.remove('active');
    showEmails('all');
}

async function completeSetup() {
    // Get form values
    const workSummary = document.getElementById('workSummary').value.trim();
    const urgentEmails = document.getElementById('urgentEmails').value.trim();
    const highPriorityEmails = document.getElementById('highPriorityEmails').value.trim();

    // Basic validation
    if (!workSummary || !urgentEmails || !highPriorityEmails) {
        alert('Please fill in all fields to personalize your experience, or click "Skip for Now".');
        return;
    }

    try {
        // Save preferences to backend
        await saveUserPreferences({
            workSummary,
            urgentEmails,
            highPriorityEmails
        });

        // Show success message
        alert('Your preferences have been saved! MinimalizEmail will now better understand your priorities.');

        // Hide setup screen and show all emails
        document.getElementById('setup').classList.remove('active');
        showEmails('all');
    } catch (error) {
        alert('Failed to save preferences. Please try again.');
        console.error('Setup completion error:', error);
    }
}

async function showEmails(filter) {
    // Hide home screen
    document.getElementById('home').style.display = 'none';
    
    // Hide all email sections
    document.querySelectorAll('.email-section').forEach(section => {
        section.classList.remove('active');
    });
    
    // Show selected section
    const section = document.getElementById(`${filter}-emails`);
    if (section) {
        section.classList.add('active');
    }
    
    // Update nav
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    if (event?.target) {
        event.target.classList.add('active');
    }
    
    currentFilter = filter;
    await loadEmails(filter);
}

async function loadEmails(filter) {
    const gridId = `${filter}-emails-grid`;
    const grid = document.getElementById(gridId);
    
    if (!grid) {
        console.error(`Grid element not found: ${gridId}`);
        return;
    }
    
    // Show loading state
    showLoading(gridId);
    
    try {
        // Fetch emails from backend
        const emails = await fetchEmails(filter);
        currentEmails = emails;
        
        // Generate email cards
        if (emails.length === 0) {
            grid.innerHTML = '<div class="loading">No emails found in this category.</div>';
            return;
        }

        grid.innerHTML = emails.map(email => {
            const frontendTags = mapBackendTagsToFrontend(email.tags || []);
            return `
                <div class="email-card" onclick="openEmailDetail(${email.id})">
                    <div class="email-header">
                        <div class="email-from">${email.from}</div>
                        <div class="email-date">${formatDate(email.received_at)}</div>
                    </div>
                    <div class="email-subject">${email.subject}</div>
                    <div class="email-summary">${email.ai_summary || 'Processing...'}</div>
                    <div class="email-tags">
                        ${frontendTags.map(tag => `<span class="tag ${tag}">${tag.replace('-', ' ')}</span>`).join('')}
                    </div>
                </div>
            `;
        }).join('');
    } catch (error) {
        showError(gridId, 'Failed to load emails. Please try again.');
        console.error('Error loading emails:', error);
    }
}

async function openEmailDetail(emailId) {
    try {
        // Show loading in modal
        document.getElementById('modalSubject').textContent = 'Loading...';
        document.getElementById('modalFrom').textContent = '';
        document.getElementById('modalBody').textContent = 'Loading email details...';
        document.getElementById('modalTags').innerHTML = '';
        document.getElementById('modalActions').innerHTML = '';
        document.getElementById('replyText').value = '';
        
        // Show modal
        document.getElementById('emailModal').classList.add('active');
        
        // Fetch email details
        const email = await fetchEmailDetails(emailId);
        if (!email) {
            alert('Failed to load email details');
            closeModal();
            return;
        }

        // Populate modal content
        document.getElementById('modalSubject').textContent = email.subject;
        document.getElementById('modalFrom').textContent = email.from;
        document.getElementById('modalBody').innerHTML = email.body || email.text_body || 'No content';        
        const frontendTags = mapBackendTagsToFrontend(email.tags || []);
        document.getElementById('modalTags').innerHTML = 
            frontendTags.map(tag => `<span class="tag ${tag}">${tag.replace('-', ' ')}</span>`).join('');
        
        // Generate action boxes
        let actionsHtml = '';
        
        // JIRA ticket info
        if (email.jira_ticket && email.jira_ticket.ticket_id) {
            actionsHtml += `
                <div class="action-box">
                    <div class="detail-title">JIRA Ticket Created</div>
                    <div class="detail-content">
                        Ticket ID: <strong>${email.jira_ticket.ticket_id}</strong><br>
                        Status: <strong>${email.jira_ticket.status}</strong><br>
                        <a href="${email.jira_ticket.url}" target="_blank" style="color: #4488ff;">View Ticket</a>
                    </div>
                </div>
            `;
        }
        
        // Calendar event info
        if (email.calendar_event && email.calendar_event.title) {
            console.log('Calendar event:', email.calendar_event.calendar_link);

            actionsHtml += `
                <div class="action-box">
                    <div class="detail-title">Meeting Scheduled</div>
                    <div class="detail-content">
                        <strong>Topic:</strong> ${email.calendar_event.title}<br>
                        <strong>Time:</strong> ${formatDate(email.calendar_event.start_time)}<br>
                        ${email.calendar_event.attendees ? `<strong>Attendees:</strong> ${email.calendar_event.attendees.join(', ')}<br>` : ''}
                        ${email.calendar_event.meet_link ? `<strong>Meet Link:</strong> <a href="${email.calendar_event.meet_link}" target="_blank" style="color: #4488ff;">Join Meeting</a><br>` : ''}
                        ${email.calendar_event.calendar_link ? `<a href="${email.calendar_event.calendar_link}" target="_blank" style="color: #4488ff;">View in Calendar</a>` : ''}
                        
                    </div>
                </div>
            `;
        }
        
        // Processing status
        if (!email.is_processed) {
            actionsHtml += `
                <div class="action-box">
                    <div class="detail-title">Processing Status</div>
                    <div class="detail-content">This email is still being processed...</div>
                </div>
            `;
        } else if (email.processing_error) {
            actionsHtml += `
                <div class="action-box">
                    <div class="detail-title">Processing Error</div>
                    <div class="detail-content">Error: ${email.processing_error}</div>
                </div>
            `;
        }
        
        document.getElementById('modalActions').innerHTML = actionsHtml;
        document.getElementById('replyText').value = email.ai_reply || '';
        
        // Store current email ID for reply
        document.getElementById('emailModal').dataset.emailId = emailId;
        
    } catch (error) {
        console.error('Error opening email detail:', error);
        alert('Failed to load email details');
        closeModal();
    }
}

function closeModal() {
    document.getElementById('emailModal').classList.remove('active');
}

async function sendReply() {
    const replyText = document.getElementById('replyText').value;
    if (!replyText.trim()) {
        alert('Please enter a reply message.');
        return;
    }
    
    const emailId = document.getElementById('emailModal').dataset.emailId;
    if (!emailId) {
        alert('Email ID not found.');
        return;
    }
    
    try {
        // Show loading state
        const sendButton = document.querySelector('#emailModal button[onclick="sendReply()"]');
        const originalText = sendButton.textContent;
        sendButton.textContent = 'Sending...';
        sendButton.disabled = true;
        
        await sendEmailReply(parseInt(emailId), replyText);
        
        alert('Reply sent successfully!');
        closeModal();
        
        // Reset button
        sendButton.textContent = originalText;
        sendButton.disabled = false;
        
    } catch (error) {
        alert('Failed to send reply. Please try again.');
        console.error('Reply send error:', error);
        
        // Reset button
        const sendButton = document.querySelector('#emailModal button[onclick="sendReply()"]');
        sendButton.textContent = 'Send Reply';
        sendButton.disabled = false;
    }
}

// Auto-refresh emails every 30 seconds
let refreshInterval;

// Update auto-refresh to include tasks
function startAutoRefresh() {
    refreshInterval = setInterval(() => {
        if (currentFilter && document.querySelector('.email-section.active')) {
            loadEmails(currentFilter);
        } else if (document.getElementById('tasks-section')?.classList.contains('active')) {
            loadTasks(taskFilter);
        }
    }, 30000); // 30 seconds
}


function stopAutoRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // Existing initialization
    showHome();
    startAutoRefresh();

    // Task modal event listeners
    const addTaskModal = document.getElementById('addTaskModal');
    if (addTaskModal) {
        addTaskModal.addEventListener('click', function(e) {
            if (e.target === this) {
                closeAddTaskModal();
            }
        });
    }

    // Close modal when clicking outside
    document.getElementById('emailModal').addEventListener('click', function(e) {
        if (e.target === this) {
            closeModal();
        }
    });

    // NEW: Event delegation for task delete buttons
    const tasksContainer = document.getElementById('tasks-container');
    if (tasksContainer) {
        tasksContainer.addEventListener('click', async function(event) {
            // Check if the clicked element, or any of its ancestors, is the delete button
            const deleteButton = event.target.closest('.task-delete-btn');
            if (deleteButton) {
                const taskId = deleteButton.dataset.taskId; // Get the task ID from the data attribute
                if (taskId) {
                    await removeTask(parseInt(taskId)); // Call your removeTask function
                }
            }
        });
    }
});

// Handle page visibility change to pause/resume auto-refresh
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        stopAutoRefresh();
    } else {
        startAutoRefresh();
    }
});

// Global task state
let currentTasks = [];
let taskFilter = 'all';

// Task API Functions
async function fetchTasks(status = 'all', priority = 'all') {
    try {
        const response = await fetch(`${API_BASE_URL}/tasks?status=${status}&priority=${priority}`);
        if (!response.ok) throw new Error('Failed to fetch tasks');
        return await response.json();
    } catch (error) {
        console.error('Error fetching tasks:', error);
        return [];
    }
}

async function toggleTaskStatus(taskId) {
    try {
        const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/toggle`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        if (!response.ok) throw new Error('Failed to toggle task status');
        return await response.json();
    } catch (error) {
        console.error('Error toggling task:', error);
        throw error;
    }
}

async function createTask(taskData) {
    try {
        const response = await fetch(`${API_BASE_URL}/tasks`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(taskData)
        });
        if (!response.ok) throw new Error('Failed to create task');
        return await response.json();
    } catch (error) {
        console.error('Error creating task:', error);
        throw error;
    }
}

async function deleteTask(taskId) {
    try {
        const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`, {
            method: 'DELETE'
        });
        if (!response.ok) throw new Error('Failed to delete task');
        return await response.json();
    } catch (error) {
        console.error('Error deleting task:', error);
        throw error;
    }
}

async function fetchTaskStats() {
    try {
        const response = await fetch(`${API_BASE_URL}/tasks/stats`);
        if (!response.ok) throw new Error('Failed to fetch task stats');
        return await response.json();
    } catch (error) {
        console.error('Error fetching task stats:', error);
        return {};
    }
}

// Task Display Functions
async function showTasks(filter = 'all') {
    // Hide home screen
    document.getElementById('home').style.display = 'none';
    
    // Hide all email sections
    document.querySelectorAll('.email-section').forEach(section => {
        section.classList.remove('active');
    });
    
    // Show tasks section
    const section = document.getElementById('tasks-section');
    if (section) {
        section.classList.add('active');
    }
    
    // Update nav
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    
    // Add active class to tasks nav item
    const tasksNavItem = document.querySelector('.nav-item[onclick*="showTasks"]');
    if (tasksNavItem) {
        tasksNavItem.classList.add('active');
    }
    
    taskFilter = filter;
    await loadTasks(filter);
}

async function loadTasks(filter = 'all') {
    const container = document.getElementById('tasks-container');
    
    if (!container) {
        console.error('Tasks container not found');
        return;
    }
    
    // Show loading state
    container.innerHTML = '<div class="loading">Loading tasks...</div>';
    
    try {
        // Determine status and priority filters
        let status = 'all';
        let priority = 'all';
        
        if (filter === 'pending') status = 'pending';
        else if (filter === 'completed') status = 'completed';
        else if (filter === 'high-priority') priority = 'high';
        
        // Fetch tasks from backend
        const tasks = await fetchTasks(status, priority);
        currentTasks = tasks;
        
        // Update task statistics
        await updateTaskStats();
        
        // Generate task list
        if (tasks.length === 0) {
            container.innerHTML = '<div class="loading">No tasks found.</div>';
            return;
        }

        container.innerHTML = generateTasksHTML(tasks);
    } catch (error) {
        container.innerHTML = '<div class="error">Failed to load tasks. Please try again.</div>';
        console.error('Error loading tasks:', error);
    }
}

function generateTasksHTML(tasks) {
    return tasks.map(task => {
        const isCompleted = task.status === 'completed';
        const priorityClass = task.priority === 'high' ? 'high-priority' :
                             task.priority === 'low' ? 'low-priority' : '';
        const dueDateStr = task.due_date ? new Date(task.due_date).toLocaleDateString() : '';
        const isOverdue = task.due_date && new Date(task.due_date) < new Date() && !isCompleted;

        return `
            <div class="task-item ${isCompleted ? 'completed' : ''} ${priorityClass}" data-task-id="${task.id}">
                <div class="task-checkbox">
                    <input type="checkbox"
                           ${isCompleted ? 'checked' : ''}
                           onchange="toggleTask(${task.id})">
                </div>
                <div class="task-content">
                    <div class="task-title ${isCompleted ? 'strikethrough' : ''}">${task.title}</div>
                    ${task.description ? `<div class="task-description">${task.description}</div>` : ''}
                    <div class="task-meta">
                        ${task.email_subject ? `<span class="task-email">From: ${task.email_subject}</span>` : ''}
                        ${dueDateStr ? `<span class="task-due-date ${isOverdue ? 'overdue' : ''}">Due: ${dueDateStr}</span>` : ''}
                        <span class="task-priority priority-${task.priority}">${task.priority}</span>
                        ${task.completed_at ? `<span class="task-completed">Completed: ${new Date(task.completed_at).toLocaleDateString()}</span>` : ''}
                    </div>
                </div>
                <div class="task-actions">
                    <button class="task-delete-btn" data-task-id="${task.id}" title="Delete task"> 
                        ×
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

async function toggleTask(taskId) {
    try {
        await toggleTaskStatus(taskId);
        // Reload current tasks to reflect the change
        await loadTasks(taskFilter);
    } catch (error) {
        alert('Failed to update task status');
        console.error('Toggle task error:', error);
    }
}

async function removeTask(taskId) {
    if (!confirm('Are you sure you want to delete this task?')) {
        return;
    }
    
    try {
        await deleteTask(taskId);
        await loadTasks(taskFilter);
    } catch (error) {
        alert('Failed to delete task');
        console.error('Delete task error:', error);
    }
}

async function updateTaskStats() {
    try {
        const stats = await fetchTaskStats();
        
        // Update stats display if elements exist
        const pendingCount = document.getElementById('pending-tasks-count');
        const completedCount = document.getElementById('completed-tasks-count');
        const highPriorityCount = document.getElementById('high-priority-tasks-count');
        const overdueCount = document.getElementById('overdue-tasks-count');
        
        if (pendingCount) pendingCount.textContent = stats.pending_tasks || 0;
        if (completedCount) completedCount.textContent = stats.completed_tasks || 0;
        if (highPriorityCount) highPriorityCount.textContent = stats.high_priority_tasks || 0;
        if (overdueCount) overdueCount.textContent = stats.overdue_tasks || 0;
        
    } catch (error) {
        console.error('Error updating task stats:', error);
    }
}

// Task creation modal functions
function showAddTaskModal() {
    document.getElementById('addTaskModal').classList.add('active');
}

function closeAddTaskModal() {
    document.getElementById('addTaskModal').classList.remove('active');
    // Clear form
    document.getElementById('taskTitle').value = '';
    document.getElementById('taskDescription').value = '';
    document.getElementById('taskPriority').value = 'normal';
    document.getElementById('taskDueDate').value = '';
}

async function saveNewTask() {
    const title = document.getElementById('taskTitle').value.trim();
    const description = document.getElementById('taskDescription').value.trim();
    const priority = document.getElementById('taskPriority').value;
    const dueDate = document.getElementById('taskDueDate').value;
    
    if (!title) {
        alert('Please enter a task title');
        return;
    }
    
    try {
        const taskData = {
            title,
            description,
            priority,
            due_date: dueDate || null
        };
        
        await createTask(taskData);
        closeAddTaskModal();
        await loadTasks(taskFilter);
        
    } catch (error) {
        alert('Failed to create task');
        console.error('Create task error:', error);
    }
}




