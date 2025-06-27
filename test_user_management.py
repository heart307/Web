#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户管理功能测试脚本
"""

import requests
import json

BASE_URL = "http://localhost:5000"

def test_login(username, password):
    """测试登录"""
    print(f"\n=== 测试登录: {username} ===")
    
    response = requests.post(f"{BASE_URL}/login", json={
        "username": username,
        "password": password
    })
    
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"登录成功: {data['user']['username']} ({data['user']['role']})")
        print(f"权限: {data['user']['permissions']}")
        return response.cookies
    else:
        print(f"登录失败: {response.json()}")
        return None

def test_user_list(cookies):
    """测试获取用户列表"""
    print(f"\n=== 测试获取用户列表 ===")
    
    response = requests.get(f"{BASE_URL}/users", cookies=cookies)
    
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        users = data['users']
        print(f"用户数量: {len(users)}")
        for user in users:
            print(f"  - {user['username']} ({user['role']}) - {user['status']}")
    else:
        print(f"获取用户列表失败: {response.json()}")

def test_user_stats(cookies):
    """测试获取用户统计"""
    print(f"\n=== 测试获取用户统计 ===")
    
    response = requests.get(f"{BASE_URL}/users/stats", cookies=cookies)
    
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        stats = data['stats']
        print(f"统计信息:")
        print(f"  总用户数: {stats['total']}")
        print(f"  活跃用户: {stats['active']}")
        print(f"  角色分布: {stats['by_role']}")
    else:
        print(f"获取用户统计失败: {response.json()}")

def test_create_user(cookies):
    """测试创建用户"""
    print(f"\n=== 测试创建用户 ===")
    
    new_user = {
        "username": "test_user_new",
        "password": "test123",
        "role": "user"
    }
    
    response = requests.post(f"{BASE_URL}/register", 
                           json=new_user, 
                           cookies=cookies)
    
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"创建用户成功: {data['message']}")
        print(f"用户信息: {data['user']}")
    else:
        print(f"创建用户失败: {response.json()}")

def test_permission_access(cookies, role):
    """测试权限访问"""
    print(f"\n=== 测试权限访问 ({role}) ===")
    
    # 测试访问用户管理页面
    response = requests.get(f"{BASE_URL}/users/manage", cookies=cookies)
    print(f"用户管理页面访问: {response.status_code}")
    
    # 测试访问站点列表
    response = requests.get(f"{BASE_URL}/sites/api/sites", cookies=cookies)
    print(f"站点列表访问: {response.status_code}")
    
    # 测试访问任务列表
    response = requests.get(f"{BASE_URL}/tasks/api/tasks", cookies=cookies)
    print(f"任务列表访问: {response.status_code}")

def main():
    """主测试函数"""
    print("=== FTP Web System 用户管理功能测试 ===")
    
    # 测试超级管理员登录
    admin_cookies = test_login("admin", "admin123")
    if admin_cookies:
        test_user_list(admin_cookies)
        test_user_stats(admin_cookies)
        test_create_user(admin_cookies)
        test_permission_access(admin_cookies, "super_admin")
    
    # 测试管理员登录
    admin_test_cookies = test_login("admin_test", "admin123")
    if admin_test_cookies:
        test_user_list(admin_test_cookies)
        test_permission_access(admin_test_cookies, "admin")
    
    # 测试普通用户登录
    user_cookies = test_login("user_test", "admin123")
    if user_cookies:
        test_permission_access(user_cookies, "user")
    
    # 测试错误登录
    test_login("nonexistent", "wrongpassword")
    
    print("\n=== 测试完成 ===")

if __name__ == '__main__':
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器，请确保应用正在运行在 http://localhost:5000")
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
