// 用户管理JavaScript

let users = [];
let currentUser = null;
let filteredUsers = [];

// 全局错误处理
window.addEventListener('error', function(event) {
    console.error('JavaScript错误:', event.error);
    console.error('错误位置:', event.filename, ':', event.lineno);
});

// 未处理的Promise错误
window.addEventListener('unhandledrejection', function(event) {
    console.error('未处理的Promise错误:', event.reason);
});

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('用户管理页面JavaScript已加载');

    // 测试关键函数是否可用
    if (typeof showCreateUserModal === 'function') {
        console.log('showCreateUserModal函数可用');
    } else {
        console.error('showCreateUserModal函数不可用');
    }

    loadCurrentUser();
    loadUsers();
    loadUserStats();
    bindEvents();
});

// 绑定事件
function bindEvents() {
    // 搜索框实时搜索
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.addEventListener('input', applyFilters);
    }

    // 筛选器变化
    const roleFilter = document.getElementById('role-filter');
    if (roleFilter) {
        roleFilter.addEventListener('change', applyFilters);
    }

    const statusFilter = document.getElementById('status-filter');
    if (statusFilter) {
        statusFilter.addEventListener('change', applyFilters);
    }

    // 角色变化时自动设置权限
    const roleSelect = document.getElementById('role');
    if (roleSelect) {
        roleSelect.addEventListener('change', function() {
            setDefaultPermissions(this.value);
        });
    }
}

// 加载当前用户信息
function loadCurrentUser() {
    fetch('/profile')
        .then(response => response.json())
        .then(data => {
            if (data.user) {
                currentUser = data.user;
                updateUIBasedOnRole();
            }
        })
        .catch(error => {
            console.error('加载用户信息失败:', error);
        });
}

// 根据角色更新UI
function updateUIBasedOnRole() {
    if (!currentUser) return;

    // 这个函数会在显示模态框时调用，所以不在这里直接修改DOM
    // 角色选项的更新移到 showCreateUserModal 函数中
}

// 根据当前用户角色更新角色选择器
function updateRoleOptions() {
    const roleSelect = document.getElementById('role');
    if (!roleSelect) return;

    // 超级管理员可以看到所有选项
    if (currentUser && currentUser.role === 'super_admin') {
        // 显示所有角色选项
        roleSelect.innerHTML = `
            <option value="user">普通用户</option>
            <option value="admin">管理员</option>
            <option value="super_admin">超级管理员</option>
        `;
    } else if (currentUser && currentUser.role === 'admin') {
        // 管理员只能创建普通用户
        roleSelect.innerHTML = `
            <option value="user">普通用户</option>
        `;
    } else {
        // 普通用户不能创建用户
        roleSelect.innerHTML = `
            <option value="user">普通用户</option>
        `;
    }
}

// 加载用户列表
function loadUsers() {
    fetch('/users')
        .then(response => response.json())
        .then(data => {
            if (data.users) {
                users = data.users;
                filteredUsers = [...users];
                renderUserTable();
            } else {
                showAlert('加载用户列表失败: ' + (data.error || '未知错误'), 'danger');
            }
        })
        .catch(error => {
            console.error('加载用户列表失败:', error);
            showAlert('加载用户列表失败', 'danger');
        });
}

// 加载用户统计
function loadUserStats() {
    fetch('/users/stats')
        .then(response => response.json())
        .then(data => {
            if (data.stats) {
                updateStatsCards(data.stats);
            }
        })
        .catch(error => {
            console.error('加载用户统计失败:', error);
        });
}

// 更新统计卡片
function updateStatsCards(stats) {
    document.getElementById('total-users').textContent = stats.total;
    document.getElementById('active-users').textContent = stats.active;
    document.getElementById('admin-users').textContent = stats.by_role.admin + stats.by_role.super_admin;
    document.getElementById('disabled-users').textContent = stats.disabled + stats.locked;
}

