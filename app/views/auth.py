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
    """管理员权限验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': '需要登录'}), 401
            return redirect(url_for('auth.login'))
        
        # 获取用户信息
        user = current_app.data_manager.find_user_by_username(session.get('username'))
        if not user or user.get('role') != 'admin':
            if request.is_json:
                return jsonify({'error': '需要管理员权限'}), 403
            return jsonify({'error': '需要管理员权限'}), 403
        
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
        
        # 验证密码
        if not verify_password(password, user['password_hash']):
            return jsonify({'error': '用户名或密码错误'}), 401
        
        # 设置会话
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        
        return jsonify({
            'message': '登录成功',
            'user': {
                'id': user['id'],
                'username': user['username'],
                'role': user['role']
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
        
        if not username or not password:
            return jsonify({'error': '用户名和密码不能为空'}), 400
        
        # 检查用户名是否已存在
        existing_user = current_app.data_manager.find_user_by_username(username)
        if existing_user:
            return jsonify({'error': '用户名已存在'}), 400
        
        # 创建新用户
        user_id = current_app.data_manager.get_next_id('users')
        new_user = {
            'id': user_id,
            'username': username,
            'password_hash': hash_password(password),
            'role': role,
            'settings': {
                'default_download_path': '/downloads',
                'max_concurrent_tasks': 3
            },
            'created_at': datetime.now().isoformat()
        }
        
        current_app.data_manager.save_user(new_user)
        
        return jsonify({
            'message': '用户创建成功',
            'user': {
                'id': new_user['id'],
                'username': new_user['username'],
                'role': new_user['role']
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'注册失败: {str(e)}'}), 500

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
        
        # 移除敏感信息
        safe_users = []
        for user in users:
            safe_users.append({
                'id': user['id'],
                'username': user['username'],
                'role': user['role'],
                'created_at': user.get('created_at')
            })
        
        return jsonify({'users': safe_users})
        
    except Exception as e:
        return jsonify({'error': f'获取用户列表失败: {str(e)}'}), 500

@auth_bp.route('/users/<user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """删除用户（仅管理员）"""
    try:
        users = current_app.data_manager.load_users()
        
        # 不能删除管理员账户
        user_to_delete = None
        for user in users:
            if user['id'] == user_id:
                user_to_delete = user
                break
        
        if not user_to_delete:
            return jsonify({'error': '用户不存在'}), 404
        
        if user_to_delete['role'] == 'admin':
            return jsonify({'error': '不能删除管理员账户'}), 400
        
        # 从列表中移除用户
        users = [u for u in users if u['id'] != user_id]
        
        # 保存更新后的用户列表
        data = current_app.data_manager._load_json(current_app.data_manager.files['users'])
        data['users'] = users
        current_app.data_manager._atomic_write(current_app.data_manager.files['users'], data)
        
        return jsonify({'message': '用户删除成功'})
        
    except Exception as e:
        return jsonify({'error': f'删除用户失败: {str(e)}'}), 500
