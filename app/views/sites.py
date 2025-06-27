#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FTP站点管理模块
"""

import base64
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template, current_app, session
from app.views.auth import login_required, permission_required, check_user_status

sites_bp = Blueprint('sites', __name__, url_prefix='/sites')

def encrypt_password(password: str) -> str:
    """简单的密码加密（实际项目中应使用更安全的加密方法）"""
    return base64.b64encode(password.encode()).decode()

def decrypt_password(encrypted: str) -> str:
    """解密密码"""
    try:
        return base64.b64decode(encrypted.encode()).decode()
    except:
        return encrypted

  # 如果解密失败，返回原文

@sites_bp.route('/')
@login_required
@check_user_status
def index():
    """站点管理页面"""
    return render_template('sites.html')

@sites_bp.route('/api/sites', methods=['GET'])
@login_required
@check_user_status
def list_sites():
    """获取站点列表"""
    try:
        sites = current_app.data_manager.load_sites()
        
        # 移除密码信息（安全考虑）
        safe_sites = []
        for site in sites:
            safe_site = site.copy()
            safe_site.pop('password', None)  # 移除密码字段
            safe_sites.append(safe_site)
        
        return jsonify({'sites': safe_sites})
        
    except Exception as e:
        return jsonify({'error': f'获取站点列表失败: {str(e)}'}), 500

@sites_bp.route('/api/sites', methods=['POST'])
@login_required
@check_user_status
# TODO: 临时移除权限检查，调试完成后恢复
# @permission_required('site_management')
def create_site():
    """创建新站点"""
    try:
        data = request.get_json()
        
        # 验证必填字段
        required_fields = ['name', 'host']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} 不能为空'}), 400
        
        # 生成站点ID
        site_id = current_app.data_manager.get_next_id('sites')
        
        # 创建站点对象
        site = {
            'id': site_id,
            'name': data['name'],
            'host': data['host'],
            'port': data.get('port', 21),
            'username': data.get('username', ''),
            'password': encrypt_password(data.get('password', '')),
            'protocol': data.get('protocol', 'ftp'),
            'group': data.get('group', '默认分组'),
            'status': 'unknown',
            'last_check': None,
            'connection_time': None,
            'last_error': None,
            'created_by': session.get('username', 'unknown'),
            'created_at': datetime.now().isoformat(),
            'auto_test': True  # 标记需要自动测试
        }
        
        # 保存站点
        current_app.data_manager.save_site(site)

        # 记录操作日志
        current_app.data_manager.write_log('operations', {
            'action': 'create_site',
            'site_id': site_id,
            'site_name': site['name'],
            'host': site['host'],
            'port': site['port'],
            'protocol': site['protocol'],
            'group': site['group'],
            'created_by': session.get('username', 'unknown'),
            'status': 'success'
        })

        # 自动执行连接测试（使用连接测试服务）
        try:
            current_app.connection_service.test_site_connection(
                site_id, site, session.get('username', 'system')
            )
            print(f"启动自动连接测试: {site_id}")
        except Exception as e:
            print(f"启动连接测试失败: {e}")

        # 移除密码信息返回
        safe_site = site.copy()
        safe_site.pop('password', None)
        safe_site.pop('auto_test', None)  # 移除内部标记

        return jsonify({
            'message': '站点创建成功，正在测试连接...',
            'site': safe_site
        }), 201
        
    except Exception as e:
        # 记录错误日志
        current_app.data_manager.write_log('operations', {
            'action': 'create_site',
            'site_name': data.get('name', 'unknown'),
            'host': data.get('host', 'unknown'),
            'created_by': session.get('username', 'unknown'),
            'status': 'failed',
            'error': str(e)
        })
        return jsonify({'error': f'创建站点失败: {str(e)}'}), 500

@sites_bp.route('/api/sites/<site_id>', methods=['GET'])
@login_required
@check_user_status
def get_site(site_id):
    """获取单个站点信息"""
    try:
        sites = current_app.data_manager.load_sites()
        
        site = None
        for s in sites:
            if s['id'] == site_id:
                site = s.copy()
                break
        
        if not site:
            return jsonify({'error': '站点不存在'}), 404
        
        # 移除密码信息
        site.pop('password', None)
        
        return jsonify({'site': site})
        
    except Exception as e:
        return jsonify({'error': f'获取站点信息失败: {str(e)}'}), 500

@sites_bp.route('/api/sites/<site_id>', methods=['PUT'])
@login_required
@check_user_status
@permission_required('site_management')
def update_site(site_id):
    """更新站点信息"""
    try:
        data = request.get_json()
        sites = current_app.data_manager.load_sites()
        
        site = None
        for s in sites:
            if s['id'] == site_id:
                site = s
                break
        
        if not site:
            return jsonify({'error': '站点不存在'}), 404
        
        # 更新字段
        updatable_fields = ['name', 'host', 'port', 'username', 'protocol', 'group']
        for field in updatable_fields:
            if field in data:
                site[field] = data[field]
        
        # 特殊处理密码字段
        if 'password' in data:
            site['password'] = encrypt_password(data['password'])
        
        site['updated_at'] = datetime.now().isoformat()
        
        # 保存更新
        current_app.data_manager.save_site(site)

        # 记录操作日志
        current_app.data_manager.write_log('operations', {
            'action': 'update_site',
            'site_id': site_id,
            'site_name': site['name'],
            'host': site['host'],
            'updated_by': session.get('username', 'unknown'),
            'status': 'success'
        })

        # 移除密码信息返回
        safe_site = site.copy()
        safe_site.pop('password', None)

        return jsonify({
            'message': '站点更新成功',
            'site': safe_site
        })
        
    except Exception as e:
        return jsonify({'error': f'更新站点失败: {str(e)}'}), 500

@sites_bp.route('/api/sites/<site_id>', methods=['DELETE'])
@login_required
@check_user_status
@permission_required('site_management')
def delete_site(site_id):
    """删除站点"""
    try:
        # 获取站点信息用于日志记录
        sites = current_app.data_manager.load_sites()
        site_to_delete = None
        for site in sites:
            if site['id'] == site_id:
                site_to_delete = site
                break

        # 删除站点
        current_app.data_manager.delete_site(site_id)

        # 记录操作日志
        current_app.data_manager.write_log('operations', {
            'action': 'delete_site',
            'site_id': site_id,
            'site_name': site_to_delete['name'] if site_to_delete else 'unknown',
            'host': site_to_delete['host'] if site_to_delete else 'unknown',
            'deleted_by': session.get('username', 'unknown'),
            'status': 'success'
        })

        return jsonify({'message': '站点删除成功'})
        
    except Exception as e:
        return jsonify({'error': f'删除站点失败: {str(e)}'}), 500

@sites_bp.route('/api/sites/<site_id>/test', methods=['POST'])
@login_required
@check_user_status
def test_site_connection(site_id):
    """测试站点连接（即时执行）"""
    try:
        # 获取站点配置
        sites = current_app.data_manager.load_sites()
        site_data = None
        for site in sites:
            if site['id'] == site_id:
                site_data = site
                break

        if not site_data:
            return jsonify({'error': '站点不存在'}), 404

        # 使用连接测试服务进行测试
        success = current_app.connection_service.test_site_connection(
            site_id, site_data, session.get('username', 'unknown')
        )

        if success:
            return jsonify({
                'message': '连接测试已启动，请稍后查看结果'
            })
        else:
            return jsonify({
                'message': '该站点已有正在进行的连接测试'
            })

    except Exception as e:
        return jsonify({'error': f'启动连接测试失败: {str(e)}'}), 500

@sites_bp.route('/api/sites/test-all', methods=['POST'])
@login_required
@check_user_status
@permission_required('site_management')
def test_all_sites():
    """测试所有站点连接"""
    try:
        started_count = current_app.connection_service.test_all_sites(
            created_by=session.get('username', 'unknown')
        )

        return jsonify({
            'message': f'已启动 {started_count} 个站点的连接测试'
        })

    except Exception as e:
        return jsonify({'error': f'批量测试失败: {str(e)}'}), 500

@sites_bp.route('/api/sites/active-tests', methods=['GET'])
@login_required
@check_user_status
def get_active_tests():
    """获取当前活跃的连接测试"""
    try:
        active_tests = current_app.connection_service.get_active_tests()

        return jsonify({
            'active_tests': active_tests,
            'count': len([t for t in active_tests.values() if t])
        })

    except Exception as e:
        return jsonify({'error': f'获取活跃测试失败: {str(e)}'}), 500

@sites_bp.route('/api/sites/<site_id>/browse', methods=['POST'])
@login_required
@check_user_status
def browse_site_directory(site_id):
    """浏览站点目录"""
    try:
        data = request.get_json()
        remote_path = data.get('path', '/')

        print(f"浏览目录请求: site_id={site_id}, path={remote_path}")

        # 获取站点配置
        sites = current_app.data_manager.load_sites()
        site_config = None
        for site in sites:
            if site['id'] == site_id:
                site_config = site.copy()
                # 解密密码
                site_config['password'] = decrypt_password(site_config.get('password', ''))
                break
        
        if not site_config:
            return jsonify({'error': '站点不存在'}), 404
        
        # 创建FTP客户端并浏览目录
        from app.core.ftp_client import FTPClient
        ftp_client = FTPClient(
            host=site_config['host'],
            port=site_config.get('port', 21),
            username=site_config.get('username', ''),
            password=site_config.get('password', ''),
            timeout=30
        )
        
        if not ftp_client.connect():
            return jsonify({'error': f'连接失败: {ftp_client.last_error}'}), 500
        
        try:
            # 获取目录列表
            print(f"正在列出目录: {remote_path}")
            files = ftp_client.list_directory(remote_path)
            current_dir = ftp_client.get_current_directory()

            print(f"目录列表获取成功: current_dir={current_dir}, files_count={len(files)}")
            for file in files[:5]:  # 只打印前5个文件
                print(f"  文件: {file}")

            return jsonify({
                'current_path': current_dir,
                'files': files
            })
            
        finally:
            ftp_client.disconnect()
        
    except Exception as e:
        return jsonify({'error': f'浏览目录失败: {str(e)}'}), 500

@sites_bp.route('/api/sites/groups', methods=['GET'])
@login_required
@check_user_status
def get_site_groups():
    """获取站点分组列表"""
    try:
        sites = current_app.data_manager.load_sites()
        
        # 提取所有分组
        groups = set()
        for site in sites:
            group = site.get('group', '默认分组')
            groups.add(group)
        
        return jsonify({'groups': sorted(list(groups))})
        
    except Exception as e:
        return jsonify({'error': f'获取分组列表失败: {str(e)}'}), 500
