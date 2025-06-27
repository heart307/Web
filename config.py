import os

class Config:
    """基础配置类"""
    # Flask配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'ftp-web-system-secret-key-2024'
    
    # 数据存储配置
    DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    BACKUP_INTERVAL = 300  # 备份间隔（秒）
    MAX_BACKUPS = 10       # 最大备份数量
    
    # 任务调度配置
    MAX_WORKERS = 3        # 最大工作线程数
    
    # 基础时间片配置（秒）
    BASE_TIME_SLICES = {
        'high': 120,       # 高优先级：2分钟
        'medium': 60,      # 中优先级：1分钟
        'low': 30          # 低优先级：30秒
    }
    
    # 任务类型时间片倍数
    TASK_TYPE_MULTIPLIERS = {
        'file_download': 2.0,      # 文件下载
        'file_upload': 2.0,        # 文件上传
        'folder_download': 2.5,    # 文件夹下载
        'folder_upload': 2.5,      # 文件夹上传
        'folder_monitor': 0.5,     # 文件夹监控
        'folder_sync': 1.5,        # 文件夹同步
        'connection_test': 0.2,    # 连接测试
        'log_cleanup': 0.3         # 日志清理
    }
    
    # FTP配置
    FTP_TIMEOUT = 30       # FTP连接超时（秒）
    FTP_CHUNK_SIZE = 8192  # 传输块大小
    
    # 监控配置
    MONITOR_INTERVAL = 60  # 监控检查间隔（秒）
    
    # 日志配置
    LOG_LEVEL = 'INFO'
    LOG_MAX_SIZE = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5
    
    # 上传配置
    UPLOAD_FOLDER = os.path.join(DATA_DIR, 'uploads')
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    
class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False

# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
