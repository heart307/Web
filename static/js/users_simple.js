// 简化版用户管理JavaScript

console.log('简化版users.js已加载');

// 使用命名空间避免变量冲突
window.UserManagement = window.UserManagement || {
    users: [],
    filteredUsers: []
};

// 显示创建用户模态框
function showCreateUserModal() {
    console.log('showCreateUserModal被调用');
    
    try {
        // 检查Bootstrap
        if (typeof bootstrap === 'undefined') {
            throw new Error('Bootstrap未加载');
        }
        
        // 检查模态框元素
        const modalElement = document.getElementById('userModal');
        if (!modalElement) {
            throw new Error('找不到userModal元素');
        }
        
        console.log('找到模态框元素');
        
        // 设置标题
        const titleElement = document.getElementById('userModalTitle');
        if (titleElement) {
            titleElement.textContent = '创建用户';
        }
        
        // 重置表单
        const formElement = document.getElementById('userForm');
        if (formElement) {
            formElement.reset();
        }
        
        // 设置密码为必填
        const passwordElement = document.getElementById('password');
        if (passwordElement) {
            passwordElement.required = true;
        }

        // 设置默认状态
        const statusElement = document.getElementById('status');
        if (statusElement) {
            statusElement.value = 'active';
        }

        // 设置默认角色
        const roleElement = document.getElementById('role');
        if (roleElement) {
            roleElement.value = 'user';
        }

        // 显示模态框
        const modal = new bootstrap.Modal(modalElement);
        modal.show();
        
        console.log('模态框应该已显示');
        
    } catch (error) {
        console.error('显示模态框失败:', error);
        alert('显示创建用户对话框失败: ' + error.message);
    }
}

// 测试函数
function testFunction() {
    console.log('测试函数被调用');
    alert('简化版JavaScript正常工作！');
}

// 刷新用户列表
function refreshUserList() {
    console.log('刷新用户列表');
    alert('刷新功能暂未实现');
}

// 保存用户
async function saveUser() {
    console.log('保存用户');

    try {
        const form = document.getElementById('userForm');
        if (!form) {
            throw new Error('找不到用户表单');
        }

        const formData = new FormData(form);
        const userId = formData.get('userId');

        // 构建用户数据（简化版）
        const userData = {
            username: formData.get('username')?.trim(),
            role: formData.get('role'),
            status: formData.get('status') || 'active'
        };

        // 添加密码（如果有）
        const password = formData.get('password');
        if (password) {
            userData.password = password;
        }

        // 验证必填字段
        if (!userData.username) {
            alert('请输入用户名');
            return;
        }

        if (!userId && !password) {
            alert('请输入密码');
            return;
        }

        // 确定请求方法和URL
        const method = userId ? 'PUT' : 'POST';
        const url = userId ? `/users/${userId}` : '/register';

        console.log('发送请求:', { method, url, userData });

        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(userData)
        });

        const result = await response.json();

        if (response.ok) {
            alert(result.message || '操作成功');

            // 关闭模态框
            const modal = bootstrap.Modal.getInstance(document.getElementById('userModal'));
            if (modal) {
                modal.hide();
            }

            // 刷新页面
            window.location.reload();
        } else {
            alert(result.error || '操作失败');
        }

    } catch (error) {
        console.error('保存用户失败:', error);
        alert('保存用户失败: ' + error.message);
    }
}

// 确保函数在全局作用域中可用
window.showCreateUserModal = showCreateUserModal;
window.testFunction = testFunction;
window.refreshUserList = refreshUserList;
window.saveUser = saveUser;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('简化版用户管理页面JavaScript初始化完成');
});

console.log('简化版users.js文件加载完成');
