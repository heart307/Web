// 仪表板专用JavaScript

// 页面加载完成后初始化仪表板
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
});

// 初始化仪表板
function initializeDashboard() {
    loadDashboardStats();
    loadRecentTasks();
    loadSystemStatus();
    
    // 设置定时刷新
    setInterval(loadDashboardStats, 30000); // 30秒刷新统计信息
    setInterval(loadSystemStatus, 10000);   // 10秒刷新系统状态
    
    console.log('Dashboard initialized');
}

// 加载仪表板统计信息
async function loadDashboardStats() {
    try {
        const data = await apiRequest('/api/dashboard/stats');
        
        // 更新统计卡片
        updateStatCard('total-tasks', data.tasks.total_tasks);
        updateStatCard('running-tasks', data.tasks.running_tasks);
        updateStatCard('total-sites', data.sites.total_sites);
        updateStatCard('system-efficiency', Math.round(data.scheduler.efficiency || 0) + '%');
        
        console.log('Dashboard stats updated');
    } catch (error) {
        console.error('Failed to load dashboard stats:', error);
        showToast('error', '加载统计信息失败: ' + error.message);
    }
}

// 更新统计卡片
function updateStatCard(elementId, value) {
    const element = document.getElementById(elementId);
    if (element) {
        // 添加更新动画
        element.classList.add('updating');
        
        setTimeout(() => {
            element.textContent = value;
            element.classList.remove('updating');
        }, 200);
    }
}

// 加载最近任务
async function loadRecentTasks() {
    try {
        const data = await apiRequest('/api/dashboard/recent-tasks');
        updateRecentTasksTable(data.tasks);
    } catch (error) {
        console.error('Failed to load recent tasks:', error);
        showToast('error', '加载最近任务失败: ' + error.message);
    }
}

