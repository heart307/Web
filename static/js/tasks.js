/**
 * 任务管理页面JavaScript
 */

// 全局变量
let tasksData = [];
let currentPage = 1;
let pageSize = 20;
let totalTasks = 0;
let currentFilters = {
    status: 'all',
    priority: 'all',
    type: 'all'
};

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('Tasks page loaded');
    loadTasks();
    
    // 设置定时刷新
    setInterval(loadTasks, 5000); // 每5秒刷新一次
});

// 加载任务列表
async function loadTasks() {
    try {
        console.log('Loading tasks...');
        
        // 构建查询参数
        const params = new URLSearchParams();
        if (currentFilters.status !== 'all') {
            params.append('status', currentFilters.status);
        }
        if (currentFilters.priority !== 'all') {
            params.append('priority', currentFilters.priority);
        }
        if (currentFilters.type !== 'all') {
            params.append('type', currentFilters.type);
        }
        params.append('limit', 100); // 获取足够的数据用于前端分页
        
        const url = `/tasks/api/tasks?${params.toString()}`;
        console.log('Fetching tasks from:', url);
        
        const data = await apiRequest(url);
        console.log('Tasks data received:', data);
        
        tasksData = data.tasks || [];

        // 去重处理：根据任务ID去除重复项
        const uniqueTasks = [];
        const seenIds = new Set();

        for (const task of tasksData) {
            const taskId = task.id || `${task.func_name}_${task.created_at}`;
            if (!seenIds.has(taskId)) {
                seenIds.add(taskId);
                uniqueTasks.push(task);
            } else {
                console.warn('Duplicate task found and removed:', taskId);
            }
        }

        tasksData = uniqueTasks;
        totalTasks = tasksData.length;

        // 验证任务数据结构
        tasksData = tasksData.map((task, index) => {
            try {
                // 确保基本字段存在
                if (!task.id) {
                    console.warn(`Task ${index} missing id:`, task);
                    task.id = `unknown_${index}`;
                }
                if (!task.args) {
                    console.warn(`Task ${index} missing args:`, task);
                    task.args = [];
                }
                if (!task.task_type && !task.func_name) {
                    console.warn(`Task ${index} missing task_type/func_name:`, task);
                    task.task_type = 'unknown';
                }
                return task;
            } catch (e) {
                console.error(`Error processing task ${index}:`, e, task);
                return {
                    id: `error_${index}`,
                    task_type: 'error',
                    status: 'failed',
                    priority: 'low',
                    progress: 0,
                    created_at: new Date().toISOString(),
                    args: []
                };
            }
        });

        updateTasksTable();
        updatePagination();
        updateTaskStats(); // 添加统计数据更新

        console.log('Tasks loaded successfully:', tasksData.length, 'tasks');
    } catch (error) {
        console.error('Failed to load tasks:', error);
        showToast('error', '加载任务列表失败: ' + error.message);
        
        // 显示错误状态
        const tbody = document.getElementById('tasks-tbody');
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="10" class="text-center text-danger">
                        <i class="bi bi-exclamation-triangle"></i> 加载失败: ${error.message}
                    </td>
                </tr>
            `;
        }
    }
}

// 更新任务表格
function updateTasksTable() {
    const tbody = document.getElementById('tasks-tbody');
    if (!tbody) return;
    
    if (tasksData.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="10" class="text-center text-muted">
                    <div class="empty-state py-4">
                        <i class="bi bi-inbox fa-3x mb-3"></i>
                        <h6>暂无任务</h6>
                        <p class="small">还没有创建任何任务</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    // 分页处理
    const startIndex = (currentPage - 1) * pageSize;
    const endIndex = startIndex + pageSize;
    const pageData = tasksData.slice(startIndex, endIndex);
    
    tbody.innerHTML = pageData.map((task, index) => {
        try {
            return `
                <tr>
                    <td>
                        <input type="checkbox" class="form-check-input" value="${task.id || 'unknown'}" onchange="updateBatchActions()">
                    </td>
                    <td>
                        <span class="text-primary">${getSiteName(task)}</span>
                    </td>
                    <td>
                        <div class="d-flex align-items-center">
                            <i class="bi ${getFileIcon(task)} me-2"></i>
                            <span class="text-truncate" style="max-width: 200px;" title="${getRemotePath(task)}">
                                ${getRemotePath(task)}
                            </span>
                        </div>
                    </td>
                    <td>
                        <span class="badge bg-secondary">${getTaskTypeText(task.task_type || task.func_name)}</span>
                    </td>
                    <td>${getPriorityBadge(task.priority)}</td>
                    <td>${getStatusBadge(task.status)}</td>
                    <td>
                        <div class="d-flex align-items-center">
                            <div class="progress me-2" style="width: 80px; height: 8px;">
                                <div class="progress-bar ${getProgressBarClass(task.status)}"
                                     style="width: ${task.progress || 0}%"></div>
                            </div>
                            <small>${Math.round(task.progress || 0)}%</small>
                        </div>
                    </td>
                    <td>
                        <span class="badge bg-light text-dark">${task.created_by || 'unknown'}</span>
                    </td>
                    <td>
                        <small class="text-muted">${formatDateTime(task.created_at)}</small>
                    </td>
                    <td>
                        <div class="btn-group btn-group-sm">
                            ${getTaskActions(task)}
                        </div>
                    </td>
                </tr>
            `;
        } catch (e) {
            console.error(`Error rendering task ${index}:`, e, task);
            return `
                <tr>
                    <td colspan="10" class="text-center text-warning">
                        <small>任务 ${index + 1} 渲染失败: ${e.message}</small>
                    </td>
                </tr>
            `;
        }
    }).join('');
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

        // 如果有site_id，尝试从全局站点列表获取（如果可用）
        if (task && task.site_id && window.sitesCache) {
            const site = window.sitesCache.find(s => s.id === task.site_id);
            if (site) {
                return String(site.name || site.host || '未知站点');
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
        if (!task) return '/';

        const taskType = task.task_type || task.func_name || '';

        // 对于不同类型的任务，参数结构可能不同
        if (taskType === 'folder_monitor') {
            // 监控任务的参数结构: [monitor_config]
            if (task.args && Array.isArray(task.args) && task.args.length > 0 && task.args[0]) {
                const config = task.args[0];
                if (config && typeof config === 'object') {
                    const remotePath = config.remote_path || '/';
                    return String(remotePath);
                }
            }
        } else if (taskType === 'connection_test') {
            // 连接测试任务
            return '连接测试';
        } else {
            // 普通下载/上传任务的参数结构: [site_config, remote_path, local_path]
            if (task.args && Array.isArray(task.args) && task.args.length > 1) {
                const remotePath = task.args[1];
                if (remotePath !== undefined && remotePath !== null) {
                    return String(remotePath);
                }
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
        if (!task) return 'bi-file-earmark text-muted';

        const taskType = task.task_type || task.func_name || '';
        const remotePath = getRemotePath(task);

        if (taskType === 'folder_download' || taskType === 'folder_monitor') {
            return 'bi-folder-fill text-warning';
        } else if (taskType === 'folder_upload') {
            return 'bi-folder-fill text-info';
        } else if (taskType === 'connection_test') {
            return 'bi-wifi text-success';
        } else {
            // 根据文件扩展名判断
            if (remotePath && typeof remotePath === 'string' && remotePath.includes('.')) {
                const parts = remotePath.split('.');
                if (parts.length > 1) {
                    const ext = parts.pop().toLowerCase();
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
    try {
        if (!taskType) return '未知类型';

        const typeMap = {
            'file_download': '文件下载',
            'file_upload': '文件上传',
            'folder_download': '文件夹下载',
            'folder_upload': '文件夹上传',
            'folder_monitor': '文件夹监控',
            'connection_test': '连接测试'
        };
        return typeMap[taskType] || String(taskType);
    } catch (e) {
        console.error('Error getting task type text:', e, taskType);
        return '未知类型';
    }
}

// 获取优先级徽章
function getPriorityBadge(priority) {
    try {
        if (!priority) return '<span class="badge bg-secondary">未知</span>';

        const priorityMap = {
            'high': '<span class="badge bg-danger">高</span>',
            'medium': '<span class="badge bg-warning">中</span>',
            'low': '<span class="badge bg-info">低</span>'
        };
        return priorityMap[priority] || '<span class="badge bg-secondary">未知</span>';
    } catch (e) {
        console.error('Error getting priority badge:', e, priority);
        return '<span class="badge bg-secondary">未知</span>';
    }
}

// 获取状态徽章
function getStatusBadge(status) {
    try {
        if (!status) return '<span class="badge bg-secondary">未知</span>';

        const statusMap = {
            'pending': '<span class="badge bg-secondary">等待中</span>',
            'running': '<span class="badge bg-primary">运行中</span>',
            'completed': '<span class="badge bg-success">已完成</span>',
            'failed': '<span class="badge bg-danger">失败</span>',
            'paused': '<span class="badge bg-warning">已暂停</span>',
            'cancelled': '<span class="badge bg-dark">已取消</span>'
        };
        return statusMap[status] || '<span class="badge bg-secondary">未知</span>';
    } catch (e) {
        console.error('Error getting status badge:', e, status);
        return '<span class="badge bg-secondary">未知</span>';
    }
}

// 获取进度条样式
function getProgressBarClass(status) {
    try {
        if (!status) return 'bg-secondary';

        const classMap = {
            'pending': 'bg-secondary',
            'running': 'bg-primary',
            'completed': 'bg-success',
            'failed': 'bg-danger',
            'paused': 'bg-warning',
            'cancelled': 'bg-dark'
        };
        return classMap[status] || 'bg-secondary';
    } catch (e) {
        console.error('Error getting progress bar class:', e, status);
        return 'bg-secondary';
    }
}

// 获取任务操作按钮
function getTaskActions(task) {
    try {
        if (!task || !task.id) {
            return '<span class="text-muted small">无操作</span>';
        }

        const taskId = String(task.id);
        const status = task.status || 'unknown';
        const actions = [];

        if (status === 'running') {
            actions.push(`<button class="btn btn-outline-warning btn-sm" onclick="pauseTask('${taskId}')" title="暂停">
                <i class="bi bi-pause"></i>
            </button>`);
        } else if (status === 'paused') {
            actions.push(`<button class="btn btn-outline-success btn-sm" onclick="resumeTask('${taskId}')" title="恢复">
                <i class="bi bi-play"></i>
            </button>`);
        }

        if (['pending', 'running', 'paused'].includes(status)) {
            actions.push(`<button class="btn btn-outline-danger btn-sm" onclick="cancelTask('${taskId}')" title="取消">
                <i class="bi bi-x"></i>
            </button>`);
        }

        // 删除按钮 - 对于已完成、失败、已取消的任务
        if (['completed', 'failed', 'cancelled'].includes(status)) {
            actions.push(`<button class="btn btn-outline-danger btn-sm" onclick="deleteTask('${taskId}')" title="删除">
                <i class="bi bi-trash"></i>
            </button>`);
        }

        actions.push(`<button class="btn btn-outline-info btn-sm" onclick="viewTaskDetails('${taskId}')" title="详情">
            <i class="bi bi-eye"></i>
        </button>`);

        return actions.join('');
    } catch (e) {
        console.error('Error getting task actions:', e, task);
        return '<span class="text-muted small">操作错误</span>';
    }
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

// 格式化持续时间
function formatDuration(seconds) {
    if (!seconds) return '-';
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
        return `${hours}h ${minutes}m ${secs}s`;
    } else if (minutes > 0) {
        return `${minutes}m ${secs}s`;
    } else {
        return `${secs}s`;
    }
}

// 筛选任务
function filterTasks(filterType, value) {
    currentFilters[filterType] = value;
    currentPage = 1; // 重置到第一页
    loadTasks();
}

// 更新分页
function updatePagination() {
    const pagination = document.getElementById('pagination');
    if (!pagination) return;
    
    const totalPages = Math.ceil(totalTasks / pageSize);
    
    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }
    
    let html = '';
    
    // 上一页
    html += `<li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
        <a class="page-link" href="#" onclick="changePage(${currentPage - 1})">上一页</a>
    </li>`;
    
    // 页码
    for (let i = 1; i <= totalPages; i++) {
        if (i === currentPage) {
            html += `<li class="page-item active">
                <span class="page-link">${i}</span>
            </li>`;
        } else {
            html += `<li class="page-item">
                <a class="page-link" href="#" onclick="changePage(${i})">${i}</a>
            </li>`;
        }
    }
    
    // 下一页
    html += `<li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
        <a class="page-link" href="#" onclick="changePage(${currentPage + 1})">下一页</a>
    </li>`;
    
    pagination.innerHTML = html;
}

// 切换页面
function changePage(page) {
    if (page < 1 || page > Math.ceil(totalTasks / pageSize)) return;
    currentPage = page;
    updateTasksTable();
    updatePagination();
}

// 任务操作函数
async function pauseTask(taskId) {
    try {
        await apiRequest(`/tasks/api/tasks/${taskId}/pause`, { method: 'POST' });
        showToast('success', '任务已暂停');
        loadTasks();
    } catch (error) {
        showToast('error', '暂停任务失败: ' + error.message);
    }
}

async function resumeTask(taskId) {
    try {
        await apiRequest(`/tasks/api/tasks/${taskId}/resume`, { method: 'POST' });
        showToast('success', '任务已恢复');
        loadTasks();
    } catch (error) {
        showToast('error', '恢复任务失败: ' + error.message);
    }
}

async function cancelTask(taskId) {
    if (!confirm('确定要取消这个任务吗？')) return;

    try {
        await apiRequest(`/tasks/api/tasks/${taskId}/cancel`, { method: 'POST' });
        showToast('success', '任务已取消');
        loadTasks();
    } catch (error) {
        showToast('error', '取消任务失败: ' + error.message);
    }
}

// 删除任务
async function deleteTask(taskId) {
    if (!confirm('确定要删除这个任务吗？删除后无法恢复。')) {
        return;
    }

    try {
        await apiRequest(`/tasks/api/tasks/${taskId}`, {
            method: 'DELETE'
        });

        showToast('success', '任务已删除');
        loadTasks(); // 重新加载任务列表
    } catch (error) {
        showToast('error', '删除任务失败: ' + error.message);
    }
}

// 查看任务详情
function viewTaskDetails(taskId) {
    // TODO: 实现任务详情模态框
    console.log('View task details:', taskId);
    showToast('info', '任务详情功能开发中...');
}

// 批量操作
function toggleSelectAll() {
    const selectAll = document.getElementById('selectAll');
    const checkboxes = document.querySelectorAll('#tasks-tbody input[type="checkbox"]');
    
    checkboxes.forEach(checkbox => {
        checkbox.checked = selectAll.checked;
    });
    
    updateBatchActions();
}

function updateBatchActions() {
    const checkedBoxes = document.querySelectorAll('#tasks-tbody input[type="checkbox"]:checked');
    const batchActionsBtn = document.querySelector('[onclick*="batchOperation"]');
    
    if (batchActionsBtn) {
        batchActionsBtn.disabled = checkedBoxes.length === 0;
    }
}

function batchOperation(operation) {
    const checkedBoxes = document.querySelectorAll('#tasks-tbody input[type="checkbox"]:checked');
    const taskIds = Array.from(checkedBoxes).map(cb => cb.value);
    
    if (taskIds.length === 0) {
        showToast('warning', '请先选择要操作的任务');
        return;
    }
    
    console.log('Batch operation:', operation, 'on tasks:', taskIds);
    showToast('info', '批量操作功能开发中...');
}

// 更新任务统计数据
function updateTaskStats() {
    try {
        // 计算各种状态的任务数量
        const stats = {
            total: tasksData.length,
            running: tasksData.filter(t => t.status === 'running').length,
            pending: tasksData.filter(t => t.status === 'pending').length,
            completed: tasksData.filter(t => t.status === 'completed').length,
            failed: tasksData.filter(t => t.status === 'failed').length,
            paused: tasksData.filter(t => t.status === 'paused').length
        };

        // 更新统计卡片
        const updateStatCard = (id, value) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        };

        updateStatCard('total-tasks', stats.total);
        updateStatCard('running-tasks', stats.running);
        updateStatCard('pending-tasks', stats.pending);
        updateStatCard('completed-tasks', stats.completed);
        updateStatCard('failed-tasks', stats.failed);
        updateStatCard('paused-tasks', stats.paused);

        console.log('Task stats updated:', stats);
    } catch (error) {
        console.error('Failed to update task stats:', error);
    }
}


