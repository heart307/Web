// 全局变量
let socket = null;
let currentUser = null;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

// 初始化应用
function initializeApp() {
    // 初始化WebSocket连接
    initializeSocket();
    
    // 加载用户信息
    loadUserProfile();
    
    // 绑定全局事件
    bindGlobalEvents();
    
    console.log('FTP Web System initialized');
}

// 初始化WebSocket连接
function initializeSocket() {
    socket = io();
    
    socket.on('connect', function() {
        console.log('WebSocket connected');
        showToast('success', '实时连接已建立');
    });
    
    socket.on('disconnect', function() {
        console.log('WebSocket disconnected');
        showToast('warning', '实时连接已断开');
    });
    
    socket.on('task_stats_update', function(data) {
        updateTaskStats(data);
    });
    
    socket.on('system_status_update', function(data) {
        updateSystemStatus(data);
    });
    
    // 订阅更新
    socket.emit('subscribe_task_updates');
    socket.emit('subscribe_system_status');
}

// 加载用户信息
async function loadUserProfile() {
    try {
        const response = await fetch('/profile');
        if (response.ok) {
            const data = await response.json();
            currentUser = data.user;
            updateUserDisplay();
        }
    } catch (error) {
        console.error('Failed to load user profile:', error);
    }
}

// 更新用户显示
function updateUserDisplay() {
    if (currentUser) {
        const usernameElement = document.getElementById('username');
        if (usernameElement) {
            usernameElement.textContent = currentUser.username;
        }
    }
}

// 绑定全局事件
function bindGlobalEvents() {
    // 表单提交防止重复
    document.addEventListener('submit', function(e) {
        const submitBtn = e.target.querySelector('button[type="submit"]');
        if (submitBtn && !submitBtn.disabled) {
            submitBtn.disabled = true;
            setTimeout(() => {
                submitBtn.disabled = false;
            }, 2000);
        }
    });
    
    // 模态框显示时加载数据
    document.addEventListener('show.bs.modal', function(e) {
        const modalId = e.target.id;
        switch (modalId) {
            case 'createTaskModal':
                loadSitesForSelect('siteId');
                break;
            case 'addSiteModal':
                resetForm('addSiteForm');
                break;
            case 'createMonitorModal':
                loadSitesForSelect('monitorSiteId');
                resetForm('createMonitorForm');
                break;
            case 'profileModal':
                loadProfileData();
                break;
            case 'logsModal':
                document.getElementById('logDate').value = new Date().toISOString().split('T')[0];
                break;
        }
    });
}

// 显示Toast消息
function showToast(type, message, title = '系统消息') {
    const toast = document.getElementById('toast');
    const toastBody = document.getElementById('toast-body');
    const toastHeader = toast.querySelector('.toast-header strong');
    const toastIcon = toast.querySelector('.toast-header i');
    
    // 设置图标和颜色
    const iconMap = {
        'success': 'bi-check-circle text-success',
        'error': 'bi-exclamation-triangle text-danger',
        'warning': 'bi-exclamation-triangle text-warning',
        'info': 'bi-info-circle text-info'
    };
    
    toastIcon.className = `${iconMap[type] || iconMap.info} me-2`;
    toastHeader.textContent = title;
    toastBody.textContent = message;
    
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
}

// API请求封装
async function apiRequest(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
        ...options
    };
    
    try {
        const response = await fetch(url, defaultOptions);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || `HTTP ${response.status}`);
        }
        
        return data;
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}

// 加载站点列表到选择框
async function loadSitesForSelect(selectId) {
    try {
        const data = await apiRequest('/sites/api/sites');
        const select = document.getElementById(selectId);
        
        // 清空现有选项
        select.innerHTML = '<option value="">请选择FTP站点</option>';
        
        // 添加站点选项
        data.sites.forEach(site => {
            const option = document.createElement('option');
            option.value = site.id;
            option.textContent = `${site.name} (${site.host})`;
            select.appendChild(option);
        });
    } catch (error) {
        showToast('error', '加载站点列表失败: ' + error.message);
    }
}

// 重置表单
function resetForm(formId) {
    const form = document.getElementById(formId);
    if (form) {
        form.reset();
    }
}

