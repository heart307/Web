#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API接口模块
"""

import os
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app, session
from flask_socketio import emit
from app.views.auth import login_required
from app import socketio

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/monitors', methods=['GET'])
@login_required
def list_monitors():
    """获取监控任务列表"""
    try:
        monitors = current_app.data_manager.load_monitors()
        return jsonify({'monitors': monitors})
        
    except Exception as e:
        return jsonify({'error': f'获取监控列表失败: {str(e)}'}), 500

@api_bp.route('/monitors', methods=['POST'])
@login_required
def create_monitor():
    """创建监控任务"""
    try:
        data = request.get_json()
        
        # 验证必填字段
        required_fields = ['name', 'site_id', 'remote_path', 'local_path']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} 不能为空'}), 400
        
        # 生成监控ID
        monitor_id = current_app.data_manager.get_next_id('monitors')
        
        # 创建监控任务
        monitor = {
            'id': monitor_id,
            'name': data['name'],
            'site_id': data['site_id'],
            'remote_path': data['remote_path'],
            'local_path': data['local_path'],
            'priority': data.get('priority', 'medium'),
            'file_pattern': data.get('file_pattern', '*'),
            'check_interval': data.get('check_interval', 60),
            'status': 'active',
            'last_check': None,
            'file_list': [],
            'created_by': session.get('username', 'unknown'),
            'created_at': datetime.now().isoformat()
        }
        
        # 保存监控任务
        current_app.data_manager.save_monitor(monitor)
        
        return jsonify({
            'message': '监控任务创建成功',
            'monitor': monitor
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'创建监控任务失败: {str(e)}'}), 500

@api_bp.route('/monitors/<monitor_id>', methods=['PUT'])
@login_required
def update_monitor(monitor_id):
    """更新监控任务"""
    try:
        data = request.get_json()
        monitors = current_app.data_manager.load_monitors()
        
        monitor = None
        for m in monitors:
            if m['id'] == monitor_id:
                monitor = m
                break
        
        if not monitor:
            return jsonify({'error': '监控任务不存在'}), 404
        
        # 更新字段
        updatable_fields = ['name', 'remote_path', 'local_path', 'priority', 
                           'file_pattern', 'check_interval', 'status']
        for field in updatable_fields:
            if field in data:
                monitor[field] = data[field]
        
        monitor['updated_at'] = datetime.now().isoformat()
        
        # 保存更新
        current_app.data_manager.save_monitor(monitor)
        
        return jsonify({
            'message': '监控任务更新成功',
            'monitor': monitor
        })
        
    except Exception as e:
        return jsonify({'error': f'更新监控任务失败: {str(e)}'}), 500

@api_bp.route('/monitors/<monitor_id>', methods=['DELETE'])
@login_required
def delete_monitor(monitor_id):
    """删除监控任务"""
    try:
        monitors = current_app.data_manager.load_monitors()
        
        # 过滤掉要删除的监控任务
        updated_monitors = [m for m in monitors if m['id'] != monitor_id]
        
        if len(updated_monitors) == len(monitors):
            return jsonify({'error': '监控任务不存在'}), 404
        
        # 保存更新后的监控列表
        data = current_app.data_manager._load_json(current_app.data_manager.files['monitors'])
        data['monitors'] = updated_monitors
        current_app.data_manager._atomic_write(current_app.data_manager.files['monitors'], data)
        
        return jsonify({'message': '监控任务删除成功'})
        
    except Exception as e:
        return jsonify({'error': f'删除监控任务失败: {str(e)}'}), 500

@api_bp.route('/monitors/<monitor_id>/run', methods=['POST'])
@login_required
def run_monitor(monitor_id):
    """手动执行监控任务"""
    try:
        monitors = current_app.data_manager.load_monitors()
        
        monitor = None
        for m in monitors:
            if m['id'] == monitor_id:
                monitor = m
                break
        
        if not monitor:
            return jsonify({'error': '监控任务不存在'}), 404
        
        # 获取站点配置
        sites = current_app.data_manager.load_sites()
        site_config = None
        for site in sites:
            if site['id'] == monitor['site_id']:
                site_config = site
                break
        
        if not site_config:
            return jsonify({'error': '关联的站点不存在'}), 404
        
        # 创建监控任务
        monitor_config = {
            'monitor_id': monitor_id,
            'site_config': site_config,
            'remote_path': monitor['remote_path'],
            'local_path': monitor['local_path'],
            'file_pattern': monitor.get('file_pattern', '*'),
            'priority': monitor.get('priority', 'medium')
        }
        
        task_data = {
            'func_name': 'folder_monitor',
            'args': [monitor_config],
            'priority': 'high',  # 手动执行使用高优先级
            'task_type': 'folder_monitor',
            'created_by': session.get('username', 'unknown')
        }
        
        task_id = current_app.scheduler.add_task(task_data)
        
        return jsonify({
            'message': '监控任务已提交执行',
            'task_id': task_id
        })
        
    except Exception as e:
        return jsonify({'error': f'执行监控任务失败: {str(e)}'}), 500

@api_bp.route('/logs/<log_type>', methods=['GET'])
@login_required
def get_logs(log_type):
    """获取日志"""
    try:
        if log_type not in ['transfer', 'monitor', 'system', 'operations']:
            return jsonify({'error': '无效的日志类型'}), 400
        
        # 获取查询参数
        date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        limit = int(request.args.get('limit', 100))
        
        # 构建日志文件路径
        log_file = f"{current_app.config['DATA_DIR']}/logs/{log_type}/{date}.json"
        
        if not os.path.exists(log_file):
            return jsonify({'logs': []})
        
        # 读取日志文件
        import json
        with open(log_file, 'r', encoding='utf-8') as f:
            logs = json.load(f)
        
        # 按时间倒序排列
        logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # 限制数量
        if limit > 0:
            logs = logs[:limit]
        
        return jsonify({'logs': logs})
        
    except Exception as e:
        return jsonify({'error': f'获取日志失败: {str(e)}'}), 500

@api_bp.route('/upload', methods=['POST'])
@login_required
def upload_file():
    """文件上传接口"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': '没有文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400
        
        # 保存文件到上传目录
        upload_dir = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_dir, exist_ok=True)
        
        # 生成唯一文件名
        import uuid
        file_ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4().hex}{file_ext}"
        file_path = os.path.join(upload_dir, unique_filename)
        
        file.save(file_path)
        
        return jsonify({
            'message': '文件上传成功',
            'filename': unique_filename,
            'original_filename': file.filename,
            'file_path': file_path,
            'file_size': os.path.getsize(file_path)
        })
        
    except Exception as e:
        return jsonify({'error': f'文件上传失败: {str(e)}'}), 500

