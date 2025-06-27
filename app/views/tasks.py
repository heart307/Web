#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务管理模块
"""

import os
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template, current_app, session
from app.views.auth import login_required, check_user_status

tasks_bp = Blueprint('tasks', __name__, url_prefix='/tasks')

def check_task_permission(task_id, action='view'):
    """检查任务权限"""
    try:
        # 获取当前用户信息
        current_user = current_app.data_manager.find_user_by_username(session.get('username'))
        if not current_user:
            return False, '用户不存在'

        # 获取任务信息
        task = current_app.scheduler.get_task_status(task_id)
        if not task:
            return False, '任务不存在'

        # 检查权限
        user_permissions = current_user.get('permissions', {})
        task_management = user_permissions.get('task_management', 'own')

        # 管理员可以操作所有任务
        if task_management == 'all':
            return True, None

        # 普通用户只能操作自己的任务
        if task_management == 'own':
            if task.get('created_by') == session.get('username'):
                return True, None
            else:
                return False, '权限不足：只能操作自己的任务'

        # 无权限
        return False, '无任务管理权限'

    except Exception as e:
        return False, f'权限检查失败: {str(e)}'

@tasks_bp.route('/')
@login_required
@check_user_status
def index():
    """任务管理页面"""
    return render_template('tasks.html')

@tasks_bp.route('/api/tasks', methods=['GET'])
@login_required
@check_user_status
def list_tasks():
    """获取任务列表"""
    try:
        # 获取查询参数
        status = request.args.get('status')
        priority = request.args.get('priority')
        task_type = request.args.get('type')
        limit = int(request.args.get('limit', 50))

        # 获取当前用户信息
        current_user = current_app.data_manager.find_user_by_username(session.get('username'))
        if not current_user:
            return jsonify({'error': '用户不存在'}), 404

        # 获取所有任务
        all_tasks = current_app.scheduler.get_all_tasks()

        # 根据用户权限过滤任务
        user_permissions = current_user.get('permissions', {})
        task_management = user_permissions.get('task_management', 'own')

        # 过滤任务
        filtered_tasks = []
        for task in all_tasks:
            # 权限过滤：普通用户只能看到自己的任务
            if task_management == 'own':
                if task.get('created_by') != session.get('username'):
                    continue
            # 管理员可以看到所有任务（task_management == 'all'）

            # 状态过滤
            if status and task.get('status') != status:
                continue

            # 优先级过滤
            if priority and str(task.get('priority', '')).lower() != priority.lower():
                continue

            # 类型过滤
            if task_type and task.get('task_type') != task_type:
                continue

            filtered_tasks.append(task)
        
        # 按创建时间排序
        filtered_tasks.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        # 限制数量
        if limit > 0:
            filtered_tasks = filtered_tasks[:limit]
        
        return jsonify({'tasks': filtered_tasks})
        
    except Exception as e:
        return jsonify({'error': f'获取任务列表失败: {str(e)}'}), 500

@tasks_bp.route('/api/tasks/<task_id>', methods=['GET'])
@login_required
@check_user_status
def get_task(task_id):
    """获取单个任务详情"""
    try:
        # 检查权限
        has_permission, error_msg = check_task_permission(task_id, 'view')
        if not has_permission:
            return jsonify({'error': error_msg}), 403

        task = current_app.scheduler.get_task_status(task_id)

        if not task:
            return jsonify({'error': '任务不存在'}), 404

        return jsonify({'task': task})

    except Exception as e:
        return jsonify({'error': f'获取任务详情失败: {str(e)}'}), 500

@tasks_bp.route('/api/tasks/<task_id>/pause', methods=['POST'])
@login_required
@check_user_status
def pause_task(task_id):
    """暂停任务"""
    try:
        # 检查权限
        has_permission, error_msg = check_task_permission(task_id, 'control')
        if not has_permission:
            return jsonify({'error': error_msg}), 403

        success = current_app.scheduler.pause_task(task_id)

        if success:
            return jsonify({'message': '任务已暂停'})
        else:
            return jsonify({'error': '暂停任务失败'}), 400

    except Exception as e:
        return jsonify({'error': f'暂停任务失败: {str(e)}'}), 500

@tasks_bp.route('/api/tasks/<task_id>/resume', methods=['POST'])
@login_required
@check_user_status
def resume_task(task_id):
    """恢复任务"""
    try:
        # 检查权限
        has_permission, error_msg = check_task_permission(task_id, 'control')
        if not has_permission:
            return jsonify({'error': error_msg}), 403

        success = current_app.scheduler.resume_task(task_id)

        if success:
            return jsonify({'message': '任务已恢复'})
        else:
            return jsonify({'error': '恢复任务失败'}), 400

    except Exception as e:
        return jsonify({'error': f'恢复任务失败: {str(e)}'}), 500

@tasks_bp.route('/api/tasks/<task_id>/cancel', methods=['POST'])
@login_required
@check_user_status
def cancel_task(task_id):
    """取消任务"""
    try:
        # 检查权限
        has_permission, error_msg = check_task_permission(task_id, 'control')
        if not has_permission:
            return jsonify({'error': error_msg}), 403

        success = current_app.scheduler.cancel_task(task_id)

        if success:
            return jsonify({'message': '任务已取消'})
        else:
            return jsonify({'error': '取消任务失败'}), 400

    except Exception as e:
        return jsonify({'error': f'取消任务失败: {str(e)}'}), 500

@tasks_bp.route('/api/tasks/<task_id>', methods=['DELETE'])
@login_required
def delete_task(task_id):
    """删除任务"""
    try:
        success = current_app.scheduler.delete_task(task_id)

        if success:
            return jsonify({'message': '任务已删除'})
        else:
            return jsonify({'error': '删除任务失败'}), 400

    except Exception as e:
        return jsonify({'error': f'删除任务失败: {str(e)}'}), 500

@tasks_bp.route('/api/tasks', methods=['POST'])
@login_required
def create_task():
    """通用任务创建接口"""
    try:
        data = request.get_json()

        # 验证必需字段
        required_fields = ['site_id', 'task_type', 'remote_path']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'缺少必需字段: {field}'}), 400

        site_id = data['site_id']
        task_type = data['task_type']
        remote_path = data['remote_path']
        local_path = data.get('local_path', '/downloads')
        priority = data.get('priority', 'medium')
        auto_start = data.get('auto_start', True)

        # 根据任务类型调用相应的服务方法
        if task_type == 'file_download':
            task_id = current_app.task_service.submit_file_download(
                site_id=site_id,
                remote_path=remote_path,
                local_path=local_path,
                priority=priority,
                created_by=session.get('username', 'unknown')
            )
        elif task_type == 'folder_download':
            task_id = current_app.task_service.submit_folder_download(
                site_id=site_id,
                remote_path=remote_path,
                local_path=local_path,
                priority=priority,
                created_by=session.get('username', 'unknown')
            )
        elif task_type == 'folder_monitor':
            monitor_interval = data.get('monitor_interval', 300)
            file_filter = data.get('file_filter', '')

            task_id = current_app.task_service.submit_folder_monitor(
                site_id=site_id,
                remote_path=remote_path,
                local_path=local_path,
                monitor_interval=monitor_interval,
                file_filter=file_filter,
                priority=priority,
                created_by=session.get('username', 'unknown')
            )
        else:
            return jsonify({'error': f'不支持的任务类型: {task_type}'}), 400

        # 记录操作日志
        current_app.data_manager.write_log('operations', {
            'action': 'create_task',
            'task_id': task_id,
            'task_type': task_type,
            'site_id': site_id,
            'remote_path': remote_path,
            'local_path': local_path,
            'priority': priority,
            'created_by': session.get('username', 'unknown'),
            'status': 'success'
        })

        return jsonify({
            'message': '任务创建成功',
            'task_id': task_id,
            'task_type': task_type
        }), 201

    except Exception as e:
        # 记录错误日志
        current_app.data_manager.write_log('operations', {
            'action': 'create_task',
            'task_type': data.get('task_type', 'unknown'),
            'site_id': data.get('site_id', 'unknown'),
            'created_by': session.get('username', 'unknown'),
            'status': 'failed',
            'error': str(e)
        })
        return jsonify({'error': f'创建任务失败: {str(e)}'}), 500

@tasks_bp.route('/api/tasks/file-download', methods=['POST'])
@login_required
def create_file_download_task():
    """创建文件下载任务"""
    try:
        data = request.get_json()
        
        # 验证必填字段
        required_fields = ['site_id', 'remote_path', 'local_path']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} 不能为空'}), 400
        
        # 提交任务
        task_id = current_app.task_service.submit_file_download(
            site_id=data['site_id'],
            remote_path=data['remote_path'],
            local_path=data['local_path'],
            priority=data.get('priority', 'medium'),
            created_by=session.get('username', 'unknown')
        )
        
        return jsonify({
            'message': '文件下载任务已创建',
            'task_id': task_id
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'创建下载任务失败: {str(e)}'}), 500

@tasks_bp.route('/api/tasks/file-upload', methods=['POST'])
@login_required
def create_file_upload_task():
    """创建文件上传任务"""
    try:
        data = request.get_json()
        
        # 验证必填字段
        required_fields = ['site_id', 'local_path', 'remote_path']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} 不能为空'}), 400
        
        # 提交任务
        task_id = current_app.task_service.submit_file_upload(
            site_id=data['site_id'],
            local_path=data['local_path'],
            remote_path=data['remote_path'],
            priority=data.get('priority', 'medium'),
            created_by=session.get('username', 'unknown')
        )
        
        return jsonify({
            'message': '文件上传任务已创建',
            'task_id': task_id
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'创建上传任务失败: {str(e)}'}), 500

@tasks_bp.route('/api/tasks/folder-download', methods=['POST'])
@login_required
def create_folder_download_task():
    """创建文件夹下载任务"""
    try:
        data = request.get_json()
        
        # 验证必填字段
        required_fields = ['site_id', 'remote_path', 'local_path']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} 不能为空'}), 400
        
        # 提交任务
        task_id = current_app.task_service.submit_folder_download(
            site_id=data['site_id'],
            remote_path=data['remote_path'],
            local_path=data['local_path'],
            priority=data.get('priority', 'medium'),
            created_by=session.get('username', 'unknown')
        )
        
        return jsonify({
            'message': '文件夹下载任务已创建',
            'task_id': task_id
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'创建文件夹下载任务失败: {str(e)}'}), 500

@tasks_bp.route('/api/tasks/folder-upload', methods=['POST'])
@login_required
def create_folder_upload_task():
    """创建文件夹上传任务"""
    try:
        data = request.get_json()
        
        # 验证必填字段
        required_fields = ['site_id', 'local_path', 'remote_path']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} 不能为空'}), 400
        
        # 提交任务
        task_id = current_app.task_service.submit_folder_upload(
            site_id=data['site_id'],
            local_path=data['local_path'],
            remote_path=data['remote_path'],
            priority=data.get('priority', 'medium'),
            created_by=session.get('username', 'unknown')
        )
        
        return jsonify({
            'message': '文件夹上传任务已创建',
            'task_id': task_id
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'创建文件夹上传任务失败: {str(e)}'}), 500

@tasks_bp.route('/api/tasks/statistics', methods=['GET'])
@login_required
def get_task_statistics():
    """获取任务统计信息"""
    try:
        # 获取调度器统计信息
        stats = current_app.scheduler.get_statistics()
        
        # 获取任务类型统计
        all_tasks = current_app.scheduler.get_all_tasks()
        
        type_stats = {}
        priority_stats = {'high': 0, 'medium': 0, 'low': 0}
        status_stats = {'pending': 0, 'running': 0, 'completed': 0, 'failed': 0, 'paused': 0}
        
        for task in all_tasks:
            # 类型统计
            task_type = task.get('task_type', 'unknown')
            type_stats[task_type] = type_stats.get(task_type, 0) + 1
            
            # 优先级统计
            priority = str(task.get('priority', 'medium')).lower()
            if priority in priority_stats:
                priority_stats[priority] += 1
            
            # 状态统计
            status = task.get('status', 'unknown')
            if status in status_stats:
                status_stats[status] += 1
        
        return jsonify({
            'scheduler': stats,
            'task_types': type_stats,
            'priorities': priority_stats,
            'statuses': status_stats
        })
        
    except Exception as e:
        return jsonify({'error': f'获取统计信息失败: {str(e)}'}), 500

@tasks_bp.route('/api/tasks/batch', methods=['POST'])
@login_required
def batch_task_operation():
    """批量任务操作"""
    try:
        data = request.get_json()
        task_ids = data.get('task_ids', [])
        operation = data.get('operation')  # pause, resume, cancel
        
        if not task_ids:
            return jsonify({'error': '任务ID列表不能为空'}), 400
        
        if operation not in ['pause', 'resume', 'cancel']:
            return jsonify({'error': '无效的操作类型'}), 400
        
        results = []
        for task_id in task_ids:
            try:
                if operation == 'pause':
                    success = current_app.scheduler.pause_task(task_id)
                elif operation == 'resume':
                    success = current_app.scheduler.resume_task(task_id)
                elif operation == 'cancel':
                    success = current_app.scheduler.cancel_task(task_id)
                
                results.append({
                    'task_id': task_id,
                    'success': success
                })
            except Exception as e:
                results.append({
                    'task_id': task_id,
                    'success': False,
                    'error': str(e)
                })
        
        return jsonify({
            'message': f'批量{operation}操作完成',
            'results': results
        })
        
    except Exception as e:
        return jsonify({'error': f'批量操作失败: {str(e)}'}), 500