// 渲染用户表格
function renderUserTable() {
    const tbody = document.getElementById('users-table-body');
    tbody.innerHTML = '';
    
    filteredUsers.forEach(user => {
        const row = createUserRow(user);
        tbody.appendChild(row);
    });
}

// 创建用户行
function createUserRow(user) {
    const row = document.createElement('tr');
    
    // 角色显示
    const roleText = {
        'super_admin': '超级管理员',
        'admin': '管理员',
        'user': '普通用户'
    }[user.role] || user.role;
    
    // 状态显示
    const statusBadge = {
        'active': '<span class="badge badge-success">活跃</span>',
        'disabled': '<span class="badge badge-warning">禁用</span>',
        'locked': '<span class="badge badge-danger">锁定</span>'
    }[user.status] || '<span class="badge badge-secondary">未知</span>';
    
    // 最后登录时间
    const lastLogin = user.last_login ? 
        new Date(user.last_login).toLocaleString('zh-CN') : 
        '<span class="text-muted">从未登录</span>';
    
    // 创建时间
    const createdAt = user.created_at ? 
        new Date(user.created_at).toLocaleString('zh-CN') : 
        '<span class="text-muted">未知</span>';
    
    // 操作按钮
    const actions = createActionButtons(user);
    
    row.innerHTML = `
        <td>
            <div class="d-flex align-items-center">
                <i class="bi bi-person-circle fs-4 text-primary me-2"></i>
                <div>
                    <strong>${user.username}</strong>
                    <br>
                    <small class="text-muted">ID: ${user.id}</small>
                </div>
            </div>
        </td>
        <td>
            <span class="badge badge-${getRoleBadgeClass(user.role)}">${roleText}</span>
        </td>
        <td>${statusBadge}</td>
        <td>${lastLogin}</td>
        <td>${createdAt}</td>
        <td>${actions}</td>
    `;
    
    return row;
}

// 获取角色徽章样式
function getRoleBadgeClass(role) {
    const classes = {
        'super_admin': 'danger',
        'admin': 'warning',
        'user': 'info'
    };
    return classes[role] || 'secondary';
}

// 创建操作按钮
function createActionButtons(user) {
    let buttons = `
        <button class="btn btn-sm btn-info me-1" onclick="showUserDetail('${user.id}')" title="查看详情">
            <i class="bi bi-eye"></i>
        </button>
    `;
    
    // 不能操作自己
    if (currentUser && user.id !== currentUser.id) {
        // 普通管理员不能操作超级管理员
        if (!(currentUser.role === 'admin' && user.role === 'super_admin')) {
            buttons += `
                <button class="btn btn-sm btn-primary me-1" onclick="editUser('${user.id}')" title="编辑">
                    <i class="bi bi-pencil"></i>
                </button>
            `;

            // 状态切换按钮
            if (user.status === 'active') {
                buttons += `
                    <button class="btn btn-sm btn-warning me-1" onclick="toggleUserStatus('${user.id}', 'disabled')" title="禁用">
                        <i class="bi bi-ban"></i>
                    </button>
                `;
            } else {
                buttons += `
                    <button class="btn btn-sm btn-success me-1" onclick="toggleUserStatus('${user.id}', 'active')" title="启用">
                        <i class="bi bi-check"></i>
                    </button>
                `;
            }

            // 不能删除超级管理员
            if (user.role !== 'super_admin') {
                buttons += `
                    <button class="btn btn-sm btn-danger" onclick="deleteUser('${user.id}')" title="删除">
                        <i class="bi bi-trash"></i>
                    </button>
                `;
            }
        }
    }
    
    return buttons;
}

// 应用筛选
function applyFilters() {
    const searchTerm = document.getElementById('search-input').value.toLowerCase();
    const roleFilter = document.getElementById('role-filter').value;
    const statusFilter = document.getElementById('status-filter').value;
    
    filteredUsers = users.filter(user => {
        const matchesSearch = user.username.toLowerCase().includes(searchTerm);
        const matchesRole = !roleFilter || user.role === roleFilter;
        const matchesStatus = !statusFilter || user.status === statusFilter;
        
        return matchesSearch && matchesRole && matchesStatus;
    });
    
    renderUserTable();
}

