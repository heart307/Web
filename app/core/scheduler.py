#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
动态时间片调度器
"""

import threading
import time
import json
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any

class TaskPriority(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"

class DynamicTimeSliceScheduler:
    """动态时间片调度器 - 实现全局序列轮转和动态时间片计算"""
    
    def __init__(self, max_workers=3, data_manager=None):
        self.max_workers = max_workers
        self.data_manager = data_manager
        
        # 全局任务序列
        self.task_sequence = []
        self.sequence_pointer = 0
        self.sequence_lock = threading.RLock()
        
        # 运行中的任务
        self.running_tasks = {}  # {thread_id: task_info}
        self.task_lock = threading.RLock()
        
        # 基础时间片配置 (秒)
        self.base_time_slices = {
            TaskPriority.HIGH: 120,    # 2分钟
            TaskPriority.MEDIUM: 60,   # 1分钟
            TaskPriority.LOW: 30       # 30秒
        }
        
        # 任务类型时间片倍数
        self.task_type_multipliers = {
            'file_download': 2.0,      # 文件下载
            'file_upload': 2.0,        # 文件上传
            'folder_download': 2.5,    # 文件夹下载
            'folder_upload': 2.5,      # 文件夹上传
            'folder_monitor': 0.5,     # 文件夹监控
            'folder_sync': 1.5,        # 文件夹同步
            'connection_test': 0.2,    # 连接测试
            'log_cleanup': 0.3         # 日志清理
        }
        
        # 注册的任务函数
        self.registered_functions = {}
        
        # 工作线程
        self.workers = []
        self.running = False
        
        # 统计信息
        self.stats = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'total_switches': 0,
            'total_execution_time': 0,
            'total_switch_overhead': 0
        }
        
        print("动态时间片调度器初始化完成")
    
    def register_function(self, name: str, func):
        """注册可执行的任务函数"""
        self.registered_functions[name] = func
        print(f"注册任务函数: {name}")
    
    def calculate_time_slice(self, priority: TaskPriority, task_type: str, 
                           file_size: Optional[int] = None) -> float:
        """动态计算时间片"""
        base_slice = self.base_time_slices[priority]
        type_multiplier = self.task_type_multipliers.get(task_type, 1.0)
        
        # 根据文件大小调整
        size_multiplier = 1.0
        if file_size:
            file_size_mb = file_size / (1024 * 1024)
            if file_size_mb > 500:      # >500MB
                size_multiplier = 3.0
            elif file_size_mb > 100:    # >100MB
                size_multiplier = 2.0
            elif file_size_mb > 10:     # >10MB
                size_multiplier = 1.5
            elif file_size_mb < 1:      # <1MB
                size_multiplier = 0.5
        
        final_slice = base_slice * type_multiplier * size_multiplier
        
        # 设置最小和最大限制
        return max(10.0, min(600.0, final_slice))  # 10秒-10分钟之间
    
    def add_task(self, task_data: Dict) -> str:
        """添加任务到调度器"""
        with self.sequence_lock:
            # 生成任务ID
            task_id = f"task_{int(time.time() * 1000)}"
            
            # 完善任务信息
            task_info = {
                'id': task_id,
                'func_name': task_data['func_name'],
                'args': task_data.get('args', []),
                'kwargs': task_data.get('kwargs', {}),
                'priority': TaskPriority(task_data['priority']),
                'task_type': task_data.get('task_type', 'unknown'),
                'file_size': task_data.get('file_size'),
                'status': 'pending',
                'progress': 0.0,
                'created_at': datetime.now().isoformat(),
                'started_at': None,
                'completed_at': None,
                'execution_count': 0,
                'total_execution_time': 0.0,
                'estimated_total_time': task_data.get('estimated_time', 0),
                'checkpoint_data': {},
                'error': None,
                'result': None,
                'created_by': task_data.get('created_by', 'system')
            }
            
            # 计算时间片
            task_info['time_slice'] = self.calculate_time_slice(
                task_info['priority'],
                task_info['task_type'],
                task_info['file_size']
            )
            
            # 插入到序列中的正确位置 (按优先级排序)
            self._insert_task_by_priority(task_info)
            
            # 保存到持久化存储
            if self.data_manager:
                self.data_manager.save_task(task_info)
            
            self.stats['total_tasks'] += 1
            
            print(f"添加任务: {task_id} (优先级: {task_info['priority'].value}, "
                  f"类型: {task_info['task_type']}, 时间片: {task_info['time_slice']:.1f}秒)")
            
            return task_id
    
    def _insert_task_by_priority(self, task_info: Dict):
        """按优先级将任务插入到序列中的正确位置"""
        priority_order = {
            TaskPriority.HIGH: 1,
            TaskPriority.MEDIUM: 2,
            TaskPriority.LOW: 3
        }
        
        task_priority = priority_order[task_info['priority']]
        
        # 找到插入位置
        insert_index = len(self.task_sequence)
        for i, existing_task in enumerate(self.task_sequence):
            existing_priority = priority_order[existing_task['priority']]
            if task_priority < existing_priority:
                insert_index = i
                break
        
        self.task_sequence.insert(insert_index, task_info)
        
        # 调整序列指针
        if insert_index <= self.sequence_pointer:
            self.sequence_pointer += 1
    
    def get_next_task_from_sequence(self) -> Optional[Dict]:
        """从序列中获取下一个待执行的任务"""
        with self.sequence_lock:
            if not self.task_sequence:
                return None

            # 确保指针在有效范围内
            if self.sequence_pointer >= len(self.task_sequence):
                self.sequence_pointer = 0

            # 寻找下一个待执行的任务
            attempts = 0

            while attempts < len(self.task_sequence):
                # 再次检查指针是否有效
                if self.sequence_pointer >= len(self.task_sequence):
                    self.sequence_pointer = 0

                current_task = self.task_sequence[self.sequence_pointer]

                # 移动指针到下一个位置 (循环)
                self.sequence_pointer = (self.sequence_pointer + 1) % len(self.task_sequence)
                attempts += 1

                # 检查任务是否可以执行
                if current_task['status'] == 'pending':
                    # 检查是否有执行时间限制（用于重新调度的任务）
                    next_execution = current_task.get('next_execution')
                    if next_execution:
                        try:
                            next_time = datetime.fromisoformat(next_execution)
                            if datetime.now() < next_time:
                                # 还没到执行时间，跳过这个任务
                                continue
                        except:
                            # 时间格式错误，忽略限制
                            pass

                    return current_task

            return None
    
    def start_workers(self):
        """启动工作线程"""
        if self.running:
            return

        self.running = True

        for i in range(self.max_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"TaskWorker-{i+1}",
                daemon=True
            )
            worker.start()
            self.workers.append(worker)

        print(f"启动了 {self.max_workers} 个工作线程")

        # 添加调试信息
        import time
        time.sleep(1)  # 等待线程启动
        alive_workers = [w for w in self.workers if w.is_alive()]
        print(f"活跃工作线程数: {len(alive_workers)}")
    
    def stop_workers(self):
        """停止工作线程"""
        self.running = False
        
        # 等待所有工作线程结束
        for worker in self.workers:
            worker.join(timeout=5)
        
        self.workers.clear()
        print("所有工作线程已停止")
    
    def _worker_loop(self):
        """工作线程主循环"""
        thread_id = threading.current_thread().name
        print(f"工作线程 {thread_id} 已启动")

        while self.running:
            try:
                # 获取下一个任务
                task = self.get_next_task_from_sequence()

                if task:
                    print(f"工作线程 {thread_id} 获取到任务: {task['id']}")
                    self._execute_task_with_timeslice(thread_id, task)
                else:
                    # 没有任务，休眠一下
                    time.sleep(1.0)
            except Exception as e:
                print(f"工作线程 {thread_id} 发生错误: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(5.0)  # 错误后等待5秒再继续

        print(f"工作线程 {thread_id} 已停止")
    
    def _execute_task_with_timeslice(self, thread_id: str, task: Dict):
        """执行任务（带时间片限制）"""
        task_id = task['id']
        time_slice = task['time_slice']
        
        # 记录开始执行
        with self.task_lock:
            self.running_tasks[thread_id] = task
            task['status'] = 'running'
            task['started_at'] = datetime.now().isoformat()
            task['execution_count'] += 1
            task['current_worker'] = thread_id
        
        # 保存状态
        if self.data_manager:
            self.data_manager.save_task(task)
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {thread_id} 开始执行任务 {task_id} "
              f"(优先级: {task['priority'].value}, 时间片: {time_slice:.1f}秒, "
              f"第{task['execution_count']}次执行)")
        
        start_time = time.time()
        
        try:
            # 获取任务函数
            func_name = task['func_name']
            func = self.registered_functions.get(func_name)
            if not func:
                raise ValueError(f"未注册的函数: {func_name}")
            
            # 执行任务
            result = self._execute_with_timeout(
                func, task_id, time_slice,
                *task['args'], **task['kwargs']
            )
            
            execution_time = time.time() - start_time
            task['total_execution_time'] += execution_time
            
            with self.task_lock:
                if result == "TIMEOUT":
                    # 时间片用完，任务未完成
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] {thread_id} 任务 {task_id} "
                          f"时间片用完({execution_time:.1f}s)，重新排队")

                    task['status'] = 'pending'
                    self.stats['total_switches'] += 1
                    self.stats['total_switch_overhead'] += 0.1  # 估算切换开销

                else:
                    # 检查是否需要重新调度（用于持续任务如文件夹监控）
                    if isinstance(result, str) and result.startswith("RESCHEDULE:"):
                        # 需要重新调度的任务
                        actual_result = result[11:]  # 移除"RESCHEDULE:"前缀
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] {thread_id} 任务 {task_id} "
                              f"执行完成，等待重新调度({execution_time:.1f}s): {actual_result}")

                        task['status'] = 'pending'  # 重置为等待状态
                        task['result'] = actual_result
                        task['last_execution'] = datetime.now().isoformat()

                        # 获取监控间隔
                        monitor_interval = task.get('monitor_interval', 300)  # 默认5分钟
                        task['next_execution'] = (datetime.now() + timedelta(seconds=monitor_interval)).isoformat()

                        # 不从序列中移除，保持在队列中等待下次执行
                        print(f"任务 {task_id} 将在 {monitor_interval} 秒后重新执行")

                    else:
                        # 任务完成
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] {thread_id} 任务 {task_id} "
                              f"执行完成({execution_time:.1f}s)")

                        task['status'] = 'completed'
                        task['completed_at'] = datetime.now().isoformat()
                        task['result'] = result
                        task['progress'] = 100.0

                        # 从序列中移除已完成的任务
                        self._remove_task_from_sequence(task)

                        self.stats['completed_tasks'] += 1
                
                self.stats['total_execution_time'] += execution_time
                
        except Exception as e:
            execution_time = time.time() - start_time
            task['total_execution_time'] += execution_time
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {thread_id} 任务 {task_id} "
                  f"执行失败: {e}")
            
            with self.task_lock:
                task['status'] = 'failed'
                task['error'] = str(e)
                task['completed_at'] = datetime.now().isoformat()
                
                # 从序列中移除失败的任务
                self._remove_task_from_sequence(task)
                
                self.stats['failed_tasks'] += 1
        
        finally:
            # 清理运行状态
            with self.task_lock:
                if thread_id in self.running_tasks:
                    del self.running_tasks[thread_id]
            
            # 保存最终状态
            if self.data_manager:
                self.data_manager.save_task(task)
    
    def _remove_task_from_sequence(self, task: Dict):
        """从序列中移除任务"""
        with self.sequence_lock:
            if task in self.task_sequence:
                task_index = self.task_sequence.index(task)
                self.task_sequence.remove(task)

                # 调整序列指针
                if task_index < self.sequence_pointer:
                    self.sequence_pointer -= 1

                # 确保指针在有效范围内
                if self.task_sequence:
                    if self.sequence_pointer >= len(self.task_sequence):
                        self.sequence_pointer = 0
                else:
                    self.sequence_pointer = 0

    def _execute_with_timeout(self, func, task_id: str, timeout: float, *args, **kwargs):
        """带超时的函数执行"""
        result = None
        exception = None

        def target():
            nonlocal result, exception
            try:
                # 传递调度器实例，让任务函数可以更新进度
                result = func(task_id, timeout, self, *args, **kwargs)
            except Exception as e:
                exception = e

        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        thread.join(timeout)

        if thread.is_alive():
            # 超时了
            return "TIMEOUT"

        if exception:
            raise exception

        return result

    def update_task_progress(self, task_id: str, progress: float, checkpoint_data: Dict = None):
        """更新任务进度"""
        with self.task_lock:
            # 在运行中的任务中查找
            for task in self.running_tasks.values():
                if task['id'] == task_id:
                    task['progress'] = progress
                    if checkpoint_data:
                        task['checkpoint_data'].update(checkpoint_data)

                    # 保存到持久化存储
                    if self.data_manager:
                        self.data_manager.save_task(task)
                    break

    def pause_task(self, task_id: str) -> bool:
        """暂停任务"""
        with self.task_lock, self.sequence_lock:
            # 查找任务
            for task in self.task_sequence:
                if task['id'] == task_id:
                    if task['status'] in ['pending', 'running']:
                        task['status'] = 'paused'
                        if self.data_manager:
                            self.data_manager.save_task(task)
                        return True
            return False

    def resume_task(self, task_id: str) -> bool:
        """恢复任务"""
        with self.task_lock, self.sequence_lock:
            # 查找任务
            for task in self.task_sequence:
                if task['id'] == task_id:
                    if task['status'] == 'paused':
                        task['status'] = 'pending'
                        if self.data_manager:
                            self.data_manager.save_task(task)
                        return True
            return False

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        with self.task_lock, self.sequence_lock:
            # 查找并移除任务
            for task in self.task_sequence[:]:
                if task['id'] == task_id:
                    task['status'] = 'failed'
                    task['error'] = "用户取消"
                    task['completed_at'] = datetime.now().isoformat()

                    self._remove_task_from_sequence(task)

                    if self.data_manager:
                        self.data_manager.save_task(task)
                    return True
            return False

    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        with self.task_lock, self.sequence_lock:
            # 检查任务是否正在运行
            if task_id in self.running_tasks:
                return False  # 不能删除正在运行的任务

            # 从任务序列中移除
            found_in_sequence = False
            for task in self.task_sequence[:]:
                if task['id'] == task_id:
                    self.task_sequence.remove(task)
                    found_in_sequence = True
                    break

            # 从数据管理器中删除任务记录
            data_deleted = False
            if self.data_manager:
                # 先检查任务是否存在于数据中
                try:
                    tasks_data = self.data_manager.load_tasks()
                    task_exists_in_data = task_id in tasks_data.get('tasks', {})

                    if task_exists_in_data:
                        # 调用删除方法
                        self.data_manager.delete_task(task_id)

                        # 验证删除是否成功
                        updated_data = self.data_manager.load_tasks()
                        task_still_exists = task_id in updated_data.get('tasks', {})
                        data_deleted = not task_still_exists
                    else:
                        data_deleted = False

                except Exception as e:
                    print(f"删除任务时出错: {e}")
                    data_deleted = False

            # 如果在序列中找到或从数据中删除成功，则认为删除成功
            return found_in_sequence or data_deleted

    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        task_data = None

        # 在运行中的任务中查找
        for task in self.running_tasks.values():
            if task['id'] == task_id:
                task_data = task.copy()
                break

        # 在序列中查找
        if not task_data:
            with self.sequence_lock:
                for task in self.task_sequence:
                    if task['id'] == task_id:
                        task_data = task.copy()
                        break

        if task_data:
            # 清理数据，确保可以JSON序列化
            if hasattr(task_data.get('priority'), 'value'):
                task_data['priority'] = task_data['priority'].value
            if hasattr(task_data.get('status'), 'value'):
                task_data['status'] = task_data['status'].value

            return task_data

        return None

    def get_all_tasks(self) -> List[Dict]:
        """获取所有任务状态"""
        all_tasks = []

        # 添加运行中的任务
        with self.task_lock:
            all_tasks.extend(self.running_tasks.values())

        # 添加序列中的任务
        with self.sequence_lock:
            for task in self.task_sequence:
                if task not in all_tasks:
                    all_tasks.append(task)

        # 添加已保存的历史任务（从数据管理器获取）
        if self.data_manager:
            try:
                # 获取最近的任务（限制数量避免性能问题）
                saved_tasks = self.data_manager.get_recent_tasks(limit=100)
                for saved_task in saved_tasks:
                    # 避免重复添加（检查ID）
                    if not any(task['id'] == saved_task['id'] for task in all_tasks):
                        all_tasks.append(saved_task)
            except Exception as e:
                print(f"获取历史任务失败: {e}")

        # 清理任务数据，确保可以JSON序列化
        cleaned_tasks = []
        for task in all_tasks:
            cleaned_task = task.copy()

            # 转换枚举类型为字符串
            if hasattr(cleaned_task.get('priority'), 'value'):
                cleaned_task['priority'] = cleaned_task['priority'].value
            if hasattr(cleaned_task.get('status'), 'value'):
                cleaned_task['status'] = cleaned_task['status'].value

            cleaned_tasks.append(cleaned_task)

        return cleaned_tasks

    def get_statistics(self) -> Dict:
        """获取调度器统计信息"""
        with self.task_lock, self.sequence_lock:
            current_stats = self.stats.copy()

            # 计算等待中的任务数量（处理枚举类型）
            pending_count = 0
            for task in self.task_sequence:
                task_status = task.get('status')
                if hasattr(task_status, 'value'):
                    task_status = task_status.value
                if task_status == 'pending':
                    pending_count += 1

            current_stats.update({
                'running_tasks': len(self.running_tasks),
                'pending_tasks': pending_count,
                'total_tasks_in_sequence': len(self.task_sequence),
                'current_sequence_pointer': self.sequence_pointer,
                'efficiency': (
                    (current_stats['total_execution_time'] /
                     (current_stats['total_execution_time'] + current_stats['total_switch_overhead']) * 100)
                    if (current_stats['total_execution_time'] + current_stats['total_switch_overhead']) > 0 else 0
                )
            })

        return current_stats

    def restore_tasks(self, tasks_data: Dict):
        """恢复任务（程序重启时使用）"""
        if not tasks_data or 'tasks' not in tasks_data:
            return

        restored_count = 0

        with self.sequence_lock:
            for task_id, task_data in tasks_data['tasks'].items():
                # 只恢复未完成的任务
                if task_data.get('status') in ['pending', 'running']:
                    # 重置状态
                    task_data['status'] = 'pending'
                    task_data['current_worker'] = None

                    # 转换枚举类型
                    if isinstance(task_data.get('priority'), str):
                        task_data['priority'] = TaskPriority(task_data['priority'])

                    # 插入到序列中
                    self._insert_task_by_priority(task_data)
                    restored_count += 1

        print(f"恢复了 {restored_count} 个未完成的任务")
