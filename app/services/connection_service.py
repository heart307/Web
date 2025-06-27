#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
连接测试服务模块
独立于任务调度器的即时连接测试功能
"""

import time
import threading
from datetime import datetime
from typing import Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed


class ConnectionTestService:
    """连接测试服务"""
    
    def __init__(self, data_manager, max_concurrent_tests=5):
        """
        初始化连接测试服务
        
        Args:
            data_manager: 数据管理器实例
            max_concurrent_tests: 最大并发测试数
        """
        self.data_manager = data_manager
        self.max_concurrent_tests = max_concurrent_tests
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_tests, thread_name_prefix="ConnectionTest")
        self.active_tests = {}  # site_id -> future
        self.test_lock = threading.Lock()
        
        print(f"连接测试服务已初始化，最大并发数: {max_concurrent_tests}")
    
    def test_site_connection(self, site_id: str, site_data: dict, created_by: str = 'system') -> bool:
        """
        测试站点连接（异步执行）
        
        Args:
            site_id: 站点ID
            site_data: 站点配置数据
            created_by: 测试发起者
            
        Returns:
            bool: 是否成功启动测试
        """
        with self.test_lock:
            # 检查是否已有正在进行的测试
            if site_id in self.active_tests:
                future = self.active_tests[site_id]
                if not future.done():
                    print(f"站点 {site_id} 已有正在进行的连接测试")
                    return False
                else:
                    # 清理已完成的测试
                    del self.active_tests[site_id]
            
            # 提交新的测试任务
            future = self.executor.submit(
                self._execute_connection_test,
                site_id, site_data, created_by
            )
            self.active_tests[site_id] = future
            
            print(f"已启动站点 {site_id} 的连接测试")
            return True
    
    def _execute_connection_test(self, site_id: str, site_data: dict, created_by: str):
        """
        执行连接测试的核心逻辑
        
        Args:
            site_id: 站点ID
            site_data: 站点配置数据
            created_by: 测试发起者
        """
        try:
            print(f"开始执行站点连接测试: {site_id}")
            start_time = time.time()
            
            # 导入FTP客户端
            from app.core.ftp_client import FTPClient
            
            # 解密密码
            password = self._decrypt_password(site_data.get('password', ''))
            
            # 创建FTP客户端并测试连接
            ftp_client = FTPClient(
                host=site_data['host'],
                port=site_data['port'],
                username=site_data.get('username', ''),
                password=password
            )
            
            # 尝试连接
            success = ftp_client.connect()
            connection_time = time.time() - start_time
            
            # 更新站点状态
            if success:
                status = 'connected'
                error_msg = None
                print(f"站点 {site_id} 连接成功，耗时 {connection_time:.2f}秒")
            else:
                status = 'disconnected'
                error_msg = ftp_client.last_error or "连接失败"
                print(f"站点 {site_id} 连接失败: {error_msg}")
            
            # 断开连接
            try:
                ftp_client.disconnect()
            except:
                pass
            
            # 更新站点数据
            self._update_site_status(site_id, status, connection_time, error_msg)
            
            # 记录操作日志
            self._log_connection_test(site_id, site_data, success, connection_time, error_msg, created_by)
            
            return success
            
        except Exception as e:
            print(f"连接测试异常: {e}")
            import traceback
            traceback.print_exc()
            
            # 更新站点状态为错误
            self._update_site_status(site_id, 'disconnected', None, str(e))
            
            # 记录错误日志
            self._log_connection_test(site_id, site_data, False, None, str(e), created_by)
            
            return False
        
        finally:
            # 清理活跃测试记录
            with self.test_lock:
                self.active_tests.pop(site_id, None)
    
    def _decrypt_password(self, encrypted: str) -> str:
        """解密密码"""
        try:
            import base64
            return base64.b64decode(encrypted.encode()).decode()
        except:
            return encrypted
    
    def _update_site_status(self, site_id: str, status: str, connection_time: Optional[float], error_msg: Optional[str]):
        """更新站点状态"""
        try:
            sites = self.data_manager.load_sites()
            for site in sites:
                if site['id'] == site_id:
                    site['status'] = status
                    site['last_check'] = datetime.now().isoformat()
                    site['connection_time'] = connection_time
                    site['last_error'] = error_msg
                    site.pop('auto_test', None)  # 移除自动测试标记
                    
                    # 保存更新
                    self.data_manager.save_site(site)
                    break
        except Exception as e:
            print(f"更新站点状态失败: {e}")
    
    def _log_connection_test(self, site_id: str, site_data: dict, success: bool, 
                           connection_time: Optional[float], error_msg: Optional[str], created_by: str):
        """记录连接测试日志"""
        try:
            self.data_manager.write_log('operations', {
                'action': 'connection_test',
                'site_id': site_id,
                'site_name': site_data.get('name', 'unknown'),
                'host': site_data.get('host', 'unknown'),
                'status': 'success' if success else 'failed',
                'connection_time': connection_time,
                'error': error_msg,
                'tested_by': created_by
            })
        except Exception as e:
            print(f"记录连接测试日志失败: {e}")
    
    def get_active_tests(self) -> Dict[str, bool]:
        """获取当前活跃的测试"""
        with self.test_lock:
            return {
                site_id: not future.done() 
                for site_id, future in self.active_tests.items()
            }
    
    def test_all_sites(self, created_by: str = 'system') -> int:
        """
        测试所有站点的连接
        
        Args:
            created_by: 测试发起者
            
        Returns:
            int: 启动的测试数量
        """
        try:
            sites = self.data_manager.load_sites()
            started_count = 0
            
            for site in sites:
                if self.test_site_connection(site['id'], site, created_by):
                    started_count += 1
            
            print(f"批量连接测试已启动，共 {started_count} 个站点")
            return started_count
            
        except Exception as e:
            print(f"批量连接测试失败: {e}")
            return 0
    
    def shutdown(self):
        """关闭连接测试服务"""
        print("正在关闭连接测试服务...")
        self.executor.shutdown(wait=True)
        print("连接测试服务已关闭")
