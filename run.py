#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FTP Web System 启动文件
"""

import os
import sys
from app import create_app, socketio

def main():
    """主函数"""
    # 获取配置环境
    config_name = os.environ.get('FLASK_ENV', 'development')
    
    # 创建应用
    app = create_app(config_name)
    
    # 启动应用
    print("FTP Web System 正在启动...")
    print(f"配置环境: {config_name}")
    print(f"数据目录: {app.config['DATA_DIR']}")
    
    try:
        # 使用SocketIO启动应用
        socketio.run(
            app,
            host='0.0.0.0',
            port=5000,
            debug=app.config['DEBUG'],
            allow_unsafe_werkzeug=True
        )
    except KeyboardInterrupt:
        print("\n正在关闭系统...")
    except Exception as e:
        print(f"启动失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
