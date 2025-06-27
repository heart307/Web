#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FTP Web System 应用初始化
"""

import os
from flask import Flask
from flask_socketio import SocketIO
from config import config

# 全局SocketIO实例
socketio = SocketIO()

def create_app(config_name='default'):
    """应用工厂函数"""
    # 设置模板和静态文件目录
    import os
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
    static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static'))

    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    
    # 加载配置
    app.config.from_object(config[config_name])
    
    # 确保数据目录存在
    os.makedirs(app.config['DATA_DIR'], exist_ok=True)
    os.makedirs(os.path.join(app.config['DATA_DIR'], 'logs'), exist_ok=True)
    os.makedirs(os.path.join(app.config['DATA_DIR'], 'backups'), exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # 初始化SocketIO
    socketio.init_app(app, cors_allowed_origins="*")
    
    # 注册蓝图
    from app.views.auth import auth_bp
    from app.views.dashboard import dashboard_bp
    from app.views.sites import sites_bp
    from app.views.tasks import tasks_bp
    from app.views.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(sites_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(api_bp)

    # 添加根路由
    @app.route('/')
    def index():
        from flask import session, redirect, url_for
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return redirect(url_for('dashboard.index'))
    
    # 初始化核心组件
    try:
        print("正在初始化核心组件...")
        from app.core.scheduler import DynamicTimeSliceScheduler
        from app.models.data_manager import DataManager
        from app.services.task_service import TaskService

        # 创建全局实例
        print("创建数据管理器...")
        data_manager = DataManager(app.config['DATA_DIR'])

        print("创建调度器...")
        scheduler = DynamicTimeSliceScheduler(
            max_workers=app.config['MAX_WORKERS'],
            data_manager=data_manager
        )

        print("创建任务服务...")
        task_service = TaskService(scheduler, data_manager)

        print("创建连接测试服务...")
        from app.services.connection_service import ConnectionTestService
        connection_service = ConnectionTestService(data_manager, max_concurrent_tests=3)

        # 将实例添加到应用上下文
        app.data_manager = data_manager
        app.scheduler = scheduler
        app.task_service = task_service
        app.connection_service = connection_service

        # 注册任务函数
        print("注册任务函数...")
        task_service.register_all_functions()

        # 启动调度器
        print("启动调度器...")
        scheduler.start_workers()

        # 恢复未完成的任务
        print("恢复未完成的任务...")
        task_service.restore_unfinished_tasks()

        print("核心组件初始化完成!")

    except Exception as e:
        print(f"初始化核心组件失败: {e}")
        import traceback
        traceback.print_exc()
    
    return app
