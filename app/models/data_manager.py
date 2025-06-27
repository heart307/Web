#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据持久化管理模块
"""

import json
import os
import threading
import time
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Any

# 尝试导入fcntl，如果失败则设置为None（Windows系统）
try:
    import fcntl
except ImportError:
    fcntl = None

class DataManager:
    """数据管理器 - 负责JSON文件的读写、备份和原子操作"""
    
    def __init__(self, data_dir="data", backup_interval=300):
        self.data_dir = data_dir
        self.backup_interval = backup_interval
        self.lock = threading.RLock()
        
        # 确保数据目录存在
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(f"{data_dir}/logs", exist_ok=True)
        os.makedirs(f"{data_dir}/backups", exist_ok=True)
        
        # 数据文件路径
        self.files = {
            'users': f"{data_dir}/users.json",
            'sites': f"{data_dir}/ftp_sites.json",
            'tasks': f"{data_dir}/transfer_tasks.json",
            'monitors': f"{data_dir}/monitor_tasks.json"
        }
        
        # 初始化数据文件
        self._initialize_data_files()
        
        # 启动定期备份
        self._start_backup_thread()
    
    def _initialize_data_files(self):
        """初始化数据文件"""
        default_data = {
            'users': {
                'users': [
                    {
                        'id': 'admin',
                        'username': 'admin',
                        'password_hash': 'pbkdf2:sha256:260000$8Uw5UJy1$4f45f7ce8a4e5b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c',  # admin123
                        'role': 'super_admin',  # 升级为超级管理员
                        'permissions': {
                            'user_management': True,
                            'site_management': True,
                            'task_management': 'all',
                            'system_config': True,
                            'role_management': True
                        },
                        'settings': {
                            'default_download_path': '/downloads',
                            'max_concurrent_tasks': 3,
                            'allowed_sites': []  # 空数组表示可访问所有站点
                        },
                        'status': 'active',
                        'created_at': datetime.now().isoformat(),
                        'last_login': None,
                        'created_by': 'system'
                    }
                ],
                'user_counter': 1
            },
            'sites': {'sites': [], 'site_counter': 0},
            'tasks': {'tasks': {}, 'task_counter': 0},
            'monitors': {'monitors': [], 'monitor_counter': 0}
        }
        
        for key, filepath in self.files.items():
            if not os.path.exists(filepath):
                self._atomic_write(filepath, default_data[key])
    
    def _atomic_write(self, filepath: str, data: Dict):
        """原子写入文件"""
        temp_file = f"{filepath}.tmp"
        backup_file = f"{filepath}.backup"
        
        try:
            # 写入临时文件
            with open(temp_file, 'w', encoding='utf-8') as f:
                # 在Unix/Linux系统上使用文件锁
                if fcntl and hasattr(fcntl, 'flock'):
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # 备份原文件
            if os.path.exists(filepath):
                shutil.copy2(filepath, backup_file)
            
            # 原子重命名
            if os.name == 'nt':  # Windows
                if os.path.exists(filepath):
                    os.remove(filepath)
            os.rename(temp_file, filepath)
            
        except Exception as e:
            # 清理临时文件
            if os.path.exists(temp_file):
                os.remove(temp_file)
            raise e
    
    def _load_json(self, filepath: str) -> Dict:
        """加载JSON文件"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"加载文件失败 {filepath}: {e}")
            return {}
    
    def save_task(self, task: Dict):
        """保存单个任务"""
        with self.lock:
            try:
                # 加载现有数据
                data = self._load_json(self.files['tasks'])
                if 'tasks' not in data:
                    data['tasks'] = {}

                # 复制任务数据并转换枚举类型为字符串
                task_copy = task.copy()
                if hasattr(task_copy.get('priority'), 'value'):
                    task_copy['priority'] = task_copy['priority'].value
                if hasattr(task_copy.get('status'), 'value'):
                    task_copy['status'] = task_copy['status'].value

                # 更新任务
                data['tasks'][task['id']] = task_copy

                # 保存
                self._atomic_write(self.files['tasks'], data)

            except Exception as e:
                print(f"保存任务失败: {e}")
                import traceback
                traceback.print_exc()

    def delete_task(self, task_id: str) -> bool:
        """删除单个任务"""
        # 简化版本，直接操作文件
        try:
            import json

            # 直接读取文件
            with open(self.files['tasks'], 'r', encoding='utf-8') as f:
                data = json.load(f)

            if 'tasks' not in data or task_id not in data['tasks']:
                return False

            # 删除任务
            del data['tasks'][task_id]

            # 直接写入文件
            with open(self.files['tasks'], 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            print(f"删除任务失败: {e}")
            return False

    def load_tasks(self) -> Dict:
        """加载所有任务"""
        return self._load_json(self.files['tasks'])

    def get_recent_tasks(self, limit: int = 100) -> List[Dict]:
        """获取最近的任务列表"""
        try:
            data = self._load_json(self.files['tasks'])
            tasks = data.get('tasks', {})

            # 转换为列表并按创建时间排序
            task_list = []
            for task_id, task_data in tasks.items():
                task_copy = task_data.copy()
                task_copy['id'] = task_id
                task_list.append(task_copy)

            # 按创建时间排序（最新的在前）
            task_list.sort(key=lambda x: x.get('created_at', ''), reverse=True)

            # 限制数量
            return task_list[:limit]

        except Exception as e:
            print(f"获取最近任务失败: {e}")
            return []
    
    def delete_task(self, task_id: str):
        """删除任务"""
        with self.lock:
            try:
                data = self._load_json(self.files['tasks'])
                if 'tasks' in data and task_id in data['tasks']:
                    del data['tasks'][task_id]
                    self._atomic_write(self.files['tasks'], data)
            except Exception as e:
                print(f"删除任务失败: {e}")
    
    def save_site(self, site: Dict):
        """保存FTP站点"""
        with self.lock:
            try:
                data = self._load_json(self.files['sites'])
                if 'sites' not in data:
                    data['sites'] = []
                
                # 查找并更新或添加
                updated = False
                for i, existing_site in enumerate(data['sites']):
                    if existing_site['id'] == site['id']:
                        data['sites'][i] = site
                        updated = True
                        break
                
                if not updated:
                    data['sites'].append(site)
                    if 'site_counter' not in data:
                        data['site_counter'] = 0
                    data['site_counter'] += 1
                
                self._atomic_write(self.files['sites'], data)
                
            except Exception as e:
                print(f"保存站点失败: {e}")
    
    def load_sites(self) -> List[Dict]:
        """加载所有FTP站点"""
        data = self._load_json(self.files['sites'])
        return data.get('sites', [])
    
    def delete_site(self, site_id: str):
        """删除FTP站点"""
        with self.lock:
            try:
                data = self._load_json(self.files['sites'])
                if 'sites' in data:
                    data['sites'] = [s for s in data['sites'] if s['id'] != site_id]
                    self._atomic_write(self.files['sites'], data)
            except Exception as e:
                print(f"删除站点失败: {e}")
    
    def save_user(self, user: Dict):
        """保存用户"""
        with self.lock:
            try:
                data = self._load_json(self.files['users'])
                if 'users' not in data:
                    data['users'] = []
                
                # 查找并更新或添加
                updated = False
                for i, existing_user in enumerate(data['users']):
                    if existing_user['id'] == user['id']:
                        data['users'][i] = user
                        updated = True
                        break
                
                if not updated:
                    data['users'].append(user)
                    if 'user_counter' not in data:
                        data['user_counter'] = 0
                    data['user_counter'] += 1
                
                self._atomic_write(self.files['users'], data)
                
            except Exception as e:
                print(f"保存用户失败: {e}")
    
    def load_users(self) -> List[Dict]:
        """加载所有用户"""
        data = self._load_json(self.files['users'])
        return data.get('users', [])
    
    def find_user_by_username(self, username: str) -> Optional[Dict]:
        """根据用户名查找用户"""
        users = self.load_users()
        for user in users:
            if user['username'] == username:
                return user
        return None

    def find_user_by_id(self, user_id: str) -> Optional[Dict]:
        """根据用户ID查找用户"""
        users = self.load_users()
        for user in users:
            if user['id'] == user_id:
                return user
        return None

    def delete_user(self, user_id: str) -> bool:
        """删除用户"""
        with self.lock:
            try:
                data = self._load_json(self.files['users'])
                if 'users' not in data:
                    return False

                # 查找要删除的用户
                user_to_delete = None
                for user in data['users']:
                    if user['id'] == user_id:
                        user_to_delete = user
                        break

                if not user_to_delete:
                    return False

                # 不能删除超级管理员
                if user_to_delete['role'] == 'super_admin':
                    return False

                # 从列表中移除用户
                data['users'] = [u for u in data['users'] if u['id'] != user_id]

                self._atomic_write(self.files['users'], data)
                return True

            except Exception as e:
                print(f"删除用户失败: {e}")
                return False

    def update_user_status(self, user_id: str, status: str) -> bool:
        """更新用户状态"""
        with self.lock:
            try:
                data = self._load_json(self.files['users'])
                if 'users' not in data:
                    return False

                # 查找并更新用户状态
                for user in data['users']:
                    if user['id'] == user_id:
                        user['status'] = status
                        self._atomic_write(self.files['users'], data)
                        return True

                return False

            except Exception as e:
                print(f"更新用户状态失败: {e}")
                return False

    def update_user_last_login(self, user_id: str) -> bool:
        """更新用户最后登录时间"""
        with self.lock:
            try:
                data = self._load_json(self.files['users'])
                if 'users' not in data:
                    return False

                # 查找并更新用户最后登录时间
                for user in data['users']:
                    if user['id'] == user_id:
                        user['last_login'] = datetime.now().isoformat()
                        self._atomic_write(self.files['users'], data)
                        return True

                return False

            except Exception as e:
                print(f"更新用户最后登录时间失败: {e}")
                return False

    def get_users_by_role(self, role: str) -> List[Dict]:
        """根据角色获取用户列表"""
        users = self.load_users()
        return [user for user in users if user.get('role') == role]

    def get_active_users(self) -> List[Dict]:
        """获取活跃用户列表"""
        users = self.load_users()
        return [user for user in users if user.get('status', 'active') == 'active']
    
    def save_monitor(self, monitor: Dict):
        """保存监控任务"""
        with self.lock:
            try:
                data = self._load_json(self.files['monitors'])
                if 'monitors' not in data:
                    data['monitors'] = []
                
                # 查找并更新或添加
                updated = False
                for i, existing_monitor in enumerate(data['monitors']):
                    if existing_monitor['id'] == monitor['id']:
                        data['monitors'][i] = monitor
                        updated = True
                        break
                
                if not updated:
                    data['monitors'].append(monitor)
                    if 'monitor_counter' not in data:
                        data['monitor_counter'] = 0
                    data['monitor_counter'] += 1
                
                self._atomic_write(self.files['monitors'], data)
                
            except Exception as e:
                print(f"保存监控任务失败: {e}")
    
    def load_monitors(self) -> List[Dict]:
        """加载所有监控任务"""
        data = self._load_json(self.files['monitors'])
        return data.get('monitors', [])
    
    def write_log(self, log_type: str, log_data: Dict):
        """写入日志"""
        try:
            log_date = datetime.now().strftime("%Y-%m-%d")
            log_dir = f"{self.data_dir}/logs/{log_type}"
            os.makedirs(log_dir, exist_ok=True)
            
            log_file = f"{log_dir}/{log_date}.json"
            
            # 读取现有日志
            logs = []
            if os.path.exists(log_file):
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        logs = json.load(f)
                except:
                    logs = []
            
            # 添加新日志
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                **log_data
            }
            logs.append(log_entry)
            
            # 保存日志
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"写入日志失败: {e}")
    
    def _start_backup_thread(self):
        """启动定期备份线程"""
        def backup_loop():
            while True:
                try:
                    time.sleep(self.backup_interval)
                    self._create_backup()
                except Exception as e:
                    print(f"备份失败: {e}")
        
        backup_thread = threading.Thread(target=backup_loop, daemon=True)
        backup_thread.start()
        print(f"启动定期备份线程，间隔: {self.backup_interval}秒")
    
    def _create_backup(self):
        """创建数据备份"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = f"{self.data_dir}/backups/{timestamp}"
            
            os.makedirs(backup_dir, exist_ok=True)
            
            # 备份所有数据文件
            for filename, filepath in self.files.items():
                if os.path.exists(filepath):
                    shutil.copy2(filepath, f"{backup_dir}/{filename}.json")
            
            print(f"创建备份: {backup_dir}")
            
            # 清理旧备份
            self._cleanup_old_backups()
            
        except Exception as e:
            print(f"创建备份失败: {e}")
    
    def _cleanup_old_backups(self):
        """清理旧备份"""
        try:
            backup_base = f"{self.data_dir}/backups"
            if not os.path.exists(backup_base):
                return
            
            backups = sorted([d for d in os.listdir(backup_base) 
                             if os.path.isdir(os.path.join(backup_base, d))])
            
            # 保留最近10个备份
            while len(backups) > 10:
                old_backup = backups.pop(0)
                old_backup_path = os.path.join(backup_base, old_backup)
                shutil.rmtree(old_backup_path)
                print(f"删除旧备份: {old_backup}")
                
        except Exception as e:
            print(f"清理备份失败: {e}")
    
    def get_next_id(self, data_type: str) -> str:
        """获取下一个ID"""
        with self.lock:
            try:
                data = self._load_json(self.files[data_type])
                counter_key = f"{data_type[:-1]}_counter"  # users -> user_counter
                
                if counter_key not in data:
                    data[counter_key] = 0
                
                data[counter_key] += 1
                next_id = f"{data_type[:-1]}_{data[counter_key]:06d}"
                
                self._atomic_write(self.files[data_type], data)
                return next_id
                
            except Exception as e:
                print(f"获取下一个ID失败: {e}")
                return f"{data_type[:-1]}_{int(time.time())}"