// 刷新用户列表
function refreshUserList() {
    loadUsers();
    loadUserStats();
}

// 确保关键函数在全局作用域中可用
window.refreshUserList = refreshUserList;
window.applyFilters = applyFilters;

// 显示创建用户模态框
function showCreateUserModal() {
    console.log('showCreateUserModal called');

    try {
        // 检查必要的DOM元素
        const userModalTitle = document.getElementById('userModalTitle');
        const userForm = document.getElementById('userForm');
        const userId = document.getElementById('userId');
        const password = document.getElementById('password');
        const userModal = document.getElementById('userModal');

        if (!userModalTitle) {
            throw new Error('userModalTitle元素不存在');
        }
        if (!userForm) {
            throw new Error('userForm元素不存在');
        }
        if (!userId) {
            throw new Error('userId元素不存在');
        }
        if (!password) {
            throw new Error('password元素不存在');
        }
        if (!userModal) {
            throw new Error('userModal元素不存在');
        }

        console.log('所有必要的DOM元素都存在');

        userModalTitle.textContent = '创建用户';
        userForm.reset();
        userId.value = '';
        password.required = true;

        console.log('表单已重置');

        // 更新角色选项
        updateRoleOptions();
        console.log('角色选项已更新');

        // 设置默认权限
        setDefaultPermissions('user');
        console.log('默认权限已设置');

        // 显示模态框
        const modal = new bootstrap.Modal(userModal);
        modal.show();

        console.log('模态框应该已显示');
    } catch (error) {
        console.error('Error in showCreateUserModal:', error);
        alert('显示创建用户对话框失败: ' + error.message);
    }
}

// 确保函数在全局作用域中可用
window.showCreateUserModal = showCreateUserModal;

// 测试函数
function testFunction() {
    console.log('测试函数被调用');
    alert('JavaScript正常工作！\n\n当前用户: ' + (currentUser ? currentUser.username : '未加载') + '\n用户数量: ' + users.length);

    // 测试模态框
    try {
        const modal = document.getElementById('userModal');
        if (modal) {
            console.log('找到用户模态框');
            const bsModal = new bootstrap.Modal(modal);
            bsModal.show();
            console.log('模态框应该已显示');
        } else {
            console.error('未找到用户模态框');
        }
    } catch (error) {
        console.error('测试模态框失败:', error);
    }
}

window.testFunction = testFunction;

// 编辑用户
function editUser(userId) {
    const user = users.find(u => u.id === userId);
    if (!user) return;
    
    document.getElementById('userModalTitle').textContent = '编辑用户';
    document.getElementById('userId').value = user.id;
    document.getElementById('username').value = user.username;
    document.getElementById('password').value = '';
    document.getElementById('password').required = false;
    document.getElementById('role').value = user.role;
    document.getElementById('status').value = user.status;
    
    // 设置用户设置
    const settings = user.settings || {};
    document.getElementById('defaultDownloadPath').value = settings.default_download_path || '/downloads';
    document.getElementById('maxConcurrentTasks').value = settings.max_concurrent_tasks || 3;
    
    // 设置权限
    setPermissions(user.permissions || {});

    new bootstrap.Modal(document.getElementById('userModal')).show();
}

// 设置默认权限
function setDefaultPermissions(role) {
    const permissions = {
        'super_admin': {
            userManagement: true,
            siteManagement: true,
            systemConfig: true,
            roleManagement: true,
            taskManagement: 'all'
        },
        'admin': {
            userManagement: true,
            siteManagement: true,
            systemConfig: false,
            roleManagement: false,
            taskManagement: 'all'
        },
        'user': {
            userManagement: false,
            siteManagement: false,
            systemConfig: false,
            roleManagement: false,
            taskManagement: 'own'
        }
    };
    
    setPermissions(permissions[role] || permissions['user']);
}