# WebSocket事件处理
@socketio.on('connect')
def handle_connect():
    """客户端连接"""
    print(f"客户端连接: {request.sid}")
    emit('connected', {'message': '连接成功'})

@socketio.on('disconnect')
def handle_disconnect():
    """客户端断开连接"""
    print(f"客户端断开连接: {request.sid}")

@socketio.on('subscribe_task_updates')
def handle_subscribe_task_updates():
    """订阅任务更新"""
    # 这里可以将客户端加入特定的房间，用于推送任务更新
    from flask_socketio import join_room
    join_room('task_updates')
    emit('subscribed', {'message': '已订阅任务更新'})

@socketio.on('subscribe_system_status')
def handle_subscribe_system_status():
    """订阅系统状态更新"""
    from flask_socketio import join_room
    join_room('system_status')
    emit('subscribed', {'message': '已订阅系统状态更新'})

# 定期推送更新的函数（需要在后台线程中调用）
def broadcast_task_updates():
    """广播任务更新"""
    try:
        # 获取最新的任务统计信息
        stats = current_app.scheduler.get_statistics()
        
        socketio.emit('task_stats_update', stats, room='task_updates')
        
    except Exception as e:
        print(f"广播任务更新失败: {e}")

def broadcast_system_status():
    """广播系统状态"""
    try:
        # 获取系统状态（简化版本）
        status = {
            'scheduler_running': current_app.scheduler.running,
            'worker_count': len(current_app.scheduler.workers),
            'timestamp': datetime.now().isoformat()
        }
        
        socketio.emit('system_status_update', status, room='system_status')
        
    except Exception as e:
        print(f"广播系统状态失败: {e}")