// 格式化日期时间
function formatDateTime(dateString) {
    if (!dateString) return '-';
    
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

// 格式化文件大小
function formatFileSize(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 格式化持续时间
function formatDuration(seconds) {
    if (!seconds || seconds < 0) return '-';
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
        return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    } else {
        return `${minutes}:${secs.toString().padStart(2, '0')}`;
    }
}

// 获取状态标签HTML
function getStatusBadge(status) {
    const statusMap = {
        'pending': { class: 'status-pending', text: '等待中', icon: 'bi-clock' },
        'running': { class: 'status-running', text: '运行中', icon: 'bi-play-circle' },
        'completed': { class: 'status-completed', text: '已完成', icon: 'bi-check-circle' },
        'failed': { class: 'status-failed', text: '失败', icon: 'bi-x-circle' },
        'paused': { class: 'status-paused', text: '已暂停', icon: 'bi-pause-circle' }
    };
    
    const statusInfo = statusMap[status] || { class: 'status-pending', text: status, icon: 'bi-question-circle' };
    
    return `<span class="status-badge ${statusInfo.class}">
        <i class="${statusInfo.icon} me-1"></i>${statusInfo.text}
    </span>`;
}

// 获取优先级标签HTML
function getPriorityBadge(priority) {
    const priorityMap = {
        'high': { class: 'priority-high', text: '高' },
        'medium': { class: 'priority-medium', text: '中' },
        'low': { class: 'priority-low', text: '低' }
    };
    
    const priorityInfo = priorityMap[priority] || { class: 'priority-medium', text: priority };
    
    return `<span class="${priorityInfo.class}">${priorityInfo.text}</span>`;
}

// 获取连接状态HTML
function getConnectionStatus(status) {
    const statusMap = {
        'connected': { class: 'connection-connected', text: '已连接', icon: 'bi-wifi' },
        'disconnected': { class: 'connection-disconnected', text: '已断开', icon: 'bi-wifi-off' },
        'unknown': { class: 'connection-unknown', text: '未知', icon: 'bi-question-circle' }
    };
    
    const statusInfo = statusMap[status] || statusMap.unknown;
    
    return `<span class="connection-status ${statusInfo.class}">
        <i class="${statusInfo.icon}"></i> ${statusInfo.text}
    </span>`;
}

// 创建进度条HTML
function createProgressBar(progress, showText = true) {
    const percentage = Math.round(progress || 0);
    const progressText = showText ? `${percentage}%` : '';
    
    return `
        <div class="progress" style="height: 20px;">
            <div class="progress-bar" role="progressbar" 
                 style="width: ${percentage}%" 
                 aria-valuenow="${percentage}" 
                 aria-valuemin="0" 
                 aria-valuemax="100">
                ${progressText}
            </div>
        </div>
    `;
}

// 确认对话框
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// 用户登出
async function logout() {
    try {
        await apiRequest('/logout', { method: 'POST' });
        window.location.href = '/login';
    } catch (error) {
        showToast('error', '登出失败: ' + error.message);
    }
}

// 模态框显示函数
function showCreateTaskModal() {
    const modal = new bootstrap.Modal(document.getElementById('createTaskModal'));
    modal.show();
}

function showAddSiteModal() {
    const modal = new bootstrap.Modal(document.getElementById('addSiteModal'));
    modal.show();
}

function showCreateMonitorModal() {
    const modal = new bootstrap.Modal(document.getElementById('createMonitorModal'));
    modal.show();
}

function showLogsModal() {
    const modal = new bootstrap.Modal(document.getElementById('logsModal'));
    modal.show();
}

function showProfileModal() {
    const modal = new bootstrap.Modal(document.getElementById('profileModal'));
    modal.show();
}

function showSettingsModal() {
    showToast('info', '系统设置功能开发中...');
}

function showMonitorModal() {
    showToast('info', '监控管理功能开发中...');
}

// 更新任务统计信息（由WebSocket调用）
function updateTaskStats(stats) {
    // 这个函数会在dashboard.js中被重写
    console.log('Task stats updated:', stats);
}

// 更新系统状态（由WebSocket调用）
function updateSystemStatus(status) {
    // 这个函数会在dashboard.js中被重写
    console.log('System status updated:', status);
}