// 设置权限复选框
function setPermissions(permissions) {
    const userManagement = document.getElementById('userManagement');
    if (userManagement) {
        userManagement.checked = permissions.user_management || permissions.userManagement || false;
    }

    const siteManagement = document.getElementById('siteManagement');
    if (siteManagement) {
        siteManagement.checked = permissions.site_management || permissions.siteManagement || false;
    }

    const systemConfig = document.getElementById('systemConfig');
    if (systemConfig) {
        systemConfig.checked = permissions.system_config || permissions.systemConfig || false;
    }

    const roleManagement = document.getElementById('roleManagement');
    if (roleManagement) {
        roleManagement.checked = permissions.role_management || permissions.roleManagement || false;
    }

    const taskManagement = document.getElementById('taskManagement');
    if (taskManagement) {
        taskManagement.value = permissions.task_management || permissions.taskManagement || 'own';
    }
}

// 保存用户
function saveUser() {
    const form = document.getElementById('userForm');
    const formData = new FormData(form);
    const userId = formData.get('userId');
    
    // 构建用户数据
    const userData = {
        username: formData.get('username'),
        role: formData.get('role'),
        status: formData.get('status'),
        settings: {
            default_download_path: formData.get('defaultDownloadPath'),
            max_concurrent_tasks: parseInt(formData.get('maxConcurrentTasks'))
        },
        permissions: {
            user_management: document.getElementById('userManagement').checked,
            site_management: document.getElementById('siteManagement').checked,
            system_config: document.getElementById('systemConfig').checked,
            role_management: document.getElementById('roleManagement').checked,
            task_management: document.getElementById('taskManagement').value
        }
    };
    
    // 添加密码（如果有）
    const password = formData.get('password');
    if (password) {
        userData.password = password;
    }
    
    // 确定请求方法和URL
    const method = userId ? 'PUT' : 'POST';
    const url = userId ? `/users/${userId}` : '/register';
    
    fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(userData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.message) {
            showAlert(data.message, 'success');
            bootstrap.Modal.getInstance(document.getElementById('userModal')).hide();
            refreshUserList();
        } else {
            showAlert(data.error || '操作失败', 'danger');
        }
    })
    .catch(error => {
        console.error('保存用户失败:', error);
        showAlert('保存用户失败', 'danger');
    });
}

// 显示用户详情
function showUserDetail(userId) {
    fetch(`/users/${userId}`)
        .then(response => response.json())
        .then(data => {
            if (data.user) {
                renderUserDetail(data.user);
                new bootstrap.Modal(document.getElementById('userDetailModal')).show();
            } else {
                showAlert(data.error || '获取用户详情失败', 'danger');
            }
        })
        .catch(error => {
            console.error('获取用户详情失败:', error);
            showAlert('获取用户详情失败', 'danger');
        });
}