// 更新最近任务表格
function updateRecentTasksTable(tasks) {
    const tbody = document.getElementById('recent-tasks-tbody');
    if (!tbody) return;
    
    if (tasks.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center text-muted">
                    <div class="empty-state">
                        <i class="bi bi-inbox"></i>
                        <p>暂无任务</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = tasks.map(task => `
        <tr>
            <td>
                <span class="text-primary">${getSiteName(task)}</span>
            </td>
            <td>
                <div class="d-flex align-items-center">
                    <i class="bi ${getFileIcon(task)} me-2"></i>
                    <span class="text-truncate" style="max-width: 150px;" title="${getRemotePath(task)}">
                        ${getRemotePath(task)}
                    </span>
                </div>
            </td>
            <td>
                <span class="badge bg-secondary">${getTaskTypeText(task.task_type || task.func_name)}</span>
            </td>
            <td>${getStatusBadge(task.status)}</td>
            <td>
                <div class="d-flex align-items-center">
                    <div class="progress me-2" style="width: 60px; height: 8px;">
                        <div class="progress-bar ${getProgressBarClass(task.status)}" style="width: ${task.progress || 0}%"></div>
                    </div>
                    <small>${Math.round(task.progress || 0)}%</small>
                </div>
            </td>
            <td>
                <small class="text-muted">${formatDateTime(task.created_at)}</small>
            </td>
        </tr>
    `).join('');
}

// 获取站点名
function getSiteName(task) {
    try {
        // 优先从任务的site_name字段获取
        if (task && task.site_name) {
            return String(task.site_name);
        }

        // 从任务参数中提取站点信息（处理不同的数据结构）
        if (task && task.args && Array.isArray(task.args) && task.args.length > 0) {
            const firstArg = task.args[0];

            // 情况1：直接是站点配置对象
            if (firstArg && firstArg.name && firstArg.host) {
                return String(firstArg.name || firstArg.host);
            }

            // 情况2：包含site_config的对象（如监控任务）
            if (firstArg && firstArg.site_config) {
                const siteConfig = firstArg.site_config;
                if (siteConfig.name || siteConfig.host) {
                    return String(siteConfig.name || siteConfig.host);
                }
            }

            // 情况3：其他嵌套结构
            if (firstArg && typeof firstArg === 'object') {
                // 递归查找站点信息
                const findSiteInfo = (obj) => {
                    if (obj.name && obj.host) return obj;
                    for (const key in obj) {
                        if (typeof obj[key] === 'object' && obj[key] !== null) {
                            const result = findSiteInfo(obj[key]);
                            if (result) return result;
                        }
                    }
                    return null;
                };

                const siteInfo = findSiteInfo(firstArg);
                if (siteInfo) {
                    return String(siteInfo.name || siteInfo.host);
                }
            }
        }

        return '未知站点';
    } catch (e) {
        console.error('Error getting site name:', e, task);
        return '未知站点';
    }
}

// 获取远程路径
function getRemotePath(task) {
    try {
        const taskType = task.task_type || task.func_name;

        // 对于不同类型的任务，参数结构可能不同
        if (taskType === 'folder_monitor') {
            // 监控任务的参数结构: [monitor_config]
            if (task.args && task.args.length > 0 && task.args[0]) {
                const config = task.args[0];
                return config.remote_path || '/';
            }
        } else if (taskType === 'connection_test') {
            // 连接测试任务
            return '连接测试';
        } else {
            // 普通下载/上传任务的参数结构: [site_config, remote_path, local_path]
            if (task.args && task.args.length > 1) {
                return task.args[1] || '/';
            }
        }

        return '/';
    } catch (e) {
        console.error('Error getting remote path:', e, task);
        return '/';
    }
}

// 获取文件图标
function getFileIcon(task) {
    try {
        const taskType = task.task_type || task.func_name;
        const remotePath = getRemotePath(task);

        if (taskType === 'folder_download' || taskType === 'folder_monitor') {
            return 'bi-folder-fill text-warning';
        } else if (taskType === 'folder_upload') {
            return 'bi-folder-fill text-info';
        } else if (taskType === 'connection_test') {
            return 'bi-wifi text-success';
        } else {
            // 根据文件扩展名判断
            if (remotePath && remotePath.includes('.')) {
                const ext = remotePath.split('.').pop().toLowerCase();
                const iconMap = {
                    'txt': 'bi-file-text text-muted',
                    'pdf': 'bi-file-pdf text-danger',
                    'doc': 'bi-file-word text-primary',
                    'docx': 'bi-file-word text-primary',
                    'xls': 'bi-file-excel text-success',
                    'xlsx': 'bi-file-excel text-success',
                    'jpg': 'bi-file-image text-info',
                    'jpeg': 'bi-file-image text-info',
                    'png': 'bi-file-image text-info',
                    'gif': 'bi-file-image text-info',
                    'zip': 'bi-file-zip text-warning',
                    'rar': 'bi-file-zip text-warning'
                };
                return iconMap[ext] || 'bi-file-earmark text-muted';
            }
            return 'bi-file-earmark text-muted';
        }
    } catch (e) {
        console.error('Error getting file icon:', e, task);
        return 'bi-file-earmark text-muted';
    }
}

// 获取任务类型文本
function getTaskTypeText(taskType) {
    const typeMap = {
        'file_download': '文件下载',
        'file_upload': '文件上传',
        'folder_download': '文件夹下载',
        'folder_upload': '文件夹上传',
        'folder_monitor': '文件夹监控',
        'connection_test': '连接测试'
    };

    return typeMap[taskType] || taskType;
}

// 加载系统状态
async function loadSystemStatus() {
    try {
        const data = await apiRequest('/api/dashboard/system-status');
        updateSystemStatusDisplay(data);
    } catch (error) {
        console.error('Failed to load system status:', error);
    }
}

// 更新系统状态显示
function updateSystemStatusDisplay(status) {
    // 更新CPU使用率
    updateProgressBar('cpu-progress', 'cpu-usage', status.cpu_percent);
    
    // 更新内存使用率
    updateProgressBar('memory-progress', 'memory-usage', status.memory_percent);
    
    // 更新磁盘使用率
    updateProgressBar('disk-progress', 'disk-usage', status.disk_percent);
    
    // 更新调度器状态
    const schedulerStatus = document.getElementById('scheduler-status');
    if (schedulerStatus) {
        if (status.scheduler_running) {
            schedulerStatus.innerHTML = '<i class="bi bi-circle-fill text-success"></i> 运行中';
        } else {
            schedulerStatus.innerHTML = '<i class="bi bi-circle-fill text-danger"></i> 已停止';
        }
    }
    
    // 更新工作线程数
    const workerCount = document.getElementById('worker-count');
    if (workerCount) {
        workerCount.textContent = status.worker_count;
    }
}

// 更新进度条
function updateProgressBar(progressId, textId, percentage) {
    const progressBar = document.getElementById(progressId);
    const textElement = document.getElementById(textId);
    
    if (progressBar) {
        progressBar.style.width = percentage + '%';
        
        // 根据百分比设置颜色
        if (percentage > 80) {
            progressBar.className = 'progress-bar bg-danger';
        } else if (percentage > 60) {
            progressBar.className = 'progress-bar bg-warning';
        } else {
            progressBar.className = 'progress-bar bg-success';
        }
    }
    
    if (textElement) {
        textElement.textContent = Math.round(percentage) + '%';
    }
}

// 刷新最近任务
function refreshRecentTasks() {
    const refreshBtn = event.target.closest('a');
    if (refreshBtn) {
        refreshBtn.classList.add('btn-refresh', 'refreshing');
        
        loadRecentTasks().finally(() => {
            setTimeout(() => {
                refreshBtn.classList.remove('refreshing');
            }, 300);
        });
    }
}

// 快速操作函数
async function submitCreateTask() {
    const form = document.getElementById('createTaskForm');
    const formData = new FormData(form);
    
    const taskData = {
        site_id: formData.get('siteId'),
        priority: formData.get('priority')
    };
    
    const taskType = formData.get('taskType');
    
    // 根据任务类型设置路径参数
    if (taskType.includes('download')) {
        taskData.remote_path = formData.get('remotePath');
        taskData.local_path = formData.get('localPath');
    } else if (taskType.includes('upload')) {
        taskData.local_path = formData.get('remotePath'); // 注意：这里是反过来的
        taskData.remote_path = formData.get('localPath');
    }
    
    try {
        const response = await apiRequest(`/tasks/api/tasks/${taskType.replace('_', '-')}`, {
            method: 'POST',
            body: JSON.stringify(taskData)
        });
        
        showToast('success', response.message);
        
        // 关闭模态框
        const modal = bootstrap.Modal.getInstance(document.getElementById('createTaskModal'));
        modal.hide();
        
        // 刷新数据
        loadDashboardStats();
        loadRecentTasks();
        
    } catch (error) {
        showToast('error', '创建任务失败: ' + error.message);
    }
}

async function submitAddSite() {
    const form = document.getElementById('addSiteForm');
    const formData = new FormData(form);

    // 验证必填字段
    const siteName = formData.get('siteName');
    const siteHost = formData.get('siteHost');

    if (!siteName || !siteHost) {
        showToast('error', '站点名称和主机地址不能为空');
        return;
    }

    const siteData = {
        name: siteName,
        host: siteHost,
        port: parseInt(formData.get('sitePort')) || 21,
        username: formData.get('siteUsername') || '',
        password: formData.get('sitePassword') || '',
        protocol: formData.get('siteProtocol') || 'ftp',
        group: formData.get('siteGroup') || '默认分组'
    };

    try {
        console.log('Submitting site data:', siteData);

        const response = await apiRequest('/sites/api/sites', {
            method: 'POST',
            body: JSON.stringify(siteData)
        });

        console.log('Site creation response:', response);
        showToast('success', response.message + ` (站点ID: ${response.site.id})`);

        // 关闭模态框
        const modal = bootstrap.Modal.getInstance(document.getElementById('addSiteModal'));
        modal.hide();

        // 重置表单
        form.reset();

        // 刷新数据
        loadDashboardStats();

        // 如果在站点管理页面，也刷新站点列表
        if (typeof loadSites === 'function') {
            setTimeout(loadSites, 500);
        }

    } catch (error) {
        console.error('Site creation error:', error);
        showToast('error', '添加站点失败: ' + error.message);
    }
}

async function submitCreateMonitor() {
    const form = document.getElementById('createMonitorForm');
    const formData = new FormData(form);
    
    const monitorData = {
        name: formData.get('monitorName'),
        site_id: formData.get('monitorSiteId'),
        remote_path: formData.get('monitorRemotePath'),
        local_path: formData.get('monitorLocalPath'),
        file_pattern: formData.get('filePattern'),
        check_interval: parseInt(formData.get('checkInterval')),
        priority: formData.get('monitorPriority')
    };
    
    try {
        const response = await apiRequest('/api/monitors', {
            method: 'POST',
            body: JSON.stringify(monitorData)
        });
        
        showToast('success', response.message);
        
        // 关闭模态框
        const modal = bootstrap.Modal.getInstance(document.getElementById('createMonitorModal'));
        modal.hide();
        
        // 刷新数据
        loadDashboardStats();
        
    } catch (error) {
        showToast('error', '创建监控失败: ' + error.message);
    }
}

async function testAllSites() {
    try {
        // 获取所有站点
        const sitesData = await apiRequest('/sites/api/sites');
        
        if (sitesData.sites.length === 0) {
            showToast('warning', '没有可测试的站点');
            return;
        }
        
        showToast('info', `开始测试 ${sitesData.sites.length} 个站点的连接...`);
        
        // 为每个站点创建连接测试任务
        let successCount = 0;
        for (const site of sitesData.sites) {
            try {
                await apiRequest(`/sites/api/sites/${site.id}/test`, {
                    method: 'POST'
                });
                successCount++;
            } catch (error) {
                console.error(`Failed to test site ${site.name}:`, error);
            }
        }
        
        showToast('success', `已为 ${successCount} 个站点创建连接测试任务`);
        
        // 刷新数据
        setTimeout(() => {
            loadDashboardStats();
            loadRecentTasks();
        }, 1000);
        
    } catch (error) {
        showToast('error', '测试连接失败: ' + error.message);
    }
}

// 加载个人资料数据
async function loadProfileData() {
    try {
        const data = await apiRequest('/profile');
        const user = data.user;
        
        document.getElementById('profileUsername').value = user.username;
        document.getElementById('profileRole').value = user.role;
        document.getElementById('defaultDownloadPath').value = user.settings?.default_download_path || '';
        document.getElementById('maxConcurrentTasks').value = user.settings?.max_concurrent_tasks || 3;
        
        // 清空密码字段
        document.getElementById('oldPassword').value = '';
        document.getElementById('newPassword').value = '';
        document.getElementById('confirmPassword').value = '';
        
    } catch (error) {
        showToast('error', '加载个人资料失败: ' + error.message);
    }
}

// 更新个人资料
async function updateProfile() {
    const oldPassword = document.getElementById('oldPassword').value;
    const newPassword = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    
    // 验证密码
    if (newPassword && newPassword !== confirmPassword) {
        showToast('error', '新密码和确认密码不匹配');
        return;
    }
    
    const updateData = {
        settings: {
            default_download_path: document.getElementById('defaultDownloadPath').value,
            max_concurrent_tasks: parseInt(document.getElementById('maxConcurrentTasks').value)
        }
    };
    
    // 如果要更改密码
    if (newPassword) {
        if (!oldPassword) {
            showToast('error', '请输入原密码');
            return;
        }
        updateData.old_password = oldPassword;
        updateData.new_password = newPassword;
    }
    
    try {
        const response = await apiRequest('/profile', {
            method: 'PUT',
            body: JSON.stringify(updateData)
        });
        
        showToast('success', response.message);
        
        // 关闭模态框
        const modal = bootstrap.Modal.getInstance(document.getElementById('profileModal'));
        modal.hide();
        
    } catch (error) {
        showToast('error', '更新个人资料失败: ' + error.message);
    }
}

// 加载日志
async function loadLogs() {
    const logType = document.getElementById('logType').value;
    const logDate = document.getElementById('logDate').value;
    
    if (!logDate) {
        showToast('warning', '请选择日期');
        return;
    }
    
    try {
        const data = await apiRequest(`/api/logs/${logType}?date=${logDate}&limit=100`);
        updateLogsTable(data.logs);
    } catch (error) {
        showToast('error', '加载日志失败: ' + error.message);
    }
}

// 更新日志表格
function updateLogsTable(logs) {
    const tbody = document.getElementById('logs-tbody');
    if (!tbody) return;
    
    if (logs.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="3" class="text-center text-muted">
                    <div class="empty-state">
                        <i class="bi bi-journal-x"></i>
                        <p>该日期没有日志记录</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = logs.map(log => `
        <tr>
            <td><small>${formatDateTime(log.timestamp)}</small></td>
            <td><span class="badge bg-info">${log.type}</span></td>
            <td><small>${JSON.stringify(log, null, 2).substring(0, 200)}...</small></td>
        </tr>
    `).join('');
}

// 重写全局函数以支持仪表板实时更新
window.updateTaskStats = function(stats) {
    updateStatCard('total-tasks', stats.total_tasks || 0);
    updateStatCard('running-tasks', stats.running_tasks || 0);
    updateStatCard('system-efficiency', Math.round(stats.efficiency || 0) + '%');
};

window.updateSystemStatus = function(status) {
    // 更新调度器状态指示器
    const schedulerStatus = document.getElementById('scheduler-status');
    if (schedulerStatus) {
        if (status.scheduler_running) {
            schedulerStatus.innerHTML = '<i class="bi bi-circle-fill text-success"></i> 运行中';
        } else {
            schedulerStatus.innerHTML = '<i class="bi bi-circle-fill text-danger"></i> 已停止';
        }
    }
    
    // 更新工作线程数
    const workerCount = document.getElementById('worker-count');
    if (workerCount) {
        workerCount.textContent = status.worker_count;
    }
};

// 获取状态徽章
function getStatusBadge(status) {
    const statusMap = {
        'pending': '<span class="badge bg-secondary">等待中</span>',
        'running': '<span class="badge bg-primary">运行中</span>',
        'completed': '<span class="badge bg-success">已完成</span>',
        'failed': '<span class="badge bg-danger">失败</span>',
        'paused': '<span class="badge bg-warning">已暂停</span>',
        'cancelled': '<span class="badge bg-dark">已取消</span>'
    };
    return statusMap[status] || '<span class="badge bg-secondary">未知</span>';
}

// 获取进度条样式
function getProgressBarClass(status) {
    const classMap = {
        'pending': 'bg-secondary',
        'running': 'bg-primary',
        'completed': 'bg-success',
        'failed': 'bg-danger',
        'paused': 'bg-warning',
        'cancelled': 'bg-dark'
    };
    return classMap[status] || 'bg-secondary';
}

// 格式化时间
function formatDateTime(dateString) {
    if (!dateString) return '-';
    try {
        const date = new Date(dateString);
        return date.toLocaleString('zh-CN');
    } catch (e) {
        return dateString;
    }
}

// 显示创建任务模态框（调用FTP浏览器）
function showCreateTaskModal() {
    // 直接调用FTP浏览器函数
    if (typeof showFTPBrowserModal === 'function') {
        showFTPBrowserModal();
    } else {
        console.error('FTP浏览器功能未加载');
        showToast('error', 'FTP浏览器功能未加载，请刷新页面重试');
    }
}

// 显示添加站点模态框
function showAddSiteModal() {
    if (typeof showSiteModal === 'function') {
        showSiteModal();
    } else {
        // 跳转到站点管理页面
        window.location.href = '/sites';
    }
}

// 显示创建监控任务模态框
function showCreateMonitorModal() {
    if (typeof showMonitorModal === 'function') {
        showMonitorModal();
    } else {
        showToast('info', '请使用FTP浏览器创建监控任务');
        showCreateTaskModal();
    }
}

// 测试所有站点连接
async function testAllSites() {
    try {
        showToast('info', '正在测试所有站点连接...');

        const data = await apiRequest('/sites/api/sites');
        const sites = data.sites;

        if (sites.length === 0) {
            showToast('warning', '没有可测试的站点');
            return;
        }

        let successCount = 0;
        let failCount = 0;

        for (const site of sites) {
            try {
                await apiRequest(`/sites/api/sites/${site.id}/test`, {
                    method: 'POST'
                });
                successCount++;
            } catch (error) {
                failCount++;
                console.error(`测试站点 ${site.name} 失败:`, error);
            }
        }

        showToast('success', `连接测试完成：成功 ${successCount} 个，失败 ${failCount} 个`);

        // 刷新仪表板数据
        loadDashboardStats();

    } catch (error) {
        console.error('测试所有站点失败:', error);
        showToast('error', '测试连接失败: ' + error.message);
    }
}

// 刷新最近任务
function refreshRecentTasks() {
    loadRecentTasks();
    showToast('success', '任务列表已刷新');
}
