#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户认证模块
"""

import hashlib
from datetime import datetime
from functools import wraps
from flask import Blueprint, request, session, jsonify, render_template, redirect, url_for, current_app

auth_bp = Blueprint('auth', __name__)

def hash_password(password: str) -> str:
    """密码哈希"""
    return hashlib.pbkdf2_hmac('sha256', password.encode(), b'salt', 100000).hex()

def verify_password(password: str, hashed: str) -> bool:
    """验证密码"""
    return hash_password(password) == hashed

def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': '需要登录'}), 401
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """管理员权限验证装饰器（管理员及以上）"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': '需要登录'}), 401
            return redirect(url_for('auth.login'))

        # 获取用户信息
        user = current_app.data_manager.find_user_by_username(session.get('username'))
        if not user or user.get('role') not in ['admin', 'super_admin']:
            if request.is_json:
                return jsonify({'error': '需要管理员权限'}), 403
            return jsonify({'error': '需要管理员权限'}), 403

        return f(*args, **kwargs)
    return decorated_function

def super_admin_required(f):
    """超级管理员权限验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': '需要登录'}), 401
            return redirect(url_for('auth.login'))

        # 获取用户信息
        user = current_app.data_manager.find_user_by_username(session.get('username'))
        if not user or user.get('role') != 'super_admin':
            if request.is_json:
                return jsonify({'error': '需要超级管理员权限'}), 403
            return jsonify({'error': '需要超级管理员权限'}), 403

        return f(*args, **kwargs)
    return decorated_function

def permission_required(permission_name):
    """特定权限验证装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                print(f"权限检查失败: 用户未登录")
                if request.is_json:
                    return jsonify({'error': '需要登录'}), 401
                return redirect(url_for('auth.login'))

            # 获取用户信息
            username = session.get('username')
            user = current_app.data_manager.find_user_by_username(username)
            if not user:
                print(f"权限检查失败: 用户 {username} 不存在")
                if request.is_json:
                    return jsonify({'error': '用户不存在'}), 404
                return redirect(url_for('auth.login'))

            # 检查权限
            permissions = user.get('permissions', {})
            has_permission = permissions.get(permission_name, False)

            print(f"权限检查: 用户={username}, 权限={permission_name}, 结果={has_permission}")
            print(f"用户所有权限: {permissions}")

            if not has_permission:
                print(f"权限检查失败: 用户 {username} 缺少 {permission_name} 权限")
                if request.is_json:
                    return jsonify({'error': f'需要{permission_name}权限'}), 403
                return jsonify({'error': f'需要{permission_name}权限'}), 403

            print(f"权限检查通过: 用户 {username} 具有 {permission_name} 权限")
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def resource_owner_or_admin(resource_user_id_param='user_id'):
    """资源所有者或管理员权限验证装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                if request.is_json:
                    return jsonify({'error': '需要登录'}), 401
                return redirect(url_for('auth.login'))

            # 获取当前用户信息
            current_user = current_app.data_manager.find_user_by_username(session.get('username'))
            if not current_user:
                if request.is_json:
                    return jsonify({'error': '用户不存在'}), 404
                return redirect(url_for('auth.login'))

            # 如果是管理员或超级管理员，直接允许
            if current_user.get('role') in ['admin', 'super_admin']:
                return f(*args, **kwargs)

            # 检查是否是资源所有者
            resource_user_id = kwargs.get(resource_user_id_param) or request.view_args.get(resource_user_id_param)
            if current_user['id'] == resource_user_id:
                return f(*args, **kwargs)

            if request.is_json:
                return jsonify({'error': '权限不足'}), 403
            return jsonify({'error': '权限不足'}), 403

        return decorated_function
    return decorator

def check_user_status(f):
    """检查用户状态装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': '需要登录'}), 401
            return redirect(url_for('auth.login'))

        # 获取用户信息
        user = current_app.data_manager.find_user_by_username(session.get('username'))
        if not user:
            if request.is_json:
                return jsonify({'error': '用户不存在'}), 404
            return redirect(url_for('auth.login'))

        # 检查用户状态
        status = user.get('status', 'active')
        if status != 'active':
            # 清除会话
            session.clear()
            if request.is_json:
                return jsonify({'error': '账户已被禁用'}), 403
            return redirect(url_for('auth.login'))

        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    if request.method == 'GET':
        return render_template('login.html')
    
    try:
        data = request.get_json() if request.is_json else request.form
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': '用户名和密码不能为空'}), 400
        
        # 查找用户
        user = current_app.data_manager.find_user_by_username(username)
        if not user:
            return jsonify({'error': '用户名或密码错误'}), 401
        
        # 检查用户状态
        if user.get('status', 'active') != 'active':
            return jsonify({'error': '账户已被禁用'}), 403

        # 验证密码
        if not verify_password(password, user['password_hash']):
            return jsonify({'error': '用户名或密码错误'}), 401

        # 更新最后登录时间
        current_app.data_manager.update_user_last_login(user['id'])

        # 设置会话
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']

        return jsonify({
            'message': '登录成功',
            'user': {
                'id': user['id'],
                'username': user['username'],
                'role': user['role'],
                'permissions': user.get('permissions', {}),
                'status': user.get('status', 'active')
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'登录失败: {str(e)}'}), 500

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """用户登出"""
    session.clear()
    return jsonify({'message': '登出成功'})

@auth_bp.route('/register', methods=['POST'])
@admin_required
def register():
    """用户注册（仅管理员可操作）"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        role = data.get('role', 'user')
        status = data.get('status', 'active')

        if not username or not password:
            return jsonify({'error': '用户名和密码不能为空'}), 400

        # 验证角色
        valid_roles = ['user', 'admin', 'super_admin']
        if role not in valid_roles:
            return jsonify({'error': '无效的用户角色'}), 400

        # 获取当前用户信息
        current_user = current_app.data_manager.find_user_by_username(session.get('username'))

        # 权限检查：只有超级管理员可以创建管理员和超级管理员
        if role in ['admin', 'super_admin'] and current_user.get('role') != 'super_admin':
            return jsonify({'error': '只有超级管理员可以创建管理员账户'}), 403

        # 检查用户名是否已存在
        existing_user = current_app.data_manager.find_user_by_username(username)
        if existing_user:
            return jsonify({'error': '用户名已存在'}), 400

        # 根据角色设置权限
        permissions = get_default_permissions(role)

        # 创建新用户
        user_id = current_app.data_manager.get_next_id('users')
        new_user = {
            'id': user_id,
            'username': username,
            'password_hash': hash_password(password),
            'role': role,
            'permissions': permissions,
            'settings': {
                'default_download_path': '/downloads',
                'max_concurrent_tasks': 3,
                'allowed_sites': []
            },
            'status': status,
            'created_at': datetime.now().isoformat(),
            'last_login': None,
            'created_by': current_user['id']
        }

        current_app.data_manager.save_user(new_user)

        return jsonify({
            'message': '用户创建成功',
            'user': {
                'id': new_user['id'],
                'username': new_user['username'],
                'role': new_user['role'],
                'status': new_user['status'],
                'created_at': new_user['created_at']
            }
        })

    except Exception as e:
        return jsonify({'error': f'注册失败: {str(e)}'}), 500

def get_default_permissions(role):
    """根据角色获取默认权限"""
    if role == 'super_admin':
        return {
            'user_management': True,
            'site_management': True,
            'task_management': 'all',
            'system_config': True,
            'role_management': True
        }
    elif role == 'admin':
        return {
            'user_management': True,
            'site_management': True,
            'task_management': 'all',
            'system_config': False,
            'role_management': False
        }
    else:  # user
        return {
            'user_management': False,
            'site_management': False,
            'task_management': 'own',
            'system_config': False,
            'role_management': False
        }

@auth_bp.route('/profile', methods=['GET'])
@login_required
def profile():
    """获取用户信息"""
    try:
        user = current_app.data_manager.find_user_by_username(session.get('username'))
        if not user:
            return jsonify({'error': '用户不存在'}), 404
        
        return jsonify({
            'user': {
                'id': user['id'],
                'username': user['username'],
                'role': user['role'],
                'settings': user.get('settings', {}),
                'created_at': user.get('created_at')
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'获取用户信息失败: {str(e)}'}), 500

@auth_bp.route('/profile', methods=['PUT'])
@login_required
def update_profile():
    """更新用户信息"""
    try:
        data = request.get_json()
        user = current_app.data_manager.find_user_by_username(session.get('username'))
        if not user:
            return jsonify({'error': '用户不存在'}), 404
        
        # 更新设置
        if 'settings' in data:
            user['settings'].update(data['settings'])
        
        # 更新密码
        if 'new_password' in data:
            old_password = data.get('old_password')
            if not old_password or not verify_password(old_password, user['password_hash']):
                return jsonify({'error': '原密码错误'}), 400
            
            user['password_hash'] = hash_password(data['new_password'])
        
        current_app.data_manager.save_user(user)
        
        return jsonify({'message': '用户信息更新成功'})
        
    except Exception as e:
        return jsonify({'error': f'更新用户信息失败: {str(e)}'}), 500

@auth_bp.route('/users', methods=['GET'])
@admin_required
def list_users():
    """获取用户列表（仅管理员）"""
    try:
        users = current_app.data_manager.load_users()
        current_user = current_app.data_manager.find_user_by_username(session.get('username'))

        # 移除敏感信息
        safe_users = []
        for user in users:
            # 普通管理员不能看到超级管理员
            if current_user.get('role') == 'admin' and user.get('role') == 'super_admin':
                continue

            safe_users.append({
                'id': user['id'],
                'username': user['username'],
                'role': user['role'],
                'status': user.get('status', 'active'),
                'permissions': user.get('permissions', {}),
                'last_login': user.get('last_login'),
                'created_at': user.get('created_at'),
                'created_by': user.get('created_by')
            })

        return jsonify({'users': safe_users})

    except Exception as e:
        return jsonify({'error': f'获取用户列表失败: {str(e)}'}), 500

@auth_bp.route('/users/<user_id>', methods=['GET'])
@admin_required
def get_user(user_id):
    """获取用户详情（仅管理员）"""
    try:
        user = current_app.data_manager.find_user_by_id(user_id)
        current_user = current_app.data_manager.find_user_by_username(session.get('username'))

        if not user:
            return jsonify({'error': '用户不存在'}), 404

        # 普通管理员不能查看超级管理员
        if current_user.get('role') == 'admin' and user.get('role') == 'super_admin':
            return jsonify({'error': '权限不足'}), 403

        # 移除敏感信息
        safe_user = {
            'id': user['id'],
            'username': user['username'],
            'role': user['role'],
            'status': user.get('status', 'active'),
            'permissions': user.get('permissions', {}),
            'settings': user.get('settings', {}),
            'last_login': user.get('last_login'),
            'created_at': user.get('created_at'),
            'created_by': user.get('created_by')
        }

        return jsonify({'user': safe_user})

    except Exception as e:
        return jsonify({'error': f'获取用户详情失败: {str(e)}'}), 500

@auth_bp.route('/users/<user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    """更新用户信息（仅管理员）"""
    try:
        data = request.get_json()
        user = current_app.data_manager.find_user_by_id(user_id)
        current_user = current_app.data_manager.find_user_by_username(session.get('username'))

        if not user:
            return jsonify({'error': '用户不存在'}), 404

        # 普通管理员不能修改超级管理员
        if current_user.get('role') == 'admin' and user.get('role') == 'super_admin':
            return jsonify({'error': '权限不足'}), 403

        # 不能修改自己的角色
        if user['id'] == current_user['id'] and 'role' in data:
            return jsonify({'error': '不能修改自己的角色'}), 400

        # 角色权限检查
        if 'role' in data:
            new_role = data['role']
            if new_role in ['admin', 'super_admin'] and current_user.get('role') != 'super_admin':
                return jsonify({'error': '只有超级管理员可以设置管理员角色'}), 403

            # 更新权限
            if new_role != user['role']:
                user['permissions'] = get_default_permissions(new_role)

        # 更新用户信息
        updatable_fields = ['role', 'status', 'settings']
        for field in updatable_fields:
            if field in data:
                user[field] = data[field]

        # 更新密码
        if 'password' in data and data['password']:
            user['password_hash'] = hash_password(data['password'])

        current_app.data_manager.save_user(user)

        return jsonify({'message': '用户信息更新成功'})

    except Exception as e:
        return jsonify({'error': f'更新用户信息失败: {str(e)}'}), 500

@auth_bp.route('/users/<user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """删除用户（仅管理员）"""
    try:
        user = current_app.data_manager.find_user_by_id(user_id)
        current_user = current_app.data_manager.find_user_by_username(session.get('username'))

        if not user:
            return jsonify({'error': '用户不存在'}), 404

        # 不能删除自己
        if user['id'] == current_user['id']:
            return jsonify({'error': '不能删除自己'}), 400

        # 普通管理员不能删除超级管理员
        if current_user.get('role') == 'admin' and user.get('role') == 'super_admin':
            return jsonify({'error': '权限不足'}), 403

        # 不能删除超级管理员（系统保护）
        if user.get('role') == 'super_admin':
            return jsonify({'error': '不能删除超级管理员账户'}), 400

        # 删除用户
        if current_app.data_manager.delete_user(user_id):
            return jsonify({'message': '用户删除成功'})
        else:
            return jsonify({'error': '删除用户失败'}), 500

    except Exception as e:
        return jsonify({'error': f'删除用户失败: {str(e)}'}), 500

@auth_bp.route('/users/<user_id>/status', methods=['PUT'])
@admin_required
def update_user_status(user_id):
    """更新用户状态（仅管理员）"""
    try:
        data = request.get_json()
        status = data.get('status')

        if status not in ['active', 'disabled', 'locked']:
            return jsonify({'error': '无效的用户状态'}), 400

        user = current_app.data_manager.find_user_by_id(user_id)
        current_user = current_app.data_manager.find_user_by_username(session.get('username'))

        if not user:
            return jsonify({'error': '用户不存在'}), 404

        # 不能修改自己的状态
        if user['id'] == current_user['id']:
            return jsonify({'error': '不能修改自己的状态'}), 400

        # 普通管理员不能修改超级管理员状态
        if current_user.get('role') == 'admin' and user.get('role') == 'super_admin':
            return jsonify({'error': '权限不足'}), 403

        # 不能禁用超级管理员
        if user.get('role') == 'super_admin' and status != 'active':
            return jsonify({'error': '不能禁用超级管理员账户'}), 400

        if current_app.data_manager.update_user_status(user_id, status):
            return jsonify({'message': '用户状态更新成功'})
        else:
            return jsonify({'error': '更新用户状态失败'}), 500

    except Exception as e:
        return jsonify({'error': f'更新用户状态失败: {str(e)}'}), 500

@auth_bp.route('/users/<user_id>/role', methods=['PUT'])
@super_admin_required
def update_user_role(user_id):
    """更新用户角色（仅超级管理员）"""
    try:
        data = request.get_json()
        new_role = data.get('role')

        if new_role not in ['user', 'admin', 'super_admin']:
            return jsonify({'error': '无效的用户角色'}), 400

        user = current_app.data_manager.find_user_by_id(user_id)
        current_user = current_app.data_manager.find_user_by_username(session.get('username'))

        if not user:
            return jsonify({'error': '用户不存在'}), 404

        # 不能修改自己的角色
        if user['id'] == current_user['id']:
            return jsonify({'error': '不能修改自己的角色'}), 400

        # 更新角色和权限
        user['role'] = new_role
        user['permissions'] = get_default_permissions(new_role)

        current_app.data_manager.save_user(user)

        return jsonify({'message': '用户角色更新成功'})

    except Exception as e:
        return jsonify({'error': f'更新用户角色失败: {str(e)}'}), 500

@auth_bp.route('/users/stats', methods=['GET'])
@admin_required
def get_user_stats():
    """获取用户统计信息（仅管理员）"""
    try:
        users = current_app.data_manager.load_users()

        stats = {
            'total': len(users),
            'active': len([u for u in users if u.get('status', 'active') == 'active']),
            'disabled': len([u for u in users if u.get('status', 'active') == 'disabled']),
            'locked': len([u for u in users if u.get('status', 'active') == 'locked']),
            'by_role': {
                'super_admin': len([u for u in users if u.get('role') == 'super_admin']),
                'admin': len([u for u in users if u.get('role') == 'admin']),
                'user': len([u for u in users if u.get('role') == 'user'])
            }
        }

        return jsonify({'stats': stats})

    except Exception as e:
        return jsonify({'error': f'获取用户统计失败: {str(e)}'}), 500

@auth_bp.route('/users/manage', methods=['GET'])
@admin_required
def manage_users():
    """用户管理页面（仅管理员）"""
    return render_template('users.html')

@auth_bp.route('/debug/permissions', methods=['GET'])
@login_required
def debug_permissions():
    """调试权限信息"""
    try:
        username = session.get('username')
        user = current_app.data_manager.find_user_by_username(username)

        if not user:
            return jsonify({'error': '用户不存在'}), 404

        return jsonify({
            'session': {
                'user_id': session.get('user_id'),
                'username': session.get('username'),
                'role': session.get('role')
            },
            'user_data': {
                'id': user['id'],
                'username': user['username'],
                'role': user['role'],
                'permissions': user.get('permissions', {}),
                'status': user.get('status', 'unknown')
            }
        })

    except Exception as e:
        return jsonify({'error': f'调试失败: {str(e)}'}), 500

@auth_bp.route('/debug/js-test', methods=['GET'])
@login_required
def debug_js_test():
    """JavaScript测试页面"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>JavaScript测试</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.7.2/font/bootstrap-icons.css" rel="stylesheet">
    </head>
    <body>
        <div class="container mt-5">
            <h1>JavaScript功能测试</h1>
            <button class="btn btn-primary" onclick="testFunction()">测试函数调用</button>
            <button class="btn btn-secondary" onclick="testUsersJS()">测试users.js加载</button>
            <div id="result" class="mt-3"></div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
        <script src="/static/js/users.js"></script>
        <script>
            function testFunction() {
                document.getElementById('result').innerHTML = '<div class="alert alert-success">JavaScript正常工作！</div>';
                console.log('测试函数被调用');
            }

            function testUsersJS() {
                if (typeof showCreateUserModal === 'function') {
                    document.getElementById('result').innerHTML = '<div class="alert alert-success">users.js已正确加载！</div>';
                } else {
                    document.getElementById('result').innerHTML = '<div class="alert alert-danger">users.js未正确加载！</div>';
                }
            }

            console.log('页面加载完成');
        </script>
    </body>
    </html>
    '''