// 渲染用户详情
function renderUserDetail(user) {
    const content = document.getElementById('userDetailContent');
    
    const roleText = {
        'super_admin': '超级管理员',
        'admin': '管理员',
        'user': '普通用户'
    }[user.role] || user.role;
    
    const statusText = {
        'active': '活跃',
        'disabled': '禁用',
        'locked': '锁定'
    }[user.status] || user.status;
    
    const permissions = user.permissions || {};
    const settings = user.settings || {};
    
    content.innerHTML = `
        <div class="row">
            <div class="col-md-6">
                <h6>基本信息</h6>
                <table class="table table-sm">
                    <tr><td><strong>用户ID:</strong></td><td>${user.id}</td></tr>
                    <tr><td><strong>用户名:</strong></td><td>${user.username}</td></tr>
                    <tr><td><strong>角色:</strong></td><td><span class="badge badge-${getRoleBadgeClass(user.role)}">${roleText}</span></td></tr>
                    <tr><td><strong>状态:</strong></td><td><span class="badge badge-${user.status === 'active' ? 'success' : 'warning'}">${statusText}</span></td></tr>
                    <tr><td><strong>创建时间:</strong></td><td>${user.created_at ? new Date(user.created_at).toLocaleString('zh-CN') : '未知'}</td></tr>
                    <tr><td><strong>最后登录:</strong></td><td>${user.last_login ? new Date(user.last_login).toLocaleString('zh-CN') : '从未登录'}</td></tr>
                    <tr><td><strong>创建者:</strong></td><td>${user.created_by || '未知'}</td></tr>
                </table>
            </div>
            <div class="col-md-6">
                <h6>权限设置</h6>
                <table class="table table-sm">
                    <tr><td><strong>用户管理:</strong></td><td>${permissions.user_management ? '<i class="bi bi-check text-success"></i>' : '<i class="bi bi-x text-danger"></i>'}</td></tr>
                    <tr><td><strong>站点管理:</strong></td><td>${permissions.site_management ? '<i class="bi bi-check text-success"></i>' : '<i class="bi bi-x text-danger"></i>'}</td></tr>
                    <tr><td><strong>系统配置:</strong></td><td>${permissions.system_config ? '<i class="bi bi-check text-success"></i>' : '<i class="bi bi-x text-danger"></i>'}</td></tr>
                    <tr><td><strong>角色管理:</strong></td><td>${permissions.role_management ? '<i class="bi bi-check text-success"></i>' : '<i class="bi bi-x text-danger"></i>'}</td></tr>
                    <tr><td><strong>任务管理:</strong></td><td>${permissions.task_management || 'own'}</td></tr>
                </table>
                
                <h6 class="mt-3">用户设置</h6>
                <table class="table table-sm">
                    <tr><td><strong>默认下载路径:</strong></td><td>${settings.default_download_path || '/downloads'}</td></tr>
                    <tr><td><strong>最大并发任务:</strong></td><td>${settings.max_concurrent_tasks || 3}</td></tr>
                    <tr><td><strong>允许访问站点:</strong></td><td>${(settings.allowed_sites || []).length === 0 ? '所有站点' : settings.allowed_sites.join(', ')}</td></tr>
                </table>
            </div>
        </div>
    `;
}

// 切换用户状态
function toggleUserStatus(userId, newStatus) {
    const user = users.find(u => u.id === userId);
    if (!user) return;
    
    const statusText = {
        'active': '启用',
        'disabled': '禁用',
        'locked': '锁定'
    }[newStatus] || newStatus;
    
    if (!confirm(`确定要${statusText}用户 "${user.username}" 吗？`)) {
        return;
    }
    
    fetch(`/users/${userId}/status`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ status: newStatus })
    })
    .then(response => response.json())
    .then(data => {
        if (data.message) {
            showAlert(data.message, 'success');
            refreshUserList();
        } else {
            showAlert(data.error || '操作失败', 'danger');
        }
    })
    .catch(error => {
        console.error('更新用户状态失败:', error);
        showAlert('更新用户状态失败', 'danger');
    });
}

// 删除用户
function deleteUser(userId) {
    const user = users.find(u => u.id === userId);
    if (!user) return;
    
    if (!confirm(`确定要删除用户 "${user.username}" 吗？此操作不可撤销！`)) {
        return;
    }
    
    fetch(`/users/${userId}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.message) {
            showAlert(data.message, 'success');
            refreshUserList();
        } else {
            showAlert(data.error || '删除失败', 'danger');
        }
    })
    .catch(error => {
        console.error('删除用户失败:', error);
        showAlert('删除用户失败', 'danger');
    });
}

// 显示提示消息
function showAlert(message, type = 'info') {
    // 创建提示框
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="close" data-dismiss="alert">
            <span>&times;</span>
        </button>
    `;
    
    // 插入到页面顶部
    const container = document.querySelector('.container-fluid');
    container.insertBefore(alertDiv, container.firstChild);
    
    // 3秒后自动消失
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 3000);
}
