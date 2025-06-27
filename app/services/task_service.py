#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务服务层 - 实现各种FTP任务函数
"""

import os
import time
import glob
from datetime import datetime
from typing import Dict, List, Optional, Any
from app.core.ftp_client import FTPClient

class TaskService:
    """任务服务 - 管理和执行各种FTP任务"""
    
    def __init__(self, scheduler, data_manager):
        self.scheduler = scheduler
        self.data_manager = data_manager
    
    def register_all_functions(self):
        """注册所有任务函数"""
        self.scheduler.register_function('file_download', self.file_download_task)
        self.scheduler.register_function('file_upload', self.file_upload_task)
        self.scheduler.register_function('folder_download', self.folder_download_task)
        self.scheduler.register_function('folder_upload', self.folder_upload_task)
        self.scheduler.register_function('folder_monitor', self.folder_monitor_task)
        self.scheduler.register_function('connection_test', self.connection_test_task)
        print("所有任务函数注册完成")
    
    def restore_unfinished_tasks(self):
        """恢复未完成的任务"""
        try:
            tasks_data = self.data_manager.load_tasks()
            self.scheduler.restore_tasks(tasks_data)
        except Exception as e:
            print(f"恢复任务失败: {e}")
    
    def create_ftp_client(self, site_config: Dict) -> FTPClient:
        """创建FTP客户端"""
        # 解密密码
        encrypted_password = site_config.get('password', '')
        password = self._decrypt_password(encrypted_password) if encrypted_password else ''

        return FTPClient(
            host=site_config['host'],
            port=site_config.get('port', 21),
            username=site_config.get('username', ''),
            password=password,
            timeout=site_config.get('timeout', 30)
        )

    def _decrypt_password(self, encrypted: str) -> str:
        """解密密码"""
        try:
            import base64
            return base64.b64decode(encrypted.encode()).decode()
        except:
            return encrypted

    def _validate_local_path(self, local_path: str) -> str:
        """验证并处理本地路径"""
        import os

        # 处理Unix风格路径
        if local_path.startswith('/'):
            local_path = local_path.lstrip('/')
            local_path = os.path.join(os.getcwd(), local_path)

        # 获取目录路径
        if not os.path.splitext(local_path)[1] or local_path.endswith(('/', '\\')):
            # 是目录路径
            dir_path = local_path
        else:
            # 是文件路径
            dir_path = os.path.dirname(local_path)

        # 检查目录是否可以创建
        if dir_path:
            try:
                # 尝试创建目录
                os.makedirs(dir_path, exist_ok=True)

                # 检查目录是否可写
                if not os.access(dir_path, os.W_OK):
                    raise Exception(f"目录不可写: {dir_path}")

            except PermissionError:
                raise Exception(f"没有权限创建目录: {dir_path}")
            except OSError as e:
                raise Exception(f"无法创建目录 {dir_path}: {str(e)}")

        return local_path
    
    def file_download_task(self, task_id: str, time_slice: float, scheduler,
                          site_config: Dict, remote_path: str, local_path: str) -> str:
        """文件下载任务"""
        print(f"开始文件下载任务: {remote_path} -> {local_path}")

        # 处理本地路径
        import os
        if local_path.startswith('/'):
            # Unix风格路径，转换为当前目录下的相对路径
            local_path = local_path.lstrip('/')
            local_path = os.path.join(os.getcwd(), local_path)

        # 构建完整的本地文件路径
        filename = os.path.basename(remote_path)

        # 判断local_path是目录还是文件路径
        # 如果没有扩展名或者以/结尾，认为是目录
        if not os.path.splitext(local_path)[1] or local_path.endswith(('/', '\\')):
            # 是目录路径，需要添加文件名
            local_file_path = os.path.join(local_path, filename)
        else:
            # 是文件路径，直接使用
            local_file_path = local_path

        # 确保本地目录存在
        local_dir = os.path.dirname(local_file_path)
        if local_dir:
            os.makedirs(local_dir, exist_ok=True)

        print(f"本地文件路径: {local_file_path}")

        # 获取任务的检查点数据
        task = scheduler.get_task_status(task_id)
        checkpoint = task.get('checkpoint_data', {}) if task else {}
        start_byte = checkpoint.get('downloaded_bytes', 0)

        # 创建FTP客户端
        ftp_client = self.create_ftp_client(site_config)
        
        if not ftp_client.connect():
            error_msg = ftp_client.last_error or "连接失败"
            print(f"FTP连接失败: {error_msg}")
            raise Exception(f"无法连接到FTP服务器: {error_msg}")

        print(f"FTP连接成功: {site_config['host']}:{site_config.get('port', 21)}")
        
        try:
            start_time = time.time()
            
            def progress_callback(progress, downloaded, total):
                # 检查是否超时
                if time.time() - start_time >= time_slice:
                    return False  # 停止传输
                
                # 更新进度
                scheduler.update_task_progress(task_id, progress, {
                    'downloaded_bytes': downloaded,
                    'total_bytes': total,
                    'last_update': datetime.now().isoformat()
                })
                return True
            
            # 检查远程文件是否存在
            remote_size = ftp_client.get_file_size(remote_path)
            if remote_size is None:
                raise Exception(f"远程文件不存在或无法访问: {remote_path}")

            print(f"远程文件大小: {remote_size} 字节")
            print(f"开始下载: {remote_path} -> {local_file_path}")

            # 执行下载
            success = ftp_client.download_file(
                remote_path, local_file_path,
                progress_callback=progress_callback,
                start_byte=start_byte
            )

            print(f"下载结果: {success}")
            
            if success:
                # 检查文件是否完整下载
                if os.path.exists(local_file_path):
                    local_size = os.path.getsize(local_file_path)
                    remote_size = ftp_client.get_file_size(remote_path)

                    if remote_size and local_size >= remote_size:
                        # 下载完成
                        self._log_transfer('download', {
                            'task_id': task_id,
                            'remote_path': remote_path,
                            'local_path': local_file_path,
                            'file_size': local_size,
                            'status': 'completed'
                        })
                        return f"文件下载完成: {local_file_path}"
                    else:
                        # 部分下载，需要继续
                        return "TIMEOUT"
                else:
                    raise Exception(f"下载失败，本地文件不存在: {local_file_path}")
            else:
                error_msg = ftp_client.last_error or "未知错误"
                raise Exception(f"下载失败: {error_msg}")
                
        finally:
            ftp_client.disconnect()
    
    def file_upload_task(self, task_id: str, time_slice: float, scheduler,
                        site_config: Dict, local_path: str, remote_path: str) -> str:
        """文件上传任务"""
        print(f"开始文件上传任务: {local_path} -> {remote_path}")
        
        if not os.path.exists(local_path):
            raise Exception(f"本地文件不存在: {local_path}")
        
        # 获取任务的检查点数据
        task = scheduler.get_task_status(task_id)
        checkpoint = task.get('checkpoint_data', {}) if task else {}
        start_byte = checkpoint.get('uploaded_bytes', 0)
        
        # 创建FTP客户端
        ftp_client = self.create_ftp_client(site_config)
        
        if not ftp_client.connect():
            raise Exception(f"无法连接到FTP服务器: {ftp_client.last_error}")
        
        try:
            start_time = time.time()
            local_size = os.path.getsize(local_path)
            
            def progress_callback(progress, uploaded, total):
                # 检查是否超时
                if time.time() - start_time >= time_slice:
                    return False  # 停止传输
                
                # 更新进度
                scheduler.update_task_progress(task_id, progress, {
                    'uploaded_bytes': uploaded,
                    'total_bytes': total,
                    'last_update': datetime.now().isoformat()
                })
                return True
            
            # 执行上传
            success = ftp_client.upload_file(
                local_path, remote_path,
                progress_callback=progress_callback,
                start_byte=start_byte
            )
            
            if success:
                # 检查文件是否完整上传
                remote_size = ftp_client.get_file_size(remote_path)
                
                if remote_size and remote_size >= local_size:
                    # 上传完成
                    self._log_transfer('upload', {
                        'task_id': task_id,
                        'local_path': local_path,
                        'remote_path': remote_path,
                        'file_size': local_size,
                        'status': 'completed'
                    })
                    return f"文件上传完成: {remote_path}"
                else:
                    # 部分上传，需要继续
                    return "TIMEOUT"
            else:
                raise Exception(f"上传失败: {ftp_client.last_error}")
                
        finally:
            ftp_client.disconnect()
    
    def folder_download_task(self, task_id: str, time_slice: float, scheduler,
                           site_config: Dict, remote_path: str, local_path: str) -> str:
        """文件夹下载任务"""
        print(f"开始文件夹下载任务: {remote_path} -> {local_path}")
        
        # 获取任务的检查点数据
        task = scheduler.get_task_status(task_id)
        checkpoint = task.get('checkpoint_data', {}) if task else {}
        processed_files = checkpoint.get('processed_files', [])
        
        # 创建FTP客户端
        ftp_client = self.create_ftp_client(site_config)
        
        if not ftp_client.connect():
            raise Exception(f"无法连接到FTP服务器: {ftp_client.last_error}")
        
        try:
            start_time = time.time()
            
            # 获取远程目录文件列表
            files = ftp_client.list_directory(remote_path)
            total_files = len([f for f in files if not f['is_directory']])
            
            if total_files == 0:
                return "文件夹为空或无文件需要下载"
            
            downloaded_count = len(processed_files)
            
            for file_info in files:
                # 检查时间片
                if time.time() - start_time >= time_slice:
                    return "TIMEOUT"
                
                if file_info['is_directory']:
                    continue
                
                file_name = file_info['name']
                if file_name in processed_files:
                    continue
                
                remote_file_path = f"{remote_path.rstrip('/')}/{file_name}"
                local_file_path = os.path.join(local_path, file_name)
                
                # 下载单个文件
                success = ftp_client.download_file(remote_file_path, local_file_path)
                
                if success:
                    processed_files.append(file_name)
                    downloaded_count += 1
                    
                    # 更新进度
                    progress = (downloaded_count / total_files) * 100
                    scheduler.update_task_progress(task_id, progress, {
                        'processed_files': processed_files,
                        'downloaded_count': downloaded_count,
                        'total_files': total_files
                    })
                else:
                    print(f"下载文件失败: {remote_file_path}")
            
            if downloaded_count >= total_files:
                self._log_transfer('folder_download', {
                    'task_id': task_id,
                    'remote_path': remote_path,
                    'local_path': local_path,
                    'file_count': downloaded_count,
                    'status': 'completed'
                })
                return f"文件夹下载完成: {downloaded_count} 个文件"
            else:
                return "TIMEOUT"
                
        finally:
            ftp_client.disconnect()
    
    def folder_upload_task(self, task_id: str, time_slice: float, scheduler,
                          site_config: Dict, local_path: str, remote_path: str) -> str:
        """文件夹上传任务"""
        print(f"开始文件夹上传任务: {local_path} -> {remote_path}")
        
        if not os.path.exists(local_path):
            raise Exception(f"本地文件夹不存在: {local_path}")
        
        # 获取任务的检查点数据
        task = scheduler.get_task_status(task_id)
        checkpoint = task.get('checkpoint_data', {}) if task else {}
        processed_files = checkpoint.get('processed_files', [])
        
        # 创建FTP客户端
        ftp_client = self.create_ftp_client(site_config)
        
        if not ftp_client.connect():
            raise Exception(f"无法连接到FTP服务器: {ftp_client.last_error}")
        
        try:
            start_time = time.time()
            
            # 获取本地文件列表
            local_files = []
            for root, dirs, files in os.walk(local_path):
                for file in files:
                    local_file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(local_file_path, local_path)
                    local_files.append((local_file_path, rel_path))
            
            total_files = len(local_files)
            if total_files == 0:
                return "文件夹为空或无文件需要上传"
            
            uploaded_count = len(processed_files)
            
            for local_file_path, rel_path in local_files:
                # 检查时间片
                if time.time() - start_time >= time_slice:
                    return "TIMEOUT"
                
                if rel_path in processed_files:
                    continue
                
                remote_file_path = f"{remote_path.rstrip('/')}/{rel_path.replace(os.sep, '/')}"
                
                # 上传单个文件
                success = ftp_client.upload_file(local_file_path, remote_file_path)
                
                if success:
                    processed_files.append(rel_path)
                    uploaded_count += 1
                    
                    # 更新进度
                    progress = (uploaded_count / total_files) * 100
                    scheduler.update_task_progress(task_id, progress, {
                        'processed_files': processed_files,
                        'uploaded_count': uploaded_count,
                        'total_files': total_files
                    })
                else:
                    print(f"上传文件失败: {local_file_path}")
            
            if uploaded_count >= total_files:
                self._log_transfer('folder_upload', {
                    'task_id': task_id,
                    'local_path': local_path,
                    'remote_path': remote_path,
                    'file_count': uploaded_count,
                    'status': 'completed'
                })
                return f"文件夹上传完成: {uploaded_count} 个文件"
            else:
                return "TIMEOUT"
                
        finally:
            ftp_client.disconnect()

    def folder_monitor_task(self, task_id: str, time_slice: float, scheduler,
                           monitor_config: Dict) -> str:
        """文件夹监控任务 - 整体下载文件夹并监控新文件"""
        site_config = monitor_config['site_config']
        remote_path = monitor_config['remote_path']
        local_path = monitor_config['local_path']
        file_pattern = monitor_config.get('file_pattern', '*')
        priority = monitor_config.get('priority', 'medium')

        print(f"开始文件夹监控任务: {remote_path} -> {local_path}")

        # 构建本地文件夹路径（保持远程文件夹结构）
        import os
        remote_folder_name = os.path.basename(remote_path.rstrip('/')) or 'root'
        local_folder_path = os.path.join(local_path, remote_folder_name)

        # 确保本地目录存在
        os.makedirs(local_folder_path, exist_ok=True)
        print(f"本地文件夹路径: {local_folder_path}")

        # 获取监控任务的历史文件列表
        monitor_id = monitor_config.get('monitor_id')
        monitors = self.data_manager.load_monitors()

        known_files = []
        is_first_run = True
        for monitor in monitors:
            if monitor.get('id') == monitor_id:
                known_files = monitor.get('file_list', [])
                is_first_run = len(known_files) == 0
                break

        # 创建FTP客户端
        ftp_client = self.create_ftp_client(site_config)

        if not ftp_client.connect():
            raise Exception(f"无法连接到FTP服务器: {ftp_client.last_error}")

        try:
            # 获取当前远程目录文件列表
            current_files = ftp_client.list_directory(remote_path)
            current_file_names = [f['name'] for f in current_files if not f['is_directory']]

            # 确定要下载的文件
            files_to_download = []
            if is_first_run:
                # 首次运行：下载所有匹配的文件
                print("首次运行，下载整个文件夹")
                for file_name in current_file_names:
                    import fnmatch
                    if fnmatch.fnmatch(file_name, file_pattern):
                        files_to_download.append(file_name)
            else:
                # 后续运行：只下载新增的文件
                print("监控模式，检查新增文件")
                for file_name in current_file_names:
                    if file_name not in known_files:
                        import fnmatch
                        if fnmatch.fnmatch(file_name, file_pattern):
                            files_to_download.append(file_name)

            # 直接在监控任务中下载文件
            downloaded_files = 0
            failed_files = 0
            start_time = time.time()

            for file_name in files_to_download:
                # 检查时间片
                if time.time() - start_time >= time_slice:
                    # 时间片用完，更新进度并返回TIMEOUT
                    progress = (downloaded_files / len(files_to_download)) * 100 if files_to_download else 100
                    scheduler.update_task_progress(task_id, progress, {
                        'downloaded_files': downloaded_files,
                        'total_files': len(files_to_download),
                        'current_file': file_name,
                        'failed_files': failed_files
                    })
                    return "TIMEOUT"

                remote_file_path = f"{remote_path.rstrip('/')}/{file_name}"
                local_file_path = os.path.join(local_folder_path, file_name)

                # 直接下载文件
                try:
                    success = ftp_client.download_file(remote_file_path, local_file_path)
                    if success:
                        downloaded_files += 1
                        if is_first_run:
                            print(f"首次下载文件成功: {file_name}")
                        else:
                            print(f"监控下载新文件成功: {file_name}")
                    else:
                        failed_files += 1
                        print(f"下载文件失败: {file_name}")
                except Exception as e:
                    failed_files += 1
                    print(f"下载文件异常: {file_name} - {e}")

                # 更新进度
                progress = (downloaded_files / len(files_to_download)) * 100 if files_to_download else 100
                scheduler.update_task_progress(task_id, progress, {
                    'downloaded_files': downloaded_files,
                    'total_files': len(files_to_download),
                    'current_file': file_name,
                    'failed_files': failed_files
                })

            # 更新监控任务的文件列表
            if files_to_download or is_first_run:
                for monitor in monitors:
                    if monitor.get('id') == monitor_id:
                        monitor['file_list'] = current_file_names
                        monitor['last_check'] = datetime.now().isoformat()
                        self.data_manager.save_monitor(monitor)
                        break

            # 记录监控日志
            self._log_monitor('folder_monitor', {
                'monitor_id': monitor_id,
                'remote_path': remote_path,
                'local_path': local_folder_path,
                'is_first_run': is_first_run,
                'files_to_download': len(files_to_download),
                'downloaded_files': downloaded_files,
                'failed_files': failed_files,
                'total_files': len(current_file_names)
            })

            # 文件夹监控任务需要持续运行，返回特殊状态
            message = ""
            if is_first_run:
                message = f"首次监控完成: 下载整个文件夹，成功 {downloaded_files} 个，失败 {failed_files} 个，共 {len(files_to_download)} 个文件"
            else:
                message = f"监控完成: 发现 {len(files_to_download)} 个新文件，成功下载 {downloaded_files} 个，失败 {failed_files} 个"

            # 返回RESCHEDULE表示需要重新调度此任务（持续监控）
            return "RESCHEDULE:" + message

        finally:
            ftp_client.disconnect()

    def connection_test_task(self, task_id: str, time_slice: float, scheduler,
                           site_config: Dict) -> str:
        """连接测试任务"""
        print(f"开始连接测试: {site_config['host']}")

        # 创建FTP客户端
        ftp_client = self.create_ftp_client(site_config)

        start_time = time.time()

        if ftp_client.connect():
            # 测试基本操作
            try:
                current_dir = ftp_client.get_current_directory()
                files = ftp_client.list_directory()

                connection_time = time.time() - start_time

                # 更新站点状态
                sites = self.data_manager.load_sites()
                for site in sites:
                    if site['id'] == site_config.get('id'):
                        site['status'] = 'connected'
                        site['last_check'] = datetime.now().isoformat()
                        site['connection_time'] = connection_time
                        self.data_manager.save_site(site)
                        break

                self._log_system('connection_test', {
                    'site_id': site_config.get('id'),
                    'host': site_config['host'],
                    'status': 'success',
                    'connection_time': connection_time,
                    'current_dir': current_dir,
                    'file_count': len(files)
                })

                return f"连接测试成功: {site_config['host']} (耗时: {connection_time:.2f}秒)"

            finally:
                ftp_client.disconnect()
        else:
            # 连接失败
            sites = self.data_manager.load_sites()
            for site in sites:
                if site['id'] == site_config.get('id'):
                    site['status'] = 'disconnected'
                    site['last_check'] = datetime.now().isoformat()
                    site['last_error'] = ftp_client.last_error
                    self.data_manager.save_site(site)
                    break

            self._log_system('connection_test', {
                'site_id': site_config.get('id'),
                'host': site_config['host'],
                'status': 'failed',
                'error': ftp_client.last_error
            })

            raise Exception(f"连接测试失败: {ftp_client.last_error}")

    def _log_transfer(self, log_type: str, data: Dict):
        """记录传输日志"""
        try:
            self.data_manager.write_log('transfer', {
                'type': log_type,
                **data
            })
        except Exception as e:
            print(f"写入传输日志失败: {e}")

    def _log_monitor(self, log_type: str, data: Dict):
        """记录监控日志"""
        try:
            self.data_manager.write_log('monitor', {
                'type': log_type,
                **data
            })
        except Exception as e:
            print(f"写入监控日志失败: {e}")

    def _log_system(self, log_type: str, data: Dict):
        """记录系统日志"""
        try:
            self.data_manager.write_log('system', {
                'type': log_type,
                **data
            })
        except Exception as e:
            print(f"写入系统日志失败: {e}")

    # 任务管理方法
    def submit_file_download(self, site_id: str, remote_path: str, local_path: str,
                           priority: str = 'medium', created_by: str = 'user') -> str:
        """提交文件下载任务"""
        # 验证本地路径
        validated_path = self._validate_local_path(local_path)

        # 获取站点配置
        sites = self.data_manager.load_sites()
        site_config = None
        for site in sites:
            if site['id'] == site_id:
                site_config = site
                break

        if not site_config:
            raise Exception(f"站点不存在: {site_id}")

        # 创建任务
        task_data = {
            'func_name': 'file_download',
            'args': [site_config, remote_path, validated_path],
            'priority': priority,
            'task_type': 'file_download',
            'created_by': created_by,
            'site_id': site_id,
            'site_name': site_config.get('name', site_config.get('host', '未知站点')),
            'remote_path': remote_path,
            'local_path': validated_path
        }

        # 尝试获取文件大小
        try:
            ftp_client = self.create_ftp_client(site_config)
            if ftp_client.connect():
                file_size = ftp_client.get_file_size(remote_path)
                if file_size:
                    task_data['file_size'] = file_size
                ftp_client.disconnect()
        except:
            pass

        return self.scheduler.add_task(task_data)

    def submit_file_upload(self, site_id: str, local_path: str, remote_path: str,
                          priority: str = 'medium', created_by: str = 'user') -> str:
        """提交文件上传任务"""
        # 获取站点配置
        sites = self.data_manager.load_sites()
        site_config = None
        for site in sites:
            if site['id'] == site_id:
                site_config = site
                break

        if not site_config:
            raise Exception(f"站点不存在: {site_id}")

        if not os.path.exists(local_path):
            raise Exception(f"本地文件不存在: {local_path}")

        # 创建任务
        task_data = {
            'func_name': 'file_upload',
            'args': [site_config, local_path, remote_path],
            'priority': priority,
            'task_type': 'file_upload',
            'file_size': os.path.getsize(local_path),
            'created_by': created_by
        }

        return self.scheduler.add_task(task_data)

    def submit_folder_download(self, site_id: str, remote_path: str, local_path: str,
                             priority: str = 'medium', created_by: str = 'user') -> str:
        """提交文件夹下载任务"""
        # 验证本地路径
        validated_path = self._validate_local_path(local_path)

        # 获取站点配置
        sites = self.data_manager.load_sites()
        site_config = None
        for site in sites:
            if site['id'] == site_id:
                site_config = site
                break

        if not site_config:
            raise Exception(f"站点不存在: {site_id}")

        # 创建任务
        task_data = {
            'func_name': 'folder_download',
            'args': [site_config, remote_path, validated_path],
            'priority': priority,
            'task_type': 'folder_download',
            'created_by': created_by,
            'site_id': site_id,
            'site_name': site_config.get('name', site_config.get('host', '未知站点')),
            'remote_path': remote_path,
            'local_path': validated_path
        }

        return self.scheduler.add_task(task_data)

    def submit_folder_upload(self, site_id: str, local_path: str, remote_path: str,
                           priority: str = 'medium', created_by: str = 'user') -> str:
        """提交文件夹上传任务"""
        # 获取站点配置
        sites = self.data_manager.load_sites()
        site_config = None
        for site in sites:
            if site['id'] == site_id:
                site_config = site
                break

        if not site_config:
            raise Exception(f"站点不存在: {site_id}")

        if not os.path.exists(local_path):
            raise Exception(f"本地文件夹不存在: {local_path}")

        # 创建任务
        task_data = {
            'func_name': 'folder_upload',
            'args': [site_config, local_path, remote_path],
            'priority': priority,
            'task_type': 'folder_upload',
            'created_by': created_by
        }

        return self.scheduler.add_task(task_data)

    def submit_folder_monitor(self, site_id: str, remote_path: str, local_path: str,
                            monitor_interval: int = 300, file_filter: str = '',
                            priority: str = 'medium', created_by: str = 'user') -> str:
        """提交文件夹监控任务"""
        # 验证本地路径
        validated_path = self._validate_local_path(local_path)

        # 获取站点配置
        sites = self.data_manager.load_sites()
        site_config = None
        for site in sites:
            if site['id'] == site_id:
                site_config = site
                break

        if not site_config:
            raise Exception(f"站点不存在: {site_id}")

        # 创建监控记录
        monitor_id = f"monitor_{int(time.time() * 1000)}"
        monitor_record = {
            'id': monitor_id,
            'name': f"监控_{remote_path}",
            'site_id': site_id,
            'remote_path': remote_path,
            'local_path': validated_path,
            'priority': priority,
            'file_pattern': file_filter or '*',
            'check_interval': monitor_interval,
            'status': 'active',
            'last_check': None,
            'file_list': [],  # 空列表表示首次运行
            'created_by': created_by,
            'created_at': datetime.now().isoformat()
        }

        # 保存监控记录
        self.data_manager.save_monitor(monitor_record)

        # 创建监控配置
        monitor_config = {
            'monitor_id': monitor_id,
            'site_config': site_config,
            'remote_path': remote_path,
            'local_path': validated_path,
            'file_pattern': file_filter or '*',
            'monitor_interval': monitor_interval,
            'priority': priority
        }

        # 创建任务
        task_data = {
            'func_name': 'folder_monitor',
            'args': [monitor_config],
            'priority': priority,
            'task_type': 'folder_monitor',
            'created_by': created_by,
            'monitor_interval': monitor_interval,
            'site_id': site_id,
            'site_name': site_config.get('name', site_config.get('host', '未知站点')),
            'remote_path': remote_path,
            'local_path': validated_path
        }

        return self.scheduler.add_task(task_data)

    def submit_connection_test(self, site_id: str, created_by: str = 'user') -> str:
        """提交连接测试任务"""
        # 获取站点配置
        sites = self.data_manager.load_sites()
        site_config = None
        for site in sites:
            if site['id'] == site_id:
                site_config = site
                break

        if not site_config:
            raise Exception(f"站点不存在: {site_id}")

        # 创建任务
        task_data = {
            'func_name': 'connection_test',
            'args': [site_config],
            'priority': 'high',  # 连接测试使用高优先级
            'task_type': 'connection_test',
            'created_by': created_by
        }

        return self.scheduler.add_task(task_data)
