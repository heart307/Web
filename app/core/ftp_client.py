#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FTP客户端封装
"""

import ftplib
import os
import time
import socket
from typing import Optional, Callable, Dict, Any, List

class FTPClient:
    """FTP客户端 - 支持连接管理、文件传输和断点续传"""
    
    def __init__(self, host: str, port: int = 21, username: str = "", 
                 password: str = "", timeout: int = 30):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        self.ftp = None
        self.connected = False
        self.last_error = None
    
    def connect(self) -> bool:
        """连接到FTP服务器"""
        try:
            self.ftp = ftplib.FTP()
            self.ftp.connect(self.host, self.port, self.timeout)
            
            if self.username:
                self.ftp.login(self.username, self.password)
            else:
                self.ftp.login()  # 匿名登录
            
            # 设置为被动模式
            self.ftp.set_pasv(True)
            
            self.connected = True
            self.last_error = None
            print(f"FTP连接成功: {self.host}:{self.port}")
            return True
            
        except Exception as e:
            self.last_error = str(e)
            print(f"FTP连接失败: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """断开FTP连接"""
        if self.ftp:
            try:
                self.ftp.quit()
            except:
                try:
                    self.ftp.close()
                except:
                    pass
            finally:
                self.ftp = None
                self.connected = False
                print(f"FTP连接已断开: {self.host}")
    
    def test_connection(self) -> bool:
        """测试连接状态"""
        if not self.connected or not self.ftp:
            return False
        
        try:
            # 发送NOOP命令测试连接
            self.ftp.voidcmd("NOOP")
            return True
        except:
            self.connected = False
            return False
    
    def ensure_connected(self) -> bool:
        """确保连接有效，如果断开则重新连接"""
        if self.test_connection():
            return True
        
        print("FTP连接已断开，尝试重新连接...")
        return self.connect()
    
    def get_file_size(self, remote_path: str) -> Optional[int]:
        """获取远程文件大小"""
        if not self.ensure_connected():
            return None

        try:
            # 首先尝试使用SIZE命令（二进制模式）
            self.ftp.voidcmd('TYPE I')  # 切换到二进制模式
            return self.ftp.size(remote_path)
        except Exception as e:
            print(f"SIZE命令失败: {e}")
            # 如果SIZE命令失败，尝试通过列表目录获取文件大小
            try:
                # 获取文件所在目录和文件名
                import os
                dir_path = os.path.dirname(remote_path).replace('\\', '/') or '.'
                filename = os.path.basename(remote_path)

                # 列出目录内容
                files = self.list_directory(dir_path)
                for file_info in files:
                    if file_info['name'] == filename and not file_info['is_directory']:
                        return file_info.get('size')

                print(f"文件不存在: {remote_path}")
                return None
            except Exception as e2:
                print(f"通过目录列表获取文件大小失败: {e2}")
                return None
    
    def file_exists(self, remote_path: str) -> bool:
        """检查远程文件是否存在"""
        if not self.ensure_connected():
            return False

        try:
            # 尝试使用SIZE命令检查文件
            self.ftp.voidcmd('TYPE I')  # 切换到二进制模式
            self.ftp.size(remote_path)
            return True
        except:
            # 如果SIZE命令失败，尝试通过列表目录检查
            try:
                import os
                dir_path = os.path.dirname(remote_path).replace('\\', '/') or '.'
                filename = os.path.basename(remote_path)

                files = self.list_directory(dir_path)
                for file_info in files:
                    if file_info['name'] == filename:
                        return True
                return False
            except:
                return False
    
    def list_directory(self, remote_path: str = ".") -> List[Dict]:
        """列出目录内容"""
        if not self.ensure_connected():
            return []
        
        try:
            files = []
            
            def parse_line(line):
                # 解析LIST命令的输出
                parts = line.split()
                if len(parts) >= 9:
                    permissions = parts[0]
                    size = parts[4] if parts[4].isdigit() else 0
                    name = " ".join(parts[8:])
                    
                    is_dir = permissions.startswith('d')
                    
                    files.append({
                        'name': name,
                        'size': int(size) if not is_dir else 0,
                        'is_directory': is_dir,
                        'permissions': permissions,
                        'raw_line': line
                    })
            
            self.ftp.retrlines(f'LIST {remote_path}', parse_line)
            return files
            
        except Exception as e:
            print(f"列出目录失败: {e}")
            return []
    
    def change_directory(self, remote_path: str) -> bool:
        """切换目录"""
        if not self.ensure_connected():
            return False
        
        try:
            self.ftp.cwd(remote_path)
            return True
        except Exception as e:
            print(f"切换目录失败: {e}")
            return False
    
    def get_current_directory(self) -> Optional[str]:
        """获取当前目录"""
        if not self.ensure_connected():
            return None
        
        try:
            return self.ftp.pwd()
        except Exception as e:
            print(f"获取当前目录失败: {e}")
            return None
    
    def create_directory(self, remote_path: str) -> bool:
        """创建远程目录"""
        if not self.ensure_connected():
            return False
        
        try:
            self.ftp.mkd(remote_path)
            return True
        except Exception as e:
            print(f"创建目录失败: {e}")
            return False
    
    def ensure_remote_directory(self, remote_path: str) -> bool:
        """确保远程目录存在"""
        if not remote_path or remote_path == '/':
            return True
        
        # 分解路径
        path_parts = remote_path.strip('/').split('/')
        current_path = ''
        
        for part in path_parts:
            current_path += '/' + part
            
            # 尝试切换到目录
            if not self.change_directory(current_path):
                # 目录不存在，尝试创建
                if not self.create_directory(current_path):
                    return False
        
        return True
    
    def download_file(self, remote_path: str, local_path: str, 
                     progress_callback: Optional[Callable] = None,
                     start_byte: int = 0) -> bool:
        """下载文件（支持断点续传）"""
        if not self.ensure_connected():
            return False
        
        try:
            # 获取远程文件大小
            remote_size = self.get_file_size(remote_path)
            if remote_size is None:
                print(f"无法获取远程文件大小: {remote_path}")
                return False
            
            # 确保本地目录存在
            local_dir = os.path.dirname(local_path)
            if local_dir:
                os.makedirs(local_dir, exist_ok=True)
            
            # 检查本地文件是否已存在
            if start_byte == 0 and os.path.exists(local_path):
                local_size = os.path.getsize(local_path)
                if local_size == remote_size:
                    print(f"文件已存在且大小相同，跳过下载: {local_path}")
                    if progress_callback:
                        progress_callback(100.0, remote_size, remote_size)
                    return True
                elif local_size < remote_size:
                    # 支持断点续传
                    start_byte = local_size
                    print(f"检测到部分下载文件，从 {start_byte} 字节开始续传")
            
            # 打开本地文件
            mode = 'ab' if start_byte > 0 else 'wb'
            
            with open(local_path, mode) as local_file:
                downloaded = start_byte
                
                def callback(data):
                    nonlocal downloaded
                    local_file.write(data)
                    downloaded += len(data)
                    
                    if progress_callback:
                        progress = (downloaded / remote_size) * 100
                        progress_callback(progress, downloaded, remote_size)
                
                # 设置断点续传位置
                if start_byte > 0:
                    self.ftp.voidcmd(f'REST {start_byte}')
                
                # 开始下载
                self.ftp.retrbinary(f'RETR {remote_path}', callback)
            
            print(f"文件下载完成: {remote_path} -> {local_path}")
            return True
            
        except Exception as e:
            print(f"下载文件失败: {e}")
            self.last_error = str(e)
            return False
    
    def upload_file(self, local_path: str, remote_path: str,
                   progress_callback: Optional[Callable] = None,
                   start_byte: int = 0) -> bool:
        """上传文件（支持断点续传）"""
        if not self.ensure_connected():
            return False
        
        if not os.path.exists(local_path):
            print(f"本地文件不存在: {local_path}")
            return False
        
        try:
            # 获取本地文件大小
            local_size = os.path.getsize(local_path)
            
            # 确保远程目录存在
            remote_dir = os.path.dirname(remote_path).replace('\\', '/')
            if remote_dir and remote_dir != '.':
                self.ensure_remote_directory(remote_dir)
            
            # 检查远程文件是否已存在
            if start_byte == 0:
                remote_size = self.get_file_size(remote_path)
                if remote_size is not None:
                    if remote_size == local_size:
                        print(f"远程文件已存在且大小相同，跳过上传: {remote_path}")
                        if progress_callback:
                            progress_callback(100.0, local_size, local_size)
                        return True
                    elif remote_size < local_size:
                        # 支持断点续传
                        start_byte = remote_size
                        print(f"检测到部分上传文件，从 {start_byte} 字节开始续传")
            
            with open(local_path, 'rb') as local_file:
                # 设置断点续传位置
                if start_byte > 0:
                    local_file.seek(start_byte)
                    self.ftp.voidcmd(f'REST {start_byte}')
                
                uploaded = start_byte
                
                def callback(data):
                    nonlocal uploaded
                    uploaded += len(data)
                    
                    if progress_callback:
                        progress = (uploaded / local_size) * 100
                        progress_callback(progress, uploaded, local_size)
                
                # 开始上传
                cmd = 'STOR' if start_byte == 0 else 'APPE'
                self.ftp.storbinary(f'{cmd} {remote_path}', local_file, callback=callback)
            
            print(f"文件上传完成: {local_path} -> {remote_path}")
            return True
            
        except Exception as e:
            print(f"上传文件失败: {e}")
            self.last_error = str(e)
            return False
    
    def delete_file(self, remote_path: str) -> bool:
        """删除远程文件"""
        if not self.ensure_connected():
            return False
        
        try:
            self.ftp.delete(remote_path)
            print(f"删除文件成功: {remote_path}")
            return True
        except Exception as e:
            print(f"删除文件失败: {e}")
            return False
    
    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect()
