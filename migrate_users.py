#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户数据迁移脚本
将现有用户数据升级到新的三级权限体系
"""

import json
import os
import shutil
from datetime import datetime

def backup_data(data_dir="data"):
    """备份现有数据"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"{data_dir}/migration_backup_{timestamp}"
    
    print(f"创建备份目录: {backup_dir}")
    os.makedirs(backup_dir, exist_ok=True)
    
    # 备份用户数据文件
    users_file = f"{data_dir}/users.json"
    if os.path.exists(users_file):
        shutil.copy2(users_file, f"{backup_dir}/users.json")
        print(f"备份用户数据: {users_file}")
    
    return backup_dir

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

def migrate_user_data(data_dir="data"):
    """迁移用户数据"""
    users_file = f"{data_dir}/users.json"
    
    if not os.path.exists(users_file):
        print("用户数据文件不存在，跳过迁移")
        return
    
    print("开始迁移用户数据...")
    
    # 读取现有数据
    with open(users_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    users = data.get('users', [])
    migrated_count = 0
    
    for user in users:
        # 检查是否已经迁移过
        if 'permissions' in user and 'status' in user:
            print(f"用户 {user['username']} 已经迁移过，跳过")
            continue
        
        print(f"迁移用户: {user['username']}")
        
        # 升级角色：将原来的 'admin' 升级为 'super_admin'
        if user.get('role') == 'admin':
            user['role'] = 'super_admin'
            print(f"  - 角色升级: admin -> super_admin")
        
        # 添加权限设置
        user['permissions'] = get_default_permissions(user.get('role', 'user'))
        print(f"  - 添加权限: {user['permissions']}")
        
        # 添加用户状态
        user['status'] = 'active'
        print(f"  - 设置状态: active")
        
        # 添加最后登录时间
        if 'last_login' not in user:
            user['last_login'] = None
        
        # 添加创建者信息
        if 'created_by' not in user:
            user['created_by'] = 'system'
        
        # 扩展设置
        if 'settings' not in user:
            user['settings'] = {}
        
        settings = user['settings']
        if 'allowed_sites' not in settings:
            settings['allowed_sites'] = []  # 空数组表示可访问所有站点
        
        migrated_count += 1
    
    # 保存迁移后的数据
    with open(users_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"用户数据迁移完成，共迁移 {migrated_count} 个用户")

def create_test_users(data_dir="data"):
    """创建测试用户"""
    users_file = f"{data_dir}/users.json"
    
    if not os.path.exists(users_file):
        print("用户数据文件不存在，无法创建测试用户")
        return
    
    print("创建测试用户...")
    
    # 读取现有数据
    with open(users_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    users = data.get('users', [])
    
    # 检查是否已存在测试用户
    existing_usernames = [u['username'] for u in users]
    
    test_users = [
        {
            'id': 'user_000002',
            'username': 'admin_test',
            'password_hash': 'adb7d68e614527420719cea2a7f49848c6980e06f5e15867ebbf24cc2acc1d49',  # admin123
            'role': 'admin',
            'permissions': get_default_permissions('admin'),
            'settings': {
                'default_download_path': '/downloads',
                'max_concurrent_tasks': 3,
                'allowed_sites': []
            },
            'status': 'active',
            'created_at': datetime.now().isoformat(),
            'last_login': None,
            'created_by': 'system'
        },
        {
            'id': 'user_000003',
            'username': 'user_test',
            'password_hash': 'adb7d68e614527420719cea2a7f49848c6980e06f5e15867ebbf24cc2acc1d49',  # admin123
            'role': 'user',
            'permissions': get_default_permissions('user'),
            'settings': {
                'default_download_path': '/downloads',
                'max_concurrent_tasks': 2,
                'allowed_sites': []
            },
            'status': 'active',
            'created_at': datetime.now().isoformat(),
            'last_login': None,
            'created_by': 'system'
        }
    ]
    
    added_count = 0
    for test_user in test_users:
        if test_user['username'] not in existing_usernames:
            users.append(test_user)
            print(f"创建测试用户: {test_user['username']} ({test_user['role']})")
            added_count += 1
        else:
            print(f"测试用户 {test_user['username']} 已存在，跳过")
    
    # 更新计数器
    if added_count > 0:
        data['user_counter'] = data.get('user_counter', 1) + added_count
    
    # 保存数据
    with open(users_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"测试用户创建完成，共创建 {added_count} 个用户")

def verify_migration(data_dir="data"):
    """验证迁移结果"""
    users_file = f"{data_dir}/users.json"
    
    if not os.path.exists(users_file):
        print("用户数据文件不存在")
        return False
    
    print("验证迁移结果...")
    
    with open(users_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    users = data.get('users', [])
    
    print(f"总用户数: {len(users)}")
    
    # 统计各角色用户数
    role_counts = {}
    status_counts = {}
    
    for user in users:
        role = user.get('role', 'unknown')
        status = user.get('status', 'unknown')
        
        role_counts[role] = role_counts.get(role, 0) + 1
        status_counts[status] = status_counts.get(status, 0) + 1
        
        # 检查必要字段
        required_fields = ['id', 'username', 'role', 'permissions', 'status']
        missing_fields = [field for field in required_fields if field not in user]
        
        if missing_fields:
            print(f"用户 {user.get('username', 'unknown')} 缺少字段: {missing_fields}")
            return False
        
        # 检查权限结构
        permissions = user.get('permissions', {})
        required_permissions = ['user_management', 'site_management', 'task_management', 'system_config', 'role_management']
        missing_permissions = [perm for perm in required_permissions if perm not in permissions]
        
        if missing_permissions:
            print(f"用户 {user['username']} 缺少权限: {missing_permissions}")
            return False
    
    print("角色分布:")
    for role, count in role_counts.items():
        print(f"  {role}: {count}")
    
    print("状态分布:")
    for status, count in status_counts.items():
        print(f"  {status}: {count}")
    
    print("迁移验证通过！")
    return True

def main():
    """主函数"""
    print("=== FTP Web System 用户数据迁移工具 ===")
    print()
    
    data_dir = "data"
    
    # 1. 备份数据
    backup_dir = backup_data(data_dir)
    print()
    
    # 2. 迁移用户数据
    migrate_user_data(data_dir)
    print()
    
    # 3. 创建测试用户
    create_test_users(data_dir)
    print()
    
    # 4. 验证迁移结果
    if verify_migration(data_dir):
        print("✅ 数据迁移成功完成！")
        print(f"📁 备份文件位置: {backup_dir}")
        print()
        print("测试账户信息:")
        print("  超级管理员: admin / admin123")
        print("  管理员: admin_test / admin123")
        print("  普通用户: user_test / admin123")
    else:
        print("❌ 数据迁移失败，请检查错误信息")
        print(f"📁 可从备份恢复: {backup_dir}")

if __name__ == '__main__':
    main()
