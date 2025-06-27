#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
仪表板模块
"""

from flask import Blueprint, render_template, jsonify, current_app
from app.views.auth import login_required

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    """仪表板首页"""
    return render_template('dashboard.html')

@dashboard_bp.route('/api/dashboard/stats')
@login_required
def get_dashboard_stats():
    """获取仪表板统计信息"""
    try:
        # 获取调度器统计信息
        scheduler_stats = current_app.scheduler.get_statistics()
        
        # 获取站点统计信息
        sites = current_app.data_manager.load_sites()
        site_stats = {
            'total_sites': len(sites),
            'connected_sites': len([s for s in sites if s.get('status') == 'connected']),
            'disconnected_sites': len([s for s in sites if s.get('status') == 'disconnected'])
        }
        
        # 获取任务统计信息
        all_tasks = current_app.scheduler.get_all_tasks()
        task_stats = {
            'total_tasks': len(all_tasks),
            'running_tasks': len([t for t in all_tasks if t.get('status') == 'running']),
            'pending_tasks': len([t for t in all_tasks if t.get('status') == 'pending']),
            'completed_tasks': len([t for t in all_tasks if t.get('status') == 'completed']),
            'failed_tasks': len([t for t in all_tasks if t.get('status') == 'failed'])
        }
        
        # 获取监控任务统计信息
        monitors = current_app.data_manager.load_monitors()
        monitor_stats = {
            'total_monitors': len(monitors),
            'active_monitors': len([m for m in monitors if m.get('status') == 'active']),
            'inactive_monitors': len([m for m in monitors if m.get('status') != 'active'])
        }
        
        return jsonify({
            'scheduler': scheduler_stats,
            'sites': site_stats,
            'tasks': task_stats,
            'monitors': monitor_stats
        })
        
    except Exception as e:
        return jsonify({'error': f'获取统计信息失败: {str(e)}'}), 500

@dashboard_bp.route('/api/dashboard/recent-tasks')
@login_required
def get_recent_tasks():
    """获取最近的任务"""
    try:
        all_tasks = current_app.scheduler.get_all_tasks()
        
        # 按创建时间排序，获取最近10个任务
        sorted_tasks = sorted(all_tasks, 
                            key=lambda x: x.get('created_at', ''), 
                            reverse=True)[:10]
        
        # 简化任务信息，但保留站点相关信息
        recent_tasks = []
        for task in sorted_tasks:
            recent_tasks.append({
                'id': task['id'],
                'func_name': task.get('func_name', ''),
                'task_type': task.get('task_type', ''),
                'priority': task.get('priority', ''),
                'status': task.get('status', ''),
                'progress': task.get('progress', 0),
                'created_at': task.get('created_at', ''),
                'started_at': task.get('started_at', ''),
                'completed_at': task.get('completed_at', ''),
                'error': task.get('error', ''),
                # 添加站点相关信息
                'site_id': task.get('site_id', ''),
                'site_name': task.get('site_name', ''),
                'remote_path': task.get('remote_path', ''),
                'local_path': task.get('local_path', ''),
                'args': task.get('args', [])  # 保留完整的args数组以兼容现有逻辑
            })
        
        return jsonify({'tasks': recent_tasks})
        
    except Exception as e:
        return jsonify({'error': f'获取最近任务失败: {str(e)}'}), 500

@dashboard_bp.route('/api/dashboard/system-status')
@login_required
def get_system_status():
    """获取系统状态"""
    try:
        import psutil
        import os
        
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # 内存使用情况
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # 磁盘使用情况
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        
        # 进程信息
        process = psutil.Process(os.getpid())
        process_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 调度器状态
        scheduler_running = current_app.scheduler.running
        worker_count = len(current_app.scheduler.workers)
        
        return jsonify({
            'cpu_percent': cpu_percent,
            'memory_percent': memory_percent,
            'disk_percent': disk_percent,
            'process_memory_mb': process_memory,
            'scheduler_running': scheduler_running,
            'worker_count': worker_count,
            'uptime': 'N/A'  # 可以添加启动时间计算
        })
        
    except ImportError:
        # 如果没有psutil，返回基本信息
        return jsonify({
            'cpu_percent': 0,
            'memory_percent': 0,
            'disk_percent': 0,
            'process_memory_mb': 0,
            'scheduler_running': current_app.scheduler.running,
            'worker_count': len(current_app.scheduler.workers),
            'uptime': 'N/A'
        })
    except Exception as e:
        return jsonify({'error': f'获取系统状态失败: {str(e)}'}), 500
