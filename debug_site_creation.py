#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试站点创建问题
"""

import requests
import json

BASE_URL = "http://localhost:5000"

def test_site_creation():
    """测试站点创建"""
    print("=== 调试站点创建问题 ===")
    
    # 1. 先登录
    print("\n1. 登录超级管理员...")
    login_response = requests.post(f"{BASE_URL}/login", json={
        "username": "admin",
        "password": "admin123"
    })
    
    print(f"登录状态码: {login_response.status_code}")
    if login_response.status_code != 200:
        print(f"登录失败: {login_response.json()}")
        return
    
    login_data = login_response.json()
    print(f"登录成功: {login_data['user']['username']} ({login_data['user']['role']})")
    print(f"权限: {login_data['user']['permissions']}")
    
    cookies = login_response.cookies
    
    # 2. 检查用户信息
    print("\n2. 检查用户信息...")
    profile_response = requests.get(f"{BASE_URL}/profile", cookies=cookies)
    print(f"用户信息状态码: {profile_response.status_code}")
    if profile_response.status_code == 200:
        profile_data = profile_response.json()
        print(f"用户权限: {profile_data['user']['permissions']}")
    else:
        print(f"获取用户信息失败: {profile_response.json()}")
    
    # 3. 测试获取站点列表
    print("\n3. 测试获取站点列表...")
    sites_response = requests.get(f"{BASE_URL}/sites/api/sites", cookies=cookies)
    print(f"站点列表状态码: {sites_response.status_code}")
    if sites_response.status_code == 200:
        sites_data = sites_response.json()
        print(f"现有站点数量: {len(sites_data['sites'])}")
    else:
        print(f"获取站点列表失败: {sites_response.json()}")
    
    # 4. 测试创建站点
    print("\n4. 测试创建站点...")
    new_site = {
        "name": "测试站点",
        "host": "test.example.com",
        "port": 21,
        "username": "testuser",
        "password": "testpass",
        "protocol": "ftp",
        "group": "测试分组"
    }
    
    create_response = requests.post(f"{BASE_URL}/sites/api/sites", 
                                  json=new_site, 
                                  cookies=cookies)
    
    print(f"创建站点状态码: {create_response.status_code}")
    if create_response.status_code == 201:
        create_data = create_response.json()
        print(f"创建成功: {create_data['message']}")
        print(f"站点信息: {create_data['site']}")
    else:
        print(f"创建失败: {create_response.json()}")
        
        # 如果是权限问题，打印详细错误信息
        if create_response.status_code == 403:
            print("权限检查失败！")
            
            # 再次检查用户权限
            print("\n重新检查用户权限...")
            profile_response2 = requests.get(f"{BASE_URL}/profile", cookies=cookies)
            if profile_response2.status_code == 200:
                profile_data2 = profile_response2.json()
                permissions = profile_data2['user']['permissions']
                print(f"site_management权限: {permissions.get('site_management', 'NOT_FOUND')}")
            
    print("\n=== 调试完成 ===")

if __name__ == '__main__':
    try:
        test_site_creation()
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器，请确保应用正在运行在 http://localhost:5000")
    except Exception as e:
        print(f"❌ 调试过程中发生错误: {e}")
